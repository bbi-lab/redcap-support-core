from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from typing import Callable, Optional

from rss import deps
from rss.lib.authorization import (
    require_authorized_editor,
    require_authorized_viewer,
)
from rss.lib.pagination import paginate
from rss.lib.report import filter_item_fields, construct_report_select
from rss.models.event import Event
from rss.models.instrument import Instrument
from rss.models.report import Report
from rss.models.user import User
from rss.view_models import event, instrument, report, pagination

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
    "/events/{uuid}",
    status_code=200,
    response_model=pagination.PaginatedResponse[event.Event],
    responses={404: {}},
)
def render_report_events(
    uuid: UUID,
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_authorized_viewer),
    page_params: deps.PaginatedParams = Depends(),
    event_field_calculator: Optional[
        Callable[
            [Session, Select[tuple[Event]], list[str], deps.PaginatedParams],
            list[event.Event],
        ]
    ] = Depends(deps.get_event_calculator),
) -> pagination.PaginatedResponse[event.Event]:
    """
    Lists all reports currently stored in the database.
    """
    item = db.scalars(select(Report).where(Report.uuid == uuid)).one_or_none()

    if not item:
        raise HTTPException(404, "The requested report {uuid} could not be found.")

    event_select, calculated_events = construct_report_select(
        db, item, Event, event_field_calculator, page_params
    )
    response_data = paginate(db, event_select, page_params)

    # Done filtering queries, so pull out field values. The report only needs to return
    # rows given by the `fields` subset.
    #
    # NOTE: This MUST be done last since this logic has the side-effect of modifying any `.data`
    #       field that it touches. Ie: If a calculated field relies on some event field that
    #       we are not returning to the user, the field will not be present in the data model
    #       if this logic occurs prior to the calculated field calculations.
    if item.fields:
        filter_item_fields(item.fields, response_data)

    # Full response data is a combination of calculated and REDCap based events
    response_data["items"] = [*response_data["items"], *calculated_events]

    return response_data


@router.get(
    "/instruments/{uuid}",
    status_code=200,
    response_model=pagination.PaginatedResponse[instrument.Instrument],
    responses={404: {}},
)
def render_report_instruments(
    uuid: UUID,
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_authorized_viewer),
    page_params: deps.PaginatedParams = Depends(),
    instrument_field_calculator: Optional[
        Callable[
            [Session, Select[tuple[Instrument]], list[str], deps.PaginatedParams],
            list[instrument.Instrument],
        ]
    ] = Depends(deps.get_instrument_calculator),
) -> pagination.PaginatedResponse[instrument.Instrument]:
    """
    Lists all reports currently stored in the database.
    """
    item = db.scalars(select(Report).where(Report.uuid == uuid)).one_or_none()

    if not item:
        raise HTTPException(404, "The requested report {uuid} could not be found.")

    instrument_select, calculated_instruments = construct_report_select(
        db, item, Instrument, instrument_field_calculator, page_params
    )
    response_data = paginate(db, instrument_select, page_params)

    # Done filtering queries, so pull out field values. The report only needs to return
    # rows given by the `fields` subset.
    #
    # NOTE: This MUST be done last since this logic has the side-effect of modifying any `.data`
    #       field that it touches. Ie: If a calculated field relies on some event field that
    #       we are not returning to the user, the field will not be present in the data model
    #       if this logic occurs prior to the calculated field calculations.
    if item.fields:
        filter_item_fields(item.fields, response_data)

    # Full response data is a combination of calculated and REDCap based events
    response_data["items"] = [*response_data["items"], *calculated_instruments]

    return response_data
