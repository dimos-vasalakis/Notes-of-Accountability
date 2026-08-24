from datetime import datetime

from sqlalchemy import DateTime, func
from sqlmodel import Field


class TimestampMixin:
    created_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )
