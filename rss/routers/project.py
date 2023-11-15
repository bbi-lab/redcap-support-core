from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from redcap.project import Project
from sqlalchemy.orm import Session

from rss import deps
from rss.lib.authorization import require_authorized_admin
from rss.lib.redcap_interface import (
    build_event_map,
    build_form_field_map,
    build_repeat_instruments_map,
    extract,
)
from rss.models.event import Event
from rss.models.instrument import Instrument
from rss.models.project_arm import ProjectArm
from rss.models.project_event import ProjectEvent, event_instrument_association
from rss.models.project_field import ProjectField
from rss.models.project_instrument import ProjectInstrument
from rss.models.user import User
from rss.view_models import project

# Router for handling all interactions with REDCap
router = APIRouter(
    prefix="/api/v1/project",
    tags=["project", "redcap"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/metadata",
    status_code=200,
    response_model=list,
    responses={404: {}},
)
def get_project_metadata(
    redcap_project: Project = Depends(deps.get_project),
) -> list:
    """
    Constructs a dictionary with event/instrument REDCap project mappings.
    """
    return redcap_project.metadata


@router.get(
    "/events",
    status_code=200,
    response_model=dict,
    responses={404: {}},
)
def get_project_event_mappings(
    redcap_project: Project = Depends(deps.get_project),
) -> dict:
    """
    Constructs a dictionary with event/instrument REDCap project mappings.
    """
    return build_event_map(redcap_project)


@router.get("/instruments", status_code=200, response_model=dict, responses={404: {}})
def get_project_repeat_instruments(
    redcap_project: Project = Depends(deps.get_project),
) -> dict:
    """
    Constructs a list of dictionaries containing all repeating instruments in a project.
    """
    return build_repeat_instruments_map(redcap_project)


@router.get("/fields", status_code=200, response_model=dict, responses={404: {}})
def get_project_field_names(
    redcap_project: Project = Depends(deps.get_project),
) -> dict:
    """
    Constructs a list of dictionaries containing all field names in a REDCap project.
    """
    return build_form_field_map(redcap_project)


@router.get(
    "/relational/records",
    status_code=200,
    response_model=list[int],
    responses={404: {}},
)
def get_record_ids(
    db: Session = Depends(deps.get_db),
) -> list[int]:
    """
    Returns a list of REDCap record IDs.
    """
    return sorted(
        set(record_id[0] for record_id in db.query(Event.record_id).tuples().all())
    )


@router.get(
    "/relational/events",
    status_code=200,
    response_model=list[project.ProjectEvent],
    responses={404: {}},
)
def get_internal_event_mappings(
    db: Session = Depends(deps.get_db),
) -> list[ProjectEvent]:
    """
    Returns a list of internal relational REDCap event mappings.
    """
    return db.query(ProjectEvent).all()


@router.get(
    "/relational/instruments",
    status_code=200,
    response_model=list[project.ProjectInstrument],
    responses={404: {}},
)
def get_internal_instrument_mappings(
    db: Session = Depends(deps.get_db),
) -> list[ProjectInstrument]:
    """
    Returns a list of internal relational REDCap instrument mappings.
    """
    return db.query(ProjectInstrument).all()


@router.get(
    "/relational/fields",
    status_code=200,
    response_model=list[project.ProjectField],
    responses={404: {}},
)
def get_internal_field_mappings(
    db: Session = Depends(deps.get_db),
) -> list[ProjectField]:
    """
    Returns a list of internal relational REDCap field mappings.
    """
    return db.query(ProjectField).all()


@router.post("/clear", status_code=200, response_model=None, responses={404: {}})
def clear_project_data(
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_authorized_admin),
) -> None:
    """
    Refreshes all study data with newly extracted REDCap project data.
    """
    db.query(Event).delete()
    db.query(Instrument).delete()

    db.query(ProjectField).delete()
    db.query(event_instrument_association).delete()
    db.query(ProjectInstrument).delete()
    db.query(ProjectEvent).delete()
    db.query(ProjectArm).delete()

    db.commit()


@router.post("/refresh", status_code=200, response_model=int, responses={404: {}})
def refresh_project_data(
    redcap_project: Project = Depends(deps.get_project),
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_authorized_admin),
) -> int:
    """
    Refreshes all study data with newly extracted REDCap project data.
    """
    # Split export of whole project into 10 batches
    next_record = int(redcap_project.generate_next_record_name())
    batch_size = next_record // 10

    relational_redcap(redcap_project, db)
    db.commit()

    event_data, form_data = extract(redcap_project, batch_size=batch_size)
    upsert_record_data(db, event_data, form_data)
    db.commit()
    return next_record


@router.post(
    "/refresh/{record_id}", status_code=200, response_model=bool, responses={404: {}}
)
def refresh_project_data_by_record(
    record_id: int,
    redcap_project: Project = Depends(deps.get_project),
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_authorized_admin),
) -> bool:
    """
    Refreshes a specific record with newly extracted REDCap data for that record
    """
    relational_redcap(redcap_project, db)
    db.commit()

    event_data, form_data = extract(redcap_project, [record_id])
    upsert_record_data(db, event_data, form_data)
    db.commit()
    return True


def upsert_record_data(
    db: Session, event_data: list[dict], form_data: list[dict]
) -> None:
    """
    Upserts the provided REDCap data into the passed db session
    """
    event_instances = db.query(Event).join(ProjectEvent).join(ProjectInstrument)
    for data in event_data:
        event = (
            db.query(ProjectEvent)
            .filter(ProjectEvent.name == data["event_name"])
            .one_or_none()
        )
        instrument = (
            db.query(ProjectInstrument)
            .filter(ProjectInstrument.name == data["form_name"])
            .one_or_none()
        )

        if not event:
            raise ValueError(
                f"Event name {data['event_name']} does not exist on this project."
            )

        if not instrument:
            raise ValueError(
                f"Instrument name {data['event_name']} does not exist on this project."
            )

        item = event_instances.filter(
            Event.record_id == data["record_id"],
            Event.repeat_instance == data["repeat_instance"],
            ProjectEvent.name == data["event_name"],
            ProjectInstrument.name == data["form_name"],
        ).one_or_none()

        if item:
            item.data = data["data"]
        else:
            item = Event(
                **jsonable_encoder(
                    data, exclude={"event_name", "form_name", "event", "instrument"}
                ),
                event_id=event.id,
                instrument_id=instrument.id,
                event=event,
                instrument=instrument,
            )

        db.add(item)

    instrument_instances = (
        db.query(Instrument).join(ProjectEvent).join(ProjectInstrument)
    )
    for data in form_data:
        event = (
            db.query(ProjectEvent)
            .filter(ProjectEvent.name == data["event_name"])
            .one_or_none()
        )
        instrument = (
            db.query(ProjectInstrument)
            .filter(ProjectInstrument.name == data["form_name"])
            .one_or_none()
        )

        if not event:
            raise ValueError(
                f"Event name {data['event_name']} does not exist on this project."
            )

        if not instrument:
            raise ValueError(
                f"Instrument name {data['event_name']} does not exist on this project."
            )

        item = instrument_instances.filter(
            Instrument.record_id == data["record_id"],
            Instrument.repeat_instance == data["repeat_instance"],
            ProjectEvent.name == data["event_name"],
            ProjectInstrument.name == data["form_name"],
        ).one_or_none()

        if item:
            item.data = data["data"]
        else:
            item = Instrument(
                **jsonable_encoder(
                    data, exclude={"event_name", "form_name", "event", "instrument"}
                ),
                event_id=event.id,
                instrument_id=instrument.id,
                event=event,
                instrument=instrument,
            )

        db.add(item)


def relational_redcap(redcap_project: Project, db: Session) -> None:
    """
    Adds rows representing the passed REDCap project relationally to
    the passed db session.
    """
    arm_event_instruments = build_event_map(redcap_project)
    repeating_instruments = build_repeat_instruments_map(redcap_project)
    instrument_fields = build_form_field_map(redcap_project, reverse_mapping=True)

    created_instruments: dict[str, ProjectInstrument] = {}
    for arm, event_instruments in arm_event_instruments.items():
        existing_arm = (
            db.query(ProjectArm).filter(ProjectArm.name == str(arm)).one_or_none()
        )
        if not existing_arm:
            project_arm = ProjectArm(name=arm)
            db.add(project_arm)
        else:
            project_arm = existing_arm

        for event, instruments in event_instruments.items():
            repeating_event = (
                True
                if (
                    event in repeating_instruments.keys()
                    and repeating_instruments[event] is None
                )
                else False
            )

            existing_event = (
                db.query(ProjectEvent).filter(ProjectEvent.name == event).one_or_none()
            )
            if not existing_event:
                project_event = ProjectEvent(
                    name=event,
                    arm_id=project_arm.id,
                    arm=project_arm,
                    repeating=repeating_event,
                )
                db.add(project_event)
            else:
                project_event = existing_event

            for instrument in instruments:
                repeating_instrument = (
                    True
                    if instrument in repeating_instruments.get(event, [])
                    else False
                )

                # REDCap projects may not intermix repeating instruments and events.
                if repeating_instrument and repeating_event:
                    raise ValueError(
                        "There can't be both repeating events and instruments"
                    )

                existing_instrument = (
                    db.query(ProjectInstrument)
                    .filter(ProjectInstrument.name == instrument)
                    .one_or_none()
                )

                # instrument was just created under a different event
                if instrument in created_instruments:
                    project_instrument = created_instruments[instrument]
                    project_instrument.events.append(project_event)
                # instrument was created in the past. Ensure event is related
                elif existing_instrument:
                    project_instrument = existing_instrument
                    if project_event not in project_instrument.events:
                        project_instrument.events.append(project_event)
                    db.refresh(project_instrument)  # this object is persistent
                # instrument needs to be created
                else:
                    project_instrument = ProjectInstrument(
                        name=instrument,
                        repeating=repeating_instrument,
                        events=[project_event],
                    )
                    created_instruments[instrument] = project_instrument
                    db.add(project_instrument)

    for field in redcap_project.export_field_names():
        instrument_name = instrument_fields.get(field["original_field_name"])

        # Handle things like <survey_name>_complete, which are for some reason
        # not surfaced by instrument field mappings.
        if not instrument_name:
            instrument_name = "_".join(field["original_field_name"].split("_")[0:2])

        if instrument_name not in instrument_fields.values():
            raise ValueError(
                f"Instrument {instrument_name} is not defined on this project instance."
            )

        # The instrument might have been created previously
        existing_instrument = created_instruments.get(instrument_name)
        if not existing_instrument:
            existing_instrument = (
                db.query(ProjectInstrument)
                .filter(ProjectInstrument.name == instrument_name)
                .one_or_none()
            )

            if not existing_instrument:
                raise ValueError(
                    "To add fields to an instrument, the instrument must have been created"
                )

        # Use the export field name for fields, rather than the original.
        # TODO: We might consider adding another field mapping layer to the model that accounts
        # for these fields, since their REDCap representations don't fit very well within our
        # model at the moment.
        field_name = field["export_field_name"]
        existing_field = (
            db.query(ProjectField).filter(ProjectField.name == field_name).one_or_none()
        )

        if not existing_field:
            project_field = ProjectField(
                name=field_name,
                instrument_id=existing_instrument.id,
                instrument=existing_instrument,
            )
            db.add(project_field)
