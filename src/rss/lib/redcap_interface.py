import logging
import os
from enum import Enum
from typing import Optional
from more_itertools import batched

from redcap.project import Project

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


def build_event_map(redcap_project: Project):
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


def build_form_field_map(redcap_project: Project, reverse_mapping=False):
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


def build_repeat_instruments_map(redcap_project: Project):
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
):
    """
    Export REDCap project records in batches. Kwargs may be any kwarg accepted
    by the Pycap `export_records` function.
    See: http://redcap-tools.github.io/PyCap/api_reference/project/#redcap.project.Project.export_records
    """
    if not batches:
        return redcap_project.export_records(**kwargs)

    records = []
    for batch in batches:
        records.extend(redcap_project.export_records(records=batch, **kwargs))

    return records


def extract(
    redcap_project: Project,
    record_subset: list[int] = [],
    batch_size: Optional[int] = None,
):
    """
    Extract the data from a provided REDCap project, aggregating it at the event
    level (repeating events, and non-repeating instruments) and the form level
    (repeating instruments). NOTE: If a project does not have any repeating instruments,
    all data will be aggregated at the event level.

    Data may be extracted for individual records only by providing a list of records you
    would like to subset the data by.

    Data may be extracted in batches by providing a batch size. Records will be pulled in
    batches of at most this size.
    """

    # TODO: We probably want to base our extract off of our relational schema

    record_id_field = redcap_project.def_field

    # Respect batch sizes even when extracting via subset
    if batch_size:
        if record_subset:
            batches = batched(record_subset, batch_size)
        else:
            batches = batched(
                range(1, int(redcap_project.generate_next_record_name())), batch_size
            )

        # Consume batched iterator into a list
        batches = list(batches)
    else:
        batches = None

    # event instrument mappings tell us what instruments are part of what events
    event_instrument_mappings = redcap_project.export_instrument_event_mappings()

    # construct dictionary of this projects repeating instruments
    # {"event": [repeating_instrument_1, repeating_instrument_2, ...]}
    repeating_instruments = build_repeat_instruments_map(redcap_project)

    event_data, instrument_data = [], []
    for event in event_instrument_mappings:
        event_name = event.get("unique_event_name")
        form_name = event.get("form")

        if not event_name or not form_name:
            logger.info(
                f"Event name and/or form name were null for record {event.get(record_id_field)}"
            )
            continue

        # A record will be a `Form` class if it is repeating. All other records are
        # aggregated at the event level, so will be of class `Event`.
        event_repeat_instruments = repeating_instruments.get(event_name, None)
        if event_repeat_instruments and form_name in event_repeat_instruments:
            record_class = RecordClass.FORM
        else:
            record_class = RecordClass.EVENT

        records = []
        for record in export_records_in_batch(
            redcap_project=redcap_project,
            batches=batches,
            forms=[form_name],
            events=[event_name],
        ):
            record_id = record[record_id_field]

            # Fill empty event and/or form names
            if record["redcap_event_name"] != "":
                event_name = record["redcap_event_name"]
            if record["redcap_repeat_instrument"] != "":
                form_name = record["redcap_repeat_instrument"]

            # When a repeat instance is not provided, we can assume it is repeat instance 0.
            # TODO: Is this the desired behavior?
            if record["redcap_repeat_instance"] != "":
                repeat_instance = record["redcap_repeat_instance"]
            else:
                repeat_instance = 0

            # No need to store these fields within the data json object
            record.pop(record_id_field)
            record.pop("redcap_repeat_instance")

            records.append(
                {
                    "record_id": record_id,
                    "event_name": event_name,
                    "form_name": form_name,
                    "repeat_instance": repeat_instance,
                    "data": record,
                }
            )

        if record_class == RecordClass.FORM:
            instrument_data.extend(records)
        elif record_class == RecordClass.EVENT:
            event_data.extend(records)
        else:
            raise ValueError("Record class is invalid")

    return event_data, instrument_data
