
from datetime import date

from sqlalchemy import select

from database import Base, engine, get_session
from models import Inventory, Donation


def initialize_database():
    migrate_database()
    print("BSAO database initialized.")


def add_inventory_item(
    name, category, quantity, unit, threshold=10
):
    """Add a new item to the pantry."""
    if quantity < 0 or threshold < 0:
        raise ValueError("Quantities cannot be negative.")

    with get_session() as session:
        item = Inventory(
            name=name,
            category=category,
            quantity=quantity,
            unit=unit,
            low_stock_threshold=threshold,
        )

        session.add(item)
        session.commit()
        session.refresh(item)

        print(f"Added {item.name}, ID: {item.id}")
        return item.id


def record_donation(
    item_id, donor, quantity, expiration_date=None
):
    """Record a donation and update inventory."""
    if quantity <= 0:
        raise ValueError("Donation quantity must be positive.")

    with get_session() as session:
        item = session.get(Inventory, item_id)

        if item is None:
            raise ValueError("Inventory item not found.")

        donation = Donation(
            item_id=item_id,
            donor=donor,
            quantity_received=quantity,
            donation_date=date.today(),
            expiration_date=expiration_date,
        )

        item.quantity += quantity

        session.add(donation)
        session.commit()

        print(f"Received {quantity} {item.unit} of {item.name}.")


def show_inventory():
    """Display current inventory and low-stock warnings."""
    with get_session() as session:
        items = session.scalars(
            select(Inventory).order_by(Inventory.name)
        ).all()

        print("\n--- BSAO Pantry Inventory ---")

        for item in items:
            print(
                f"{item.name}: {item.quantity} {item.unit}"
            )

            if item.quantity <= item.low_stock_threshold:
                print("  WARNING: Low stock")


def show_donations():
    """Display donation history."""
    with get_session() as session:
        donations = session.scalars(
            select(Donation).order_by(Donation.id)
        ).all()

        print("\n--- Donation History ---")

        for donation in donations:
            item = session.get(Inventory, donation.item_id)

            print(
                f"{donation.donor} donated "
                f"{donation.quantity_received} "
                f"of {item.name} on {donation.donation_date}"
            )


if __name__ == "__main__":
    initialize_database()

    # Create a sample item only if it doesn't already exist.
    with get_session() as session:
        item = session.scalar(
            select(Inventory).where(
                Inventory.name == "Canned Beans"
            )
        )

    if item is None:
        add_inventory_item(
            name="Canned Beans",
            category="Canned Goods",
            quantity=0,
            unit="cans",
            threshold=10,
        )

    # Show saved information without repeatedly
    # inserting the same sample donation.
    show_inventory()
    show_donations()

from sqlalchemy import inspect, text


def migrate_database():
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    columns = {
        column["name"]
        for column in inspector.get_columns("inventory")
    }

    if "is_active" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE inventory "
                    "ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
                )
            )

    print("Database migration complete.")
