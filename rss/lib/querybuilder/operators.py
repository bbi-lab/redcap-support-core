from typing import Literal, get_args, Union

from sqlalchemy import Boolean, Integer
from sqlalchemy.orm import Session
from sqlalchemy.orm.query import Query

from rss.models.event import Event
from rss.models.instrument import Instrument
from rss.models.project_field import ProjectField
from rss.models.project_instrument import ProjectInstrument

# add aggregators/operators here as they become valid
Operator = Literal["==", "!=", ">=", "<=", ">", "<"]
VALID_OPERATORS: tuple[Operator, ...] = get_args(Operator)

OPERATORS = {
    "==": lambda model_field, field_value: model_field == field_value,
    "!=": lambda model_field, field_value: model_field != field_value,
    ">=": lambda model_field, field_value: model_field >= field_value,
    "<=": lambda model_field, field_value: model_field <= field_value,
    "<": lambda model_field, field_value: model_field < field_value,
    ">": lambda model_field, field_value: model_field > field_value,
}


def _extract_path(path: str) -> tuple[str, str]:
    """
    Extracts the path to the field into its base components. Path should be of the form `instrument.field`,
    where the `instrument` part is the name of an instrument and `field` is the name of some field within
    that instrument.
    """
    paths = path.split(".")

    if len(paths) != 2:
        raise ValueError(
            "REDCap path names should contain an instrument and field separated by a periods: `instrument.field`"
        )

    return paths[0], paths[1]


def _induce_model(
    field_relationships: Query[ProjectInstrument], field_name: str
) -> Union[type[Event], type[Instrument]]:
    """
    Induce which model a provided field belongs to based on whether the instrument
    it is associated with is repeatable.

    - A field will appear in some data object of the `Event` model when the instrument
      the field belongs to is not repeatable.
    - A field will appear in some data object of the `Instrument` model when the
      instrument  the field belongs to is repeatable.
    """
    is_event = (
        not field_relationships.filter(ProjectField.name == field_name).one().repeating
    )
    return Event if is_event else Instrument


def compare(
    db: Session,
    operator: str,
    instrument: ProjectInstrument,
    field: str,
    field_value: Union[str, bool, int, None],
    model: Union[type[Event], type[Instrument]],
):
    # Our goal is to find all record_id / event pairs that contain a field that passes
    # the provided criterion.
    if operator is None:
        raise ValueError(
            f"Criterion dictionary must contain a valid operator, not `None`: {VALID_OPERATORS}"
        )
    elif operator not in VALID_OPERATORS:
        raise ValueError(
            f"Operator {operator} not in accepted operators: {VALID_OPERATORS}"
        )
    else:
        comparison = OPERATORS[operator]

    # TODO: Worried about boolean and integer casts when data is missing, as we will have
    #       Integer("") or Bool(""). The latter is falsy, but the former may evaluate to
    #       some undesirable number or raise an error.
    if isinstance(field_value, bool):
        results = (
            db.query(model.record_id)
            .filter(
                model.instrument_id == instrument.id,
                comparison(model.data[field].astext.cast(Boolean), field_value),
            )
            .distinct()
            .tuples()
            .all()
        )
    elif isinstance(field_value, int):
        results = (
            db.query(model.record_id)
            .filter(
                model.instrument_id == instrument.id,
                comparison(model.data[field].astext.cast(Integer), field_value),
            )
            .distinct()
            .tuples()
            .all()
        )
    else:
        results = (
            db.query(model.record_id)
            .filter(
                model.instrument_id == instrument.id,
                comparison(model.data[field].astext, field_value),
            )
            .distinct()
            .tuples()
            .all()
        )

    return results


def evaluate_criterion(
    db: Session, criterion: dict[str, Union[str, bool, int, None]]
) -> list[tuple[int]]:
    """
    Evaluate a criterion dictionary against the database, returning any records
    from the db that pass the filter defined by the criterion dictionary.

    criterion:

    """
    # Fetch and validate field type
    field_path = criterion.get("field")
    if field_path is None:
        raise ValueError(
            "The `field` field in a criterion dictionary is required, and can not be `None`"
        )
    elif not isinstance(field_path, str):
        raise ValueError(
            "The `field` field in a criterion dictionary should be a string in the form `instrument.field`."
        )
    else:
        instrument, field = _extract_path(field_path)

    # Fetch and validate operator type
    field_operator = criterion.get("operator")
    if field_operator is None:
        raise ValueError(
            "The `operator` field in a criterion dictionary is required and can not be `None`."
        )
    elif not isinstance(field_operator, str):
        raise ValueError(
            "The `operator` field in a criterion dictionary should be a string."
        )

    # Fetch the instrument object to which the requested field belongs
    instrument = (
        db.query(ProjectInstrument).filter(ProjectInstrument.name == instrument).one()
    )

    # TODO: Ensure this properly handles all desired types, including None types
    field_value = criterion.get("value")

    fields = db.query(ProjectInstrument).join(ProjectField)
    model = _induce_model(fields, field)

    results = compare(
        db=db,
        operator=field_operator,
        instrument=instrument,
        field=field,
        field_value=field_value,
        model=model,
    )

    return [(row[0],) for row in results]
