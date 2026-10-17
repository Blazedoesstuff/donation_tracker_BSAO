
from datetime import date

from sqlalchemy import (
    Date,
    ForeignKey,
    Integer,
    String, true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )

    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    unit: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    storage_location: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    low_stock_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10
    )

    donations: Mapped[list["Donation"]] = relationship(
        back_populates="item"

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False
    )
    )


class Donation(Base):
    __tablename__ = "donations"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    item_id: Mapped[int] = mapped_column(
        ForeignKey("inventory.id"), nullable=False
    )

    donor: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    quantity_received: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    donation_date: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today
    )

    expiration_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )

    item: Mapped["Inventory"] = relationship(
        back_populates="donations"
    )

    from datetime import date

    from sqlalchemy import Date, ForeignKey, Integer, String
    from sqlalchemy.orm import Mapped, mapped_column, relationship

    class Distribution(Base):
        __tablename__ = "distributions"

        id: Mapped[int] = mapped_column(
            Integer, primary_key=True, index=True
        )

        item_id: Mapped[int] = mapped_column(
            ForeignKey("inventory.id"), nullable=False
        )

        quantity_distributed: Mapped[int] = mapped_column(
            Integer, nullable=False
        )

        distribution_date: Mapped[date] = mapped_column(
            Date, nullable=False, default=date.today
        )

        notes: Mapped[str | None] = mapped_column(
            String(250), nullable=True
        )

        item: Mapped["Inventory"] = relationship()
