"""业务数据的数据库模型。实体与字段的正式设计在 V1.2。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from sales_ops.db import Base


class Customer(Base):
    __tablename__ = "customer"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
