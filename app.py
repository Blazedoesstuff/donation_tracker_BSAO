import pandas as pd
import streamlit as st
from datetime import date, timedelta
from sqlalchemy import inspect, select, text

from database import Base, engine, get_session
from models import Inventory, Donation, Distribution


def initialize_database():
    """Create missing tables and add is_active to an existing SQLite database."""
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "inventory" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("inventory")}
        if "is_active" not in columns:
            with engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE inventory ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
                ))


initialize_database()

CATEGORIES = [
    "Canned Goods", "Grains", "Produce", "Dairy", "Protein",
    "Baby Supplies", "Menstrual Products", "Household Essentials", "Other",
]
UNITS = ["cans", "boxes", "bags", "items", "lbs", "packs", "bottles"]


def get_inventory(active_only=True):
    with get_session() as session:
        query = select(Inventory)
        if active_only:
            query = query.where(Inventory.is_active.is_(True))
        items = session.scalars(query.order_by(Inventory.name)).all()
        return [{
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "quantity": item.quantity,
            "unit": item.unit,
            "location": item.storage_location,
            "threshold": item.low_stock_threshold,
            "is_active": item.is_active,
        } for item in items]


def get_donations():
    with get_session() as session:
        donations = session.scalars(select(Donation).order_by(
            Donation.donation_date.desc(), Donation.id.desc()
        )).all()
        records = []
        for donation in donations:
            item = session.get(Inventory, donation.item_id)
            records.append({
                "Date": donation.donation_date,
                "Donor": donation.donor,
                "Item": item.name if item else "Unknown item",
                "Quantity": donation.quantity_received,
                "Expiration": donation.expiration_date,
            })
        return records


def get_distributions():
    with get_session() as session:
        distributions = session.scalars(select(Distribution).order_by(
            Distribution.distribution_date.desc(), Distribution.id.desc()
        )).all()
        records = []
        for distribution in distributions:
            item = session.get(Inventory, distribution.item_id)
            records.append({
                "Date": distribution.distribution_date,
                "Item": item.name if item else "Unknown item",
                "Quantity": distribution.quantity_distributed,
                "Unit": item.unit if item else "",
                "Notes": distribution.notes or "",
            })
        return records


def add_inventory_item(name, category, quantity, unit, location, threshold):
    name, unit = name.strip(), unit.strip()
    if not name or not unit:
        raise ValueError("Item name and unit are required.")
    if quantity < 0 or threshold < 0:
        raise ValueError("Quantities and thresholds cannot be negative.")
    with get_session() as session:
        session.add(Inventory(
            name=name, category=category, quantity=int(quantity), unit=unit,
            storage_location=location.strip() or None,
            low_stock_threshold=int(threshold), is_active=True,
        ))
        session.commit()


def update_inventory_item(item_id, name, category, quantity, unit, location, threshold):
    name, unit = name.strip(), unit.strip()
    if not name or not unit:
        raise ValueError("Item name and unit are required.")
    if quantity < 0 or threshold < 0:
        raise ValueError("Quantities and thresholds cannot be negative.")
    with get_session() as session:
        item = session.get(Inventory, item_id)
        if item is None:
            raise ValueError("Inventory item not found.")
        item.name = name
        item.category = category
        item.quantity = int(quantity)
        item.unit = unit
        item.storage_location = location.strip() or None
        item.low_stock_threshold = int(threshold)
        session.commit()


def deactivate_inventory_item(item_id):
    with get_session() as session:
        item = session.get(Inventory, item_id)
        if item is None:
            raise ValueError("Inventory item not found.")
        item.is_active = False
        session.commit()


def record_donation(item_id, donor, quantity, expiration_date=None):
    donor = donor.strip()
    if not donor:
        raise ValueError("Donor name is required.")
    if quantity <= 0:
        raise ValueError("Donation quantity must be positive.")
    with get_session() as session:
        item = session.get(Inventory, item_id)
        if item is None or not item.is_active:
            raise ValueError("Active inventory item not found.")
        item.quantity += int(quantity)
        session.add(Donation(
            item_id=item_id, donor=donor, quantity_received=int(quantity),
            donation_date=date.today(), expiration_date=expiration_date,
        ))
        session.commit()


def record_distribution(item_id, quantity, notes=""):
    if quantity <= 0:
        raise ValueError("Distribution quantity must be positive.")
    with get_session() as session:
        item = session.get(Inventory, item_id)
        if item is None or not item.is_active:
            raise ValueError("Active inventory item not found.")
        if item.quantity < quantity:
            raise ValueError(f"Only {item.quantity} {item.unit} available.")
        item.quantity -= int(quantity)
        session.add(Distribution(
            item_id=item_id, quantity_distributed=int(quantity),
            distribution_date=date.today(), notes=notes.strip() or None,
        ))
        session.commit()


# Streamlit setup and navigation
st.set_page_config(page_title="BSAO Pantry Tracker", page_icon="📦", layout="wide")
st.sidebar.title("BSAO Pantry")
st.sidebar.caption("Pantry Inventory Management")
page = st.sidebar.radio("Navigation", [
    "Dashboard", "Inventory", "Record Donation", "Donation History",
    "Distribute Supplies", "Distribution History",
])


if page == "Dashboard":
    st.title("📦 BSAO Pantry Dashboard")
    st.caption("Overview of current pantry supplies.")
    items = get_inventory()
    donations = get_donations()
    today = date.today()
    cutoff = today + timedelta(days=30)
    low_stock = [item for item in items if item["quantity"] <= item["threshold"]]
    with get_session() as session:
        dated_donations = session.scalars(select(Donation).where(
            Donation.expiration_date.is_not(None)
        )).all()
    expired_count = sum(1 for d in dated_donations if d.expiration_date < today)
    expiring_count = sum(1 for d in dated_donations if today <= d.expiration_date <= cutoff)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Inventory Items", len(items))
    c2.metric("Low-Stock Items", len(low_stock))
    c3.metric("Expiring Donation Records", expiring_count)
    c4.metric("Expired Donation Records", expired_count)
    st.subheader("Low-Stock Alerts")
    if low_stock:
        for item in low_stock:
            st.warning(f'{item["name"]}: {item["quantity"]} {item["unit"]} (threshold: {item["threshold"]})')
    else:
        st.success("No low-stock items.")
    st.subheader("Recent Donations")
    if donations:
        st.dataframe(donations[:5], use_container_width=True, hide_index=True)
    else:
        st.info("No donations have been recorded yet.")
    if expired_count:
        st.error("Some donation records have past expiration dates. Verify remaining stock before distribution.")
    elif expiring_count:
        st.warning("Some donation records expire within 30 days. Verify remaining quantities manually.")

elif page == "Inventory":
    st.title("Inventory Management")
    with st.expander("➕ Add a new inventory item"):
        with st.form("add_inventory_form", clear_on_submit=True):
            name = st.text_input("Item name")
            category = st.selectbox("Category", CATEGORIES)
            quantity = st.number_input("Initial quantity", min_value=0, step=1)
            unit = st.selectbox("Unit", UNITS)
            location = st.text_input("Storage location (optional)")
            threshold = st.number_input("Low-stock threshold", min_value=0, value=10, step=1)
            submitted = st.form_submit_button("Add item")
            if submitted:
                try:
                    add_inventory_item(name, category, quantity, unit, location, threshold)
                    st.success(f"{name.strip()} added.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    items = get_inventory()
    st.subheader("Current inventory")
    if items:
        search = st.text_input("Search by item name")
        filtered = [item for item in items if search.casefold() in item["name"].casefold()]
        st.dataframe([{
            "ID": i["id"], "Item": i["name"], "Category": i["category"],
            "Quantity": i["quantity"], "Unit": i["unit"],
            "Location": i["location"] or "Not specified",
            "Low-stock threshold": i["threshold"],
        } for i in filtered], use_container_width=True, hide_index=True)

        st.subheader("Edit or deactivate an item")
        options = {f'{i["name"]} (ID: {i["id"]})': i["id"] for i in items}
        label = st.selectbox("Select an item to edit", list(options.keys()))
        item_id = options[label]
        current = next(i for i in items if i["id"] == item_id)
        with st.form("edit_inventory_form"):
            new_name = st.text_input("Name", value=current["name"])
            cat_index = CATEGORIES.index(current["category"]) if current["category"] in CATEGORIES else 0
            new_category = st.selectbox("Category", CATEGORIES, index=cat_index)
            new_quantity = st.number_input("Current quantity", min_value=0, value=int(current["quantity"]), step=1)
            unit_index = UNITS.index(current["unit"]) if current["unit"] in UNITS else 0
            new_unit = st.selectbox("Unit", UNITS, index=unit_index)
            new_location = st.text_input("Storage location", value=current["location"] or "")
            new_threshold = st.number_input("Low-stock threshold", min_value=0, value=int(current["threshold"]), step=1)
            save = st.form_submit_button("Save changes")
            if save:
                try:
                    update_inventory_item(item_id, new_name, new_category, new_quantity, new_unit, new_location, new_threshold)
                    st.success("Inventory item updated.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        confirm = st.checkbox(f'I understand that "{current["name"]}" will be hidden from active inventory.', key=f"confirm_{item_id}")
        if st.button("Deactivate selected item", disabled=not confirm):
            try:
                deactivate_inventory_item(item_id)
                st.success("Item deactivated; its history is preserved.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    else:
        st.info("No active inventory items yet. Add your first item above.")

elif page == "Record Donation":
    st.title("Record a Donation")
    items = get_inventory()
    if not items:
        st.warning("Add an active inventory item before recording a donation.")
    else:
        options = {f'{i["name"]} (ID: {i["id"]}) — {i["quantity"]} {i["unit"]} in stock': i["id"] for i in items}
        with st.form("donation_form", clear_on_submit=True):
            label = st.selectbox("Item", list(options.keys()))
            donor = st.text_input("Donor or organization")
            quantity = st.number_input("Quantity received", min_value=1, step=1)
            has_expiration = st.checkbox("This donation has an expiration date")
            expiration = None
            if has_expiration:
                expiration = st.date_input("Expiration date", min_value=date.today(), value=date.today() + timedelta(days=30))
            submitted = st.form_submit_button("Record donation")
            if submitted:
                try:
                    record_donation(options[label], donor, quantity, expiration)
                    st.success("Donation recorded and stock updated.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

elif page == "Donation History":
    st.title("Donation History")
    donations = get_donations()
    if donations:
        st.dataframe(donations, use_container_width=True, hide_index=True)
        st.download_button("Download donation history CSV", pd.DataFrame(donations).to_csv(index=False).encode("utf-8"), file_name="bsao_donation_history.csv", mime="text/csv")
    else:
        st.info("No donation records found.")

elif page == "Distribute Supplies":
    st.title("Distribute Pantry Supplies")
    items = [i for i in get_inventory() if i["quantity"] > 0]
    if not items:
        st.info("No available stock to distribute.")
    else:
        options = {f'{i["name"]} — {i["quantity"]} {i["unit"]} available': i["id"] for i in items}
        with st.form("distribution_form", clear_on_submit=True):
            label = st.selectbox("Item", list(options.keys()))
            selected = next(i for i in items if i["id"] == options[label])
            quantity = st.number_input("Quantity distributed", min_value=1, max_value=int(selected["quantity"]), value=1, step=1)
            notes = st.text_input("Notes (optional)")
            submitted = st.form_submit_button("Record distribution")
            if submitted:
                try:
                    record_distribution(options[label], quantity, notes)
                    st.success("Distribution recorded and stock reduced.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

elif page == "Distribution History":
    st.title("Distribution History")
    distributions = get_distributions()
    if distributions:
        st.dataframe(distributions, use_container_width=True, hide_index=True)
        st.download_button("Download distribution history CSV", pd.DataFrame(distributions).to_csv(index=False).encode("utf-8"), file_name="bsao_distribution_history.csv", mime="text/csv")
    else:
        st.info("No distributions recorded yet.")
