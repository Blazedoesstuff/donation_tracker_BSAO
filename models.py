from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    unit = Column(String, nullable=False)
    storage_location = Column(String, nullable=True)
    low_stock_threshold = Column(Integer, default=10)
    is_active = Column(Boolean, default=True, nullable=False)

    donations = relationship(
        "Donation",
        back_populates="item"
    )

    distributions = relationship(
        "Distribution",
        back_populates="item"
    )


class Donation(Base):
    __tablename__ = "donations"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(
        Integer,
        ForeignKey("inventory.id"),
        nullable=False
    )
    donor = Column(String, nullable=False)
    quantity_received = Column(Integer, nullable=False)
    donation_date = Column(Date, nullable=False)
    expiration_date = Column(Date, nullable=True)

    item = relationship(
        "Inventory",
        back_populates="donations"
    )


class Distribution(Base):
    __tablename__ = "distributions"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(
        Integer,
        ForeignKey("inventory.id"),
        nullable=False
    )
    quantity_distributed = Column(Integer, nullable=False)
    distribution_date = Column(Date, nullable=False)
    notes = Column(String, nullable=True)

    item = relationship(
        "Inventory",
        back_populates="distributions"
    )