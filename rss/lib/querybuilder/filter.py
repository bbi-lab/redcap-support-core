from typing import Union
from sqlalchemy.orm import Session

from rss.models.event import Event
from .aggregators import aggregate_criterion, VALID_AGGREGATORS

# Type definition for criterions list
criterions = list[dict[str, Union[str, int, bool, None]]]


def filter(
    db: Session,
    filters: dict[
        str,
        Union[dict, criterions],
    ],
) -> set[tuple[int]]:
    """
    Constructs a query for the provided filters, which should be of the form
    ```
    filters = {
        Aggregator: [
            {"field": "instrument.field", "operator": Operator, "value": <some_value>},
            {"field": "instrument.field", "operator": Operator, "value": <some_value>},
            criterion3,
            criterion4,
            ...
        ],
        Aggregator: [
            criterion1,
            criterion2,
            ...
        ]
    }

    Recursively evaluate aggregation filters, aggregate and evaluate criterion within an
    individual aggregation filter.
    ```
    """
    # TODO: if we perform this distinct on the records a user is pre-emptively subsetting,
    #       we could reduce the work this function needs to perform. Ie: pass a version of
    #       this query into this function.
    # TODO: Ensure this set of tuples is not always distinct because it is technically 'Rows'
    records = set(db.query(Event.record_id).distinct().tuples().all())

    for aggregator, criterions in filters.items():
        if aggregator in VALID_AGGREGATORS:
            # Recurse if the criterions are a filter object dictionary
            if isinstance(criterions, dict):
                records.intersection_update(filter(db, criterions))
            else:
                records.intersection_update(
                    aggregate_criterion(db, aggregator, criterions, records)
                )

        else:
            raise ValueError(
                f"Aggregator {aggregator} not in accepted aggregators: {VALID_AGGREGATORS}"
            )

    return records
