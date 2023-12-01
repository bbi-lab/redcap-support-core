from typing import Optional
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from rss.lib.middlewares import request_object
from rss.deps import PaginatedParams


class Paginator:
    def __init__(self, session: Session, query: Select, page_params: PaginatedParams):
        self.session = session
        self.query = query
        self.params = page_params
        self.request = request_object.get()

        # computed later
        self.number_of_pages = 0
        self.next_page = ""
        self.previous_page = ""

    def _get_next_page(self) -> Optional[str]:
        if self.params.page >= self.number_of_pages:
            return

        url = self.request.url.include_query_params(page=self.params.page + 1)
        return str(url)

    def _get_previous_page(self) -> Optional[str]:
        if self.params.page == 1 or self.params.page > self.number_of_pages + 1:
            return

        url = self.request.url.include_query_params(page=self.params.page - 1)
        return str(url)

    def get_response(self) -> dict:
        count = self._get_total_count()
        return {
            "count": count,
            "pages": self._get_number_of_pages(count),
            "next_page": self._get_next_page(),
            "previous_page": self._get_previous_page(),
            "items": [
                row
                for row in self.session.scalars(
                    self.query.limit(self.params.limit).offset(self.params.offset)
                )
            ],
        }

    def _get_number_of_pages(self, count: int) -> int:
        rest = count % self.params.per_page
        quotient = count // self.params.per_page
        return max(1, quotient) if not rest else quotient + 1

    def _get_total_count(self) -> int:
        count = self.session.scalar(
            select(func.count()).select_from(self.query.subquery())
        )

        if not count:
            count = 0

        self.number_of_pages = self._get_number_of_pages(count)
        return count


def paginate(
    db: Session,
    query: Select,
    page_params: PaginatedParams,
) -> dict:
    paginator = Paginator(db, query, page_params)
    return paginator.get_response()
