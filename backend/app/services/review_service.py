"""Domain service for handling customer review creation, retrieval, and filtering."""

from collections.abc import Iterator

from sqlalchemy import ColumnElement, Select, case, func, select
from sqlalchemy.orm import Session

from app.models.review import AnalysisStatus, Priority, Review
from app.schemas.review import (
    AdminReviewDto,
    CreateReviewRequest,
    PaginatedResponse,
    ReviewDto,
    ReviewQuery,
    ReviewStatistics,
)

#: Number of rows fetched per database round-trip while streaming.
_BATCH_SIZE = 500

#: Numeric weight of every priority level, used to sort by urgency.
#:
#: The column stores the priority as a string, so a plain ``ORDER BY``
#: would sort it alphabetically ("High" < "Low" < "Medium") instead of by
#: urgency.  The mapping below turns the string into a number that can be
#: ordered the way a support operator expects it.  A review that has not
#: been analysed yet has no priority at all and stays ``NULL``, which keeps
#: it at the end of the list in both sort directions.
_PRIORITY_ORDER = case(
    (Review.priority == Priority.HIGH.value, 3),
    (Review.priority == Priority.MEDIUM.value, 2),
    (Review.priority == Priority.LOW.value, 1),
    else_=None,
)


class ReviewService:
    """Service providing business logic for review lifecycle and administrative queries."""

    def __init__(self, db: Session) -> None:
        """Initialize ReviewService with a SQLAlchemy database session."""
        self.db = db

    def create(self, request: CreateReviewRequest) -> ReviewDto:
        """Persist a new customer review with a Pending handling status.

        Args:
            request: Customer review submission data.

        Returns:
            The created review DTO.
        """
        review = Review(
            author_name=request.author_name.strip(),
            email=request.email.strip(),
            text=request.text.strip(),
            analysis_status=AnalysisStatus.PENDING.value,
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return self._map_to_dto(review)

    def get_all_paginated(self, query: ReviewQuery, page: int = 1, page_size: int = 10) -> PaginatedResponse:
        """Query and filter reviews returning paginated structure.

        Args:
            query: Filter and sort criteria.
            page: Current page (1-based index).
            page_size: Maximum items per page.

        Returns:
            PaginatedResponse with page metadata and items.
        """
        filters = self._build_filters(query)
        total = self.db.execute(select(func.count(Review.id)).where(*filters)).scalar() or 0

        stmt = self._build_query_stmt(query)
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        reviews = self.db.execute(stmt).scalars().all()
        items = [self._map_to_admin_dto(review) for review in reviews]

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def _build_filters(query: ReviewQuery) -> list[ColumnElement[bool]]:
        """Build the WHERE clauses shared by the count and the item query.

        Args:
            query: Filter and sort criteria.

        Returns:
            A list of SQLAlchemy boolean expressions.
        """
        filters: list[ColumnElement[bool]] = []

        if query.status:
            filters.append(Review.analysis_status == query.status.value)

        if query.rating:
            filters.append(Review.rating == query.rating)

        if query.priority:
            filters.append(Review.priority == query.priority.value)

        return filters

    def _build_query_stmt(self, query: ReviewQuery) -> Select[Review]:
        """Construct the filtered and ordered select statement.

        Args:
            query: Filter and sort criteria.

        Returns:
            A SELECT statement over the reviews table.
        """
        stmt = select(Review).where(*self._build_filters(query))

        if query.sort_by and query.sort_by.lower() == "priority":
            order = _PRIORITY_ORDER.desc().nulls_last() if query.descending else _PRIORITY_ORDER.asc().nulls_last()
            stmt = stmt.order_by(order)
        elif query.sort_by and query.sort_by.lower() == "rating":
            order = Review.rating.desc().nulls_last() if query.descending else Review.rating.asc().nulls_last()
            stmt = stmt.order_by(order)
        else:
            order = Review.created_at_utc.desc() if query.descending else Review.created_at_utc.asc()
            stmt = stmt.order_by(order)

        # Many reviews share a rating or a priority, and the database does
        # not keep a stable order among equal values: across OFFSET pages a
        # review could then appear twice or not at all.  The newest-first
        # date and the id break every tie deterministically.
        return stmt.order_by(Review.created_at_utc.desc(), Review.id)

    def stream_all(self, query: ReviewQuery) -> Iterator[AdminReviewDto]:
        """Yield every review matching the filter, one row at a time.

        The rows are fetched in batches so that a large dataset does not
        have to be loaded into memory at once.  This is what the CSV
        export endpoint streams to the client.

        Args:
            query: Filter and sort criteria.

        Yields:
            One AdminReviewDto per matching review.
        """
        stmt = self._build_query_stmt(query)

        for review in self.db.execute(stmt.execution_options(yield_per=_BATCH_SIZE)).scalars():
            yield self._map_to_admin_dto(review)

    def get_by_id(self, id: str) -> AdminReviewDto | None:
        """Retrieve full review details by its unique identifier (admin use).

        Args:
            id: Unique review UUID.

        Returns:
            AdminReviewDto if found, otherwise None.
        """
        review = self.db.execute(select(Review).where(Review.id == id)).scalar_one_or_none()

        if not review:
            return None

        return self._map_to_admin_dto(review)

    def update_status(self, id: str, status: AnalysisStatus) -> AdminReviewDto | None:
        """Update the operator-managed handling status of a review.

        Args:
            id: Unique review UUID.
            status: New review handling status.

        Returns:
            Updated AdminReviewDto if found, otherwise None.
        """
        review = self.db.execute(select(Review).where(Review.id == id)).scalar_one_or_none()

        if not review:
            return None

        review.analysis_status = status.value
        self.db.commit()
        self.db.refresh(review)
        return self._map_to_admin_dto(review)

    @staticmethod
    def _map_to_dto(review: Review) -> ReviewDto:
        """Map a SQLAlchemy Review model to public ReviewDto."""
        return ReviewDto.model_validate(review)

    @staticmethod
    def _map_to_admin_dto(review: Review) -> AdminReviewDto:
        """Map a SQLAlchemy Review model to AdminReviewDto."""
        return AdminReviewDto.model_validate(review)

    def get_statistics(self) -> ReviewStatistics:
        """Compute aggregate statistics over the whole review dataset.

        The ratings distribution and the average rating are computed with a
        single conditional-aggregation query instead of one ``COUNT`` per
        rating.  Everything runs as plain SQL aggregates, so no additional
        dependency is required.

        Returns:
            The review counts per star rating, the overall total and the
            average rating.
        """
        row = self.db.execute(
            select(
                func.sum(case((Review.rating == 1, 1), else_=0)).label("rating_1"),
                func.sum(case((Review.rating == 2, 1), else_=0)).label("rating_2"),
                func.sum(case((Review.rating == 3, 1), else_=0)).label("rating_3"),
                func.sum(case((Review.rating == 4, 1), else_=0)).label("rating_4"),
                func.sum(case((Review.rating == 5, 1), else_=0)).label("rating_5"),
                func.count(Review.id).label("total"),
                func.avg(Review.rating).label("avg_rating"),
            )
        ).one()

        return ReviewStatistics(
            rating_1=row.rating_1 or 0,
            rating_2=row.rating_2 or 0,
            rating_3=row.rating_3 or 0,
            rating_4=row.rating_4 or 0,
            rating_5=row.rating_5 or 0,
            total=row.total or 0,
            avg_rating=round(float(row.avg_rating), 2) if row.avg_rating else 0.0,
        )
