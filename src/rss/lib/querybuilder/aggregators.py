from typing import Literal, get_args, Union

from sqlalchemy.orm import Session

from .operators import evaluate_criterion

Agregator = Literal["all", "any"]
VALID_AGGREGATORS: tuple[Agregator, ...] = get_args(Agregator)


def aggregate_criterion(
    db: Session,
    operation: Agregator,
    criterions: list[dict[str, Union[bool, int, str, None]]],
    records: set[tuple[int]],
) -> set[tuple[int]]:
    """
    Aggregates a list of criterions using the appropriate set aggregation operation. Criterions
    should be of the form:
    ```
    criterions = [
        {"field": "instrument.field", "operator": Operator, "value": <some_value>},
        ...
    ]
    ```

    This function also requires a query of the relationships between fields and the instrument
    which contains them in addtion to a set of aggregated (record_id, event_id) tuples which
    indicate rows in the `db` that have thus far been filtered so they are included in our query.
    """
    for idx, criterion in enumerate(criterions):
        results = evaluate_criterion(db, criterion)

        # Update record set aggregation based on the provided aggregator.
        # `operation` is guaranteed to be an `Agregator`. The first result
        # set in an `any` operation is treated differently, since we want
        # it to form the basis for future set updates.
        if operation == "any" and idx == 0:
            records = set(results)
        elif operation == "any":
            records.update(results)
        elif operation == "all":
            records.intersection_update(results)

    return records
