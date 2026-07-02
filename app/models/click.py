from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Click(Base):
    """One row per redirect (analytics event), written by the analytics worker
    draining the Redis stream — never on the request hot path.
    """

    __tablename__ = "clicks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    short_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    referrer: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Composite index accelerates the stats aggregation (count/last per code).
    __table_args__ = (Index("ix_clicks_code_time", "short_code", "clicked_at"),)
