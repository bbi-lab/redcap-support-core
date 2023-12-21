from fastapi import APIRouter, Depends
import logging
import math
from redcap.project import Project
from sqlalchemy.orm import Session

from rss import deps
from rss.lib.authorization import require_authorized_admin
from rss.lib.redcap_interface import (
    build_event_map,
    build_form_field_map,
    build_repeat_instruments_map,
    relational_redcap,
    relational_refresh,
)
from rss.models.event import Event
from rss.models.instrument import Instrument
from rss.models.project import (
    ProjectArm,
    ProjectEvent,
    ProjectInstrument,
    ProjectField,
    event_instrument_association,
)
from rss.models.user import User
from rss.view_models import project

# Router for handling all interactions with REDCap
router = APIRouter(
    prefix="/api/v1/project",
    tags=["project", "redcap"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger()
logger.setLevel("INFO")


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
    batch_size = math.ceil(next_record / 20)

    logger.info(f"Refreshing {next_record} records in batches of {batch_size}.")

    relational_redcap(redcap_project, db)
    db.commit()

    logger.info("Done building project structure. Clearing project data.")

    db.query(Event).delete()
    db.query(Instrument).delete()
    db.flush()

    logger.info("Done clearing existing project data. Refreshing data.")

    # Commit as we go within this function, to avoid OOM errors on large transactions.
    relational_refresh(redcap_project, db, batch_size)
    db.commit()
    return next_record


# TODO: Single record refresh?
