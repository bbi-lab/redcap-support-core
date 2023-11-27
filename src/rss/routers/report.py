from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import tuple_, any_
from sqlalchemy.orm import Session, selectinload, Query

from typing import Union, Callable, Optional

from rss import deps
from rss.lib.authorization import (
    require_authorized_editor,
    require_authorized_viewer,
)
from rss.lib.exceptions.report import NoCustomCalculatorError
from rss.lib.querybuilder.filter import filter
from rss.models.event import Event
from rss.models.instrument import Instrument
from rss.models.project_event import ProjectEvent
from rss.models.project_field import ProjectField
from rss.models.project_instrument import ProjectInstrument
from rss.models.report import Report
from rss.models.user import User
from rss.view_models import event, instrument, report

# Router for handling all interactions with REDCap
router = APIRouter(
    prefix="/api/v1/reports",
    tags=["reports"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "",
    status_code=200,
    response_model=list[report.SavedReport],
    responses={404: {}},
)
def get_reports(
    db: Session = Depends(deps.get_db),
) -> list[Report]:
    """
    Lists all reports currently stored in the database.
    """
    return db.query(Report).all()


@router.post(
    "/",
    status_code=200,
    response_model=report.SavedReport,
    responses={404: {}},
)
def create_report(
    report_create: report.CreatedReport,
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_authorized_editor),
) -> Report:
    """
    Lists all reports currently stored in the database.
    """
    item = Report(**jsonable_encoder(report_create, by_alias=False))
    db.add(item)
    db.commit()
    return item


@router.delete(
    "/{uuid}",
    status_code=200,
    response_model=bool,
    responses={404: {}},
)
def delete_report(
    uuid: UUID,
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_authorized_editor),
) -> bool:
    """
    Lists all reports currently stored in the database.
    """
    item = db.query(Report).filter(Report.uuid == uuid).delete()

    db.commit()
    return bool(item)


@router.get(
    "/{uuid}",
    status_code=200,
    response_model=report.SavedReport,
    responses={404: {}},
)
def get_report(
    uuid: UUID,
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_authorized_viewer),
) -> Report:
    """
    Lists all reports currently stored in the database.
    """
    item = db.query(Report).filter(Report.uuid == uuid).one_or_none()

    if not item:
        raise HTTPException(404, "The requested report {uuid} could not be found.")

    return item


@router.put(
    "/{uuid}",
    status_code=200,
    response_model=report.SavedReport,
    responses={404: {}},
)
def modify_report(
    report_modify: report.ModifiedReport,
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_authorized_editor),
) -> Report:
    """
    Lists all reports currently stored in the database.
    """
    item = db.query(Report).filter(Report.uuid == report_modify.uuid).one_or_none()

    if not item:
        raise HTTPException(
            404, "The report requested for modification ({uuid}) could not be found."
        )

    for attr in vars(report_modify):
        item.__setattr__(attr, report_modify.__getattribute__(attr))

    db.add(item)
    db.commit()
    return item


# TODO: Should we consider merging event and instrument data fields? It probably depends on the
#       'axis of interest' for the user, so might be best to do that sort of thing on the client
#       side.

# TODO: Calculated fields for events (aggregated across event), and repeat instruments (aggregated
#       across repeat instruments). Do we want to aggregate repeat instance data across the repeat
#       instance number axis?

# TODO: Consider fetching record_ids / event_ids using this method, executing SELECTs against the DB
#       without an ORM, manually turning returned rows into dictionaries, and returning an ORJSONResponse
#       directly. When operating on large JSON responses, FASTAPIs native jsonable_encoder is called on
#       each object, dramatically reducing performance. If we could speed up this encoding and JSON dumping
#       step, we could help this endpoint out dramatically.


# TODO: Do we want to implement some sort of pagination to deal with the above...
@router.get(
    "/render/{uuid}",
    status_code=200,
    response_model=tuple[list[event.Event], list[instrument.Instrument]],
    # response_class=ORJSONResponse,
    responses={404: {}},
)
def render_report(
    uuid: UUID,
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_authorized_viewer),
    event_field_calculator: Optional[
        Callable[[Session, Query[Event], list[str]], list[event.Event]]
    ] = Depends(deps.get_event_calculator),
    instrument_field_calculator: Optional[
        Callable[[Session, Query[Instrument], list[str]], list[instrument.Instrument]]
    ] = Depends(deps.get_instrument_calculator),
) -> tuple[
    list[Union[Event, event.Event]], list[Union[Instrument, instrument.Instrument]]
]:
    """
    Lists all reports currently stored in the database.
    """
    item = db.query(Report).filter(Report.uuid == uuid).one_or_none()

    if not item:
        raise HTTPException(404, "The requested report {uuid} could not be found.")

    # subqueryload and selectinload have similar performance, and both are improvements over a
    # joinedload. Both are better than lazy loading in this scenario, since we are guaranteed to
    # have to load relationships while json encoding. We use selectin here because it is
    # compatible with batching, which may need to be implemented in the future.
    # See: https://docs.sqlalchemy.org/en/13/orm/loading_relationships.html#select-in-loading
    event_data = db.query(Event).options(selectinload("*"))
    instrument_data = db.query(Instrument).options(selectinload("*"))

    # TODO: Can we do this later so that the filter function can do less work?
    if item.filters:
        matching_rows = [(row[0],) for row in filter(db, item.filters)]

        # Subset by filtered record_ids up front to ease burden on future queries. Our
        # goal here isn't to prune the data fields into what the user wants, but rather
        # to only surface records that match user provided filters.
        event_data = event_data.filter(tuple_(Event.record_id) == (any_(matching_rows)))  # type: ignore
        instrument_data = instrument_data.filter(
            tuple_(Instrument.record_id) == (any_(matching_rows))  # type: ignore
        )

    # Filter by user requested records
    if item.records:
        event_data = event_data.filter(Event.record_id.in_(item.records))
        instrument_data = instrument_data.filter(Instrument.record_id.in_(item.records))

    # TODO: If a lower level filter is applied, we need to perform joins for the higher
    #       level fields as well. If only a higher level field is applied, we can stop
    #       at that field.
    if any([item.events, item.instruments, item.fields]):
        event_data = (
            event_data.join(ProjectEvent, onclause=ProjectEvent.id == Event.event_id)
            .join(
                ProjectInstrument, onclause=ProjectInstrument.id == Event.instrument_id
            )
            .join(ProjectField)
        )
        instrument_data = (
            instrument_data.join(
                ProjectEvent, onclause=ProjectEvent.id == Instrument.event_id
            )
            .join(
                ProjectInstrument,
                onclause=ProjectInstrument.id == Instrument.instrument_id,
            )
            .join(ProjectField)
        )

    # Filter by user requested instruments, events, and fields.
    if item.events:
        event_data = event_data.filter(ProjectEvent.name.in_(item.events))
        instrument_data = instrument_data.filter(ProjectEvent.name.in_(item.events))

    if item.instruments:
        event_data = event_data.filter(ProjectInstrument.name.in_(item.instruments))
        instrument_data = instrument_data.filter(
            ProjectInstrument.name.in_(item.instruments)
        )

    # TODO: Allow calculated fields to be included within filter logic.
    if item.calculated_event_fields and event_field_calculator is None:
        raise NoCustomCalculatorError(
            "Calculated event fields are defined on this report, but no field calculator was provided."
        )

    elif item.calculated_event_fields and event_field_calculator:
        calculated_event_data = event_field_calculator(
            db, event_data, item.calculated_event_fields
        )
    else:
        calculated_event_data = []

    if item.calculated_instrument_fields and instrument_field_calculator is None:
        raise NoCustomCalculatorError(
            "Calculated instrument fields are defined on this report, but no field calculator was provided."
        )

    elif item.calculated_instrument_fields and instrument_field_calculator:
        calculated_instrument_data = instrument_field_calculator(
            db, instrument_data, item.calculated_instrument_fields
        )
    else:
        calculated_instrument_data = []

    if item.fields:
        event_data = event_data.filter(ProjectField.name.in_(item.fields))
        instrument_data = instrument_data.filter(ProjectField.name.in_(item.fields))

        # Done filtering queries, so pull out field values. The report only needs to return
        # rows given by the `fields` subset.
        #
        # NOTE: This MUST be done last since this logic has the side-effect of modifying any `.data`
        #       field that it touches. Ie: If a calculated field relies on some event field that
        #       we are not returning to the user, the field will not be present in the data model
        #       if this logic occurs prior to the calculated field calculations.
        for row in event_data:
            row.data = {
                field: row.data[field] for field in item.fields if field in row.data
            }
        for row in instrument_data:
            row.data = {
                field: row.data[field] for field in item.fields if field in row.data
            }

    return [*event_data.all(), *calculated_event_data], [
        *instrument_data.all(),
        *calculated_instrument_data,
    ]


def format_report_field():
    pass
