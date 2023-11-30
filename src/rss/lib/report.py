from sqlalchemy import tuple_, any_, select, Select
from sqlalchemy.orm import Session, selectinload

from typing import Union, Callable

from rss import deps
from rss.lib.exceptions.report import NoCustomCalculatorError
from rss.lib.querybuilder.filter import filter
from rss.models.event import Event
from rss.models.instrument import Instrument
from rss.models.project_event import ProjectEvent
from rss.models.project_field import ProjectField
from rss.models.project_instrument import ProjectInstrument
from rss.models.report import Report
from rss.view_models import event, instrument


def construct_report_select(
    db: Session,
    report: Report,
    model: type[Union[Event, Instrument]],
    field_calculator: Callable[
        [
            Session,
            Select[tuple[Union[Instrument, Event]]],
            list[str],
            deps.PaginatedParams,
        ],
        list[Union[instrument.Instrument, event.Event]],
    ],
    page_params: deps.PaginatedParams,
) -> tuple[
    Select[tuple[Union[Event, Instrument]]],
    list[Union[instrument.Instrument, event.Event]],
]:
    # subqueryload and selectinload have similar performance, and both are improvements over a
    # joinedload. Both are better than lazy loading in this scenario, since we are guaranteed to
    # have to load relationships while json encoding. We use selectin here because it is
    # compatible with batching, which may need to be implemented in the future.
    # See: https://docs.sqlalchemy.org/en/13/orm/loading_relationships.html#select-in-loading
    report_query = select(model).options(selectinload("*"))

    # TODO: Can we do this later so that the filter function can do less work? (probably not)
    if report.filters:
        matching_rows = [(row[0],) for row in filter(db, report.filters)]

        # Subset by filtered record_ids up front to ease burden on future queries. Our
        # goal here isn't to prune the data fields into what the user wants, but rather
        # to only surface records that match user provided filters.
        report_query = report_query.where(
            tuple_(model.record_id) == (any_(matching_rows))  # type: ignore
        )

    # Filter by user requested records
    if report.records:
        report_query = report_query.where(model.record_id.in_(report.records))

    # TODO: If a lower level filter is applied, we need to perform joins for the higher
    #       level fields as well. If only a higher level field is applied, we can stop
    #       at that field.
    if any([report.events, report.instruments, report.fields]):
        report_query = (
            report_query.join(ProjectEvent, onclause=ProjectEvent.id == model.event_id)
            .join(
                ProjectInstrument,
                onclause=ProjectInstrument.id == model.instrument_id,
            )
            .join(ProjectField)
        )

    # Filter by user requested instruments, events, and fields.
    if report.events:
        report_query = report_query.where(ProjectEvent.name.in_(report.events))

    if report.instruments:
        report_query = report_query.where(
            ProjectInstrument.name.in_(report.instruments)
        )

    # TODO: This method of calculating report data on paginated queries might have the result of
    #       calculating the same data twice if some events are within one batch and some are within
    #       another. We should paginated via record_ids, rather than pk ids/rows.
    if report.calculated_instrument_fields and field_calculator is None:
        raise NoCustomCalculatorError(
            "Calculated instrument fields are defined on this report, but no field calculator was provided."
        )

    elif model == Event and report.calculated_event_fields and field_calculator:
        calculated_report_data = field_calculator(
            db, report_query, report.calculated_event_fields, page_params
        )
    elif (
        model == Instrument and report.calculated_instrument_fields and field_calculator
    ):
        calculated_report_data = field_calculator(
            db, report_query, report.calculated_instrument_fields, page_params
        )
    else:
        calculated_report_data = []

    if report.fields:
        report_query = report_query.where(ProjectField.name.in_(report.fields))

    return report_query, calculated_report_data


def filter_item_fields(item_fields: list[str], response_data: dict):
    for row in response_data["items"]:
        row.data = {
            field: row.data[field] for field in item_fields if field in row.data
        }
