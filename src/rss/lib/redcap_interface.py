import logging
import os
from enum import Enum
from typing import Optional, Union
from more_itertools import batched
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from redcap.project import Project
from rss.models.project import ProjectArm, ProjectEvent, ProjectInstrument, ProjectField
from rss.models.event import Event
from rss.models.instrument import Instrument

logger = logging.getLogger(__name__)


class RecordClass(Enum):
    EVENT = "event"
    FORM = "instrument"


def redcap_environment() -> tuple[str, str]:
    redcap_url = os.environ.get("REDCAP_URL")
    redcap_api_key = os.environ.get("REDCAP_API_KEY")

    if not redcap_url:
        raise ValueError("`REDCAP_URL` should be available as an environment variable")

    if not redcap_api_key:
        raise ValueError(
            "`REDCAP_API_KEY` should be available as an environment variable"
        )

    return redcap_url, redcap_api_key


def build_event_map(redcap_project: Project) -> dict[str, dict[str, list[str]]]:
    """
    Construct a map of events and which study arm they belong to.
    """
    event_map = {}

    for event_dict in redcap_project.export_instrument_event_mappings():
        event = event_dict.get("unique_event_name")
        arm = event_dict.get("arm_num")
        form = event_dict.get("form")

        # Events are surfaced per field, we don't care about duplicates
        if arm in event_map:
            if event in event_map[arm]:
                event_map[arm][event].append(form)
            else:
                event_map[arm][event] = [form]

        else:
            event_map[arm] = {event: [form]}

    return event_map


def build_form_field_map(
    redcap_project: Project, reverse_mapping=False
) -> Union[dict[str, list[str]], dict[str, str]]:
    """
    Construct a map of forms -> contained fields. If reverse_mapping is
    True, build a map of fields -> containing form.
    """
    form_field_map = {}

    for form_field in redcap_project.metadata:
        form = form_field.get("form_name")
        field = form_field.get("field_name")

        if reverse_mapping:
            form_field_map[field] = form
        else:
            if form in form_field_map:
                form_field_map[form].append(field)
            else:
                form_field_map[form] = [field]

    return form_field_map


def build_repeat_instruments_map(redcap_project: Project) -> dict[str, str]:
    """
    Construct a map of repeat instruments and which events they belong to.
    """
    repeat_instrument_map = {}

    for instrument in redcap_project.export_repeating_instruments_events():
        event = instrument.get("event_name")
        form = instrument.get("form_name")

        # REDCap indicates no form with "", which is falsy
        if event in repeat_instrument_map and form:
            repeat_instrument_map[event].append(form)
        elif form:
            repeat_instrument_map[event] = [form]
        else:
            repeat_instrument_map[event] = None

    return repeat_instrument_map


def export_records_in_batch(
    redcap_project, batches: Optional[list[tuple[int]]] = None, **kwargs
) -> list[dict[str, str]]:
    """
    Export REDCap project records in batches. Kwargs may be any kwarg accepted
    by the Pycap `export_records` function.
    See: http://redcap-tools.github.io/PyCap/api_reference/project/#redcap.project.Project.export_records
    """
    if not batches:
        logger.debug(
            f"No batches provided. Fetching all records with arguments {kwargs}."
        )
        return redcap_project.export_records(**kwargs)

    records = []
    for batch in batches:
        logger.debug(
            f"Fetching batch {batch[0]}-{batch[-1]} of data with arguments {kwargs}."
        )
        records.extend(redcap_project.export_records(records=batch, **kwargs))

    logger.info(f"Fetched {len(records)} REDCap records via API.")
    return records


def upsert_record_data(
    db: Session,
    records_to_upsert: list[dict],
    Model: Union[type[Event], type[Instrument]],
    constraint: str,
) -> int:
    """
    Upserts the provided REDCap records into the passed db session. The passed model
    is the model object these records belong to while the constraint is the PSQL
    UNIQUE CONSTRAINT that tells us when records conflict with those within our DB.
    """
    logger.info(
        f"Preparing to upsert {len(records_to_upsert)} {Model.__name__} records."
    )

    fetched_events, fetched_instruments, items = {}, {}, []
    for record in records_to_upsert:
        # Cache events/instruments to avoid repeat queries to DB.
        if record["event_name"] not in fetched_events:
            logger.debug(
                f"No cached event found. Fetching event info for {record['event_name']}."
            )

            fetched_events[record["event_name"]] = db.scalars(
                select(ProjectEvent).where(ProjectEvent.name == record["event_name"])
            ).one_or_none()

        if record["form_name"] not in fetched_instruments:
            logger.debug(
                f"No cached instrument found. Fetching event info for {record['event_name']}."
            )

            fetched_instruments[record["form_name"]] = db.scalars(
                select(ProjectInstrument).where(
                    ProjectInstrument.name == record["form_name"]
                )
            ).one_or_none()

        event, instrument = (
            fetched_events[record["event_name"]],
            fetched_instruments[record["form_name"]],
        )

        # The event/instrument this record belongs to must exist on our DB instance to ingest it.
        if not event:
            raise ValueError(
                f"Event name {record['event_name']} does not exist on this project."
            )

        if not instrument:
            raise ValueError(
                f"Instrument name {record['form_name']} does not exist on this project."
            )

        item = {
            "record_id": record["record_id"],
            "repeat_instance": record["repeat_instance"],
            "data": record["data"],
            "event_id": event.id,
            "instrument_id": instrument.id,
        }
        items.append(item)

        logger.debug(
            f"Adding event from record {item['record_id']} within event {item['event_id']}, instrument {item['instrument_id']} (repeat instance {item['repeat_instance']})."
        )

    # Bulk upsert all items in batches of 10000 to avoid EOF errors due to buffer size.
    if items:
        for n, batch in enumerate(batched(items, 10000)):
            insert_stmt = insert(Model).values(batch)
            on_conflict = insert_stmt.on_conflict_do_update(
                constraint=constraint,
                set_={"data": insert_stmt.excluded.data},
            )
            result = db.execute(on_conflict)

            logger.info(
                f"Upserted {len(batch)} (batch {n+1}) records of type {Model.__name__}. {result.rowcount} conflicting records were updated."
            )

        db.flush()

    return len(items)


def relational_redcap(redcap_project: Project, db: Session) -> None:
    """
    Adds rows representing the passed REDCap project relationally to
    the passed db session.
    """

    def add_arm_to_project(arm: str) -> ProjectArm:
        existing_arm = db.scalars(
            select(ProjectArm).where(ProjectArm.name == str(arm))
        ).one_or_none()

        if not existing_arm:
            project_arm = ProjectArm(name=arm)
            db.add(project_arm)
            logger.debug(
                f"Arm did not already exist in project. Created arm {project_arm.name}."
            )

        else:
            project_arm = existing_arm
            logger.debug(f"Arm {project_arm.name} already existed in project.")

        return project_arm

    def add_all_events_to_arm(
        project_arm: ProjectArm,
        event_instruments: dict[str, list[str]],
        repeating_instruments: dict[str, str],
    ) -> dict[str, ProjectInstrument]:
        created_instruments: dict[str, ProjectInstrument] = {}

        logger.debug(
            f"Adding {len(event_instruments)} within {project_arm.name} to project."
        )
        for event, instruments in event_instruments.items():
            repeating_event = (
                True
                if (
                    event in repeating_instruments.keys()
                    and repeating_instruments[event] is None
                )
                else False
            )

            existing_event = db.scalars(
                select(ProjectEvent).where(ProjectEvent.name == event)
            ).one_or_none()

            if not existing_event:
                project_event = ProjectEvent(
                    name=event,
                    arm_id=project_arm.id,
                    arm=project_arm,
                    repeating=repeating_event,
                )
                db.add(project_event)
                logger.debug(
                    f"Event did not already exist in project. Created event {project_event.name} of type Repeating = {repeating_event}."
                )
            else:
                project_event = existing_event
                logger.debug(
                    f"Event {project_event.name} of type Repeating = {repeating_event} already existed in project."
                )

            created_instruments = {
                **created_instruments,
                **add_all_instruments_to_event(project_event, instruments),
            }

        return created_instruments

    def add_all_instruments_to_event(
        project_event: ProjectEvent, instruments: list[str]
    ) -> dict[str, ProjectInstrument]:
        created_instruments: dict[str, ProjectInstrument] = {}

        logger.debug(
            f"Adding {len(instruments)} within {project_event.name} to project."
        )
        for instrument in instruments:
            repeating_instrument = (
                True
                if instrument in repeating_instruments.get(project_event.name, [])
                else False
            )

            # REDCap projects may not intermix repeating instruments and events.
            if repeating_instrument and project_event.repeating:
                raise ValueError("There can't be both repeating events and instruments")

            existing_instrument = db.scalars(
                select(ProjectInstrument).where(ProjectInstrument.name == instrument)
            ).one_or_none()

            if instrument in created_instruments:
                project_instrument = created_instruments[instrument]
                project_instrument.events.append(project_event)
                logger.debug(
                    f"Instrument {project_instrument} of type Repeating = {repeating_instrument} has already been created under a different event. Added event relationship {project_event.name}."
                )

            elif existing_instrument:
                project_instrument = existing_instrument
                if project_event not in project_instrument.events:
                    project_instrument.events.append(project_event)

                # this object is persistent
                db.refresh(project_instrument)
                logger.debug(
                    f"Instrument {project_instrument} of type Repeating = {repeating_instrument} has already been created in the past. Added event relationship to {project_event.name}."
                )

            else:
                project_instrument = ProjectInstrument(
                    name=instrument,
                    repeating=repeating_instrument,
                    events=[project_event],
                )
                created_instruments[instrument] = project_instrument
                db.add(project_instrument)
                logger.debug(
                    f"Instrument did not already exist in project. Created instrument {project_instrument.name} of type repeating = {repeating_instrument} within event {project_event.name}."
                )

        return created_instruments

    def add_field_to_project(
        field: dict,
        created_instruments: dict[str, ProjectInstrument],
        instrument_fields: Union[dict[str, str], dict[str, list[str]]],
    ):
        instrument_name = instrument_fields.get(field["original_field_name"])

        # Handle things like <survey_name>_complete, which are for some reason
        # not surfaced by instrument field mappings.
        if not instrument_name:
            instrument_name = "_".join(field["original_field_name"].split("_")[0:2])

        if instrument_name not in instrument_fields.values():
            raise ValueError(
                f"Instrument {instrument_name} is not defined on this project instance."
            )
        logger.debug(
            f"Adding field {field['original_field_name']} to instrument {instrument_name}."
        )

        # If the instrument was created as part of this refresh, it may not exist in the DB yet.
        existing_instrument = created_instruments.get(instrument_name)

        if not existing_instrument:
            existing_instrument = db.scalars(
                select(ProjectInstrument).where(
                    ProjectInstrument.name == instrument_name
                )
            ).one_or_none()

            if not existing_instrument:
                raise ValueError(
                    "To add fields to an instrument, the instrument must have been created"
                )

        # Use the export field name for fields, rather than the original name.
        # TODO: We might consider adding another field mapping layer to the model that accounts
        # for these fields, since their REDCap representations don't fit very well within our
        # model at the moment.
        field_name = field["export_field_name"]
        existing_field = db.scalars(
            select(ProjectField).where(ProjectField.name == field_name)
        ).one_or_none()

        if not existing_field:
            project_field = ProjectField(
                name=field_name,
                instrument_id=existing_instrument.id,
                instrument=existing_instrument,
            )
            db.add(project_field)
            logger.debug(
                f"Field did not already exist in project. Created field {project_field.name} within instrument {existing_instrument.name}."
            )
        else:
            project_field = existing_field
            logger.debug(
                f"Field {project_field.name} within instrument {existing_instrument.name} already existed in project."
            )

        return project_field

    # Dictionary persists instruments created during this functions' execution since they will not yet be available within the DB.
    created_instruments: dict[str, ProjectInstrument] = {}

    arm_event_instruments = build_event_map(redcap_project)
    repeating_instruments = build_repeat_instruments_map(redcap_project)

    logger.debug(f"Adding {len(arm_event_instruments)} arms to project.")
    for arm, instruments_within_arm in arm_event_instruments.items():
        project_arm = add_arm_to_project(arm)
        created_instruments = {
            **created_instruments,
            **add_all_events_to_arm(
                project_arm, instruments_within_arm, repeating_instruments
            ),
        }

    instrument_fields = build_form_field_map(redcap_project, reverse_mapping=True)
    field_names = redcap_project.export_field_names()

    logger.debug(f"Adding {len(field_names)} fields to project.")
    for field in field_names:
        add_field_to_project(field, created_instruments, instrument_fields)

    logger.info("Done constructing relational representation of REDCap project.")


def relational_refresh(
    redcap_project: Project, db: Session, batch_size: Optional[int] = None
) -> None:
    """
    Refreshes all events in the provided REDCap project. Record export will be done
    using the provided batch size, if provided.
    """
    events_to_refresh = db.scalars(select(ProjectEvent)).all()
    refreshed_events = 0

    if batch_size:
        batches = list(
            batched(
                range(1, int(redcap_project.generate_next_record_name())), batch_size
            )
        )
    else:
        batches = None

    logger.debug(
        f"Refreshing {len(events_to_refresh)} events in {len(batches)} batches."
    )
    for event in events_to_refresh:
        logger.debug(
            f"Refreshing {len(event.instruments)} instruments within event {event}."
        )
        for instrument in event.instruments:
            logger.info(f"Working on {event.name}, {instrument.name}")
            refreshed_records = export_records_in_batch(
                redcap_project, batches, events=[event.name], forms=[instrument.name]
            )

            logger.debug(f"Reformatting {len(refreshed_records)} prior to upsert.")
            refreshed_records = [
                format_redcap_record(
                    redcap_project, record, event.name, instrument.name
                )
                for record in refreshed_records
            ]

            # A record will be a `Form` class if it is repeating. All other records are
            # aggregated at the event level, so will be of class `Event`.
            if instrument.repeating:
                upserts = upsert_record_data(
                    db,
                    refreshed_records,
                    Instrument,
                    "instrument_record_id_repeat_instance_event_id_instrument_id_key",
                )
            else:
                upserts = upsert_record_data(
                    db,
                    refreshed_records,
                    Event,
                    "event_record_id_repeat_instance_event_id_instrument_id_key",
                )

            refreshed_events += upserts

    logger.info(f"Successfully refreshed {refreshed_events}.")


def format_redcap_record(
    project: Project, record: dict[str, str], event_name: str, form_name: str
) -> dict[str, str]:
    record_id = record[project.def_field]
    logger.debug(
        f"Reformatting record {record_id} in event {event_name}, instrument {form_name}."
    )

    # Use event/form names directly from the record if they are available.
    if record["redcap_event_name"] != "":
        event_name = record["redcap_event_name"]
    if record["redcap_repeat_instrument"] != "":
        form_name = record["redcap_repeat_instrument"]

    # When a repeat instance is not provided, assign the record to repeat instance 0.
    if record["redcap_repeat_instance"] != "":
        repeat_instance = record["redcap_repeat_instance"]
    else:
        logger.debug("No repeat instance data provided. Assuming instance 0.")
        repeat_instance = "0"

    # These are stored outside the JSON data blob rather than inside.
    record.pop(project.def_field)
    record.pop("redcap_repeat_instance")

    record = {
        "record_id": record_id,
        "event_name": event_name,
        "form_name": form_name,
        "repeat_instance": repeat_instance,
        "data": record,
    }

    logger.debug(
        f"Successfully reformatted record {record_id} in event {event_name}, instrument {form_name}, repeat instance {repeat_instance}."
    )
    return record
