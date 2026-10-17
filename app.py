
import streamlit as st
from datetime import date, timedelta
from sqlalchemy import select

from database import Base, engine, get_session
from models import Inventory, Donation, Distribution


# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="BSAO Pantry Tracker",
    page_icon="📦",
    layout="wide"
)

# Create database tables if needed
Base.metadata.create_all(bind=engine)


# -----------------------------
# Helper functions
# -----------------------------

def get_inventory():
    with get_session() as session:
        items = session.scalars(
            select(Inventory)
            .where(Inventory.is_active.is_(True))
            .order_by(Inventory.name)
        ).all()

        return [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "quantity": item.quantity,
                "unit": item.unit,
                "location": item.storage_location,
                "threshold": item.low_stock_threshold,
            }
            for item in items
        ]



def get_donations():
    with get_session() as session:
        donations = session.scalars(
            select(Donation).order_by(
                Donation.donation_date.desc(),
                Donation.id.desc()
            )
        ).all()

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


def add_inventory_item(
    name, category, quantity, unit, location, threshold
):
    with get_session() as session:
        item = Inventory(
            name=name.strip(),
            category=category,
            quantity=quantity,
            unit=unit,
            storage_location=location.strip() or None,
            low_stock_threshold=threshold,
        )

        session.add(item)
        session.commit()


def record_donation(
    item_id, donor, quantity, expiration_date
):
    with get_session() as session:
        item = session.get(Inventory, item_id)

        if item is None:
            raise ValueError("The selected item no longer exists.")

        # Update stock and record the donation together.
        item.quantity += quantity

        donation = Donation(
            item_id=item_id,
            donor=donor.strip(),
            quantity_received=quantity,
            donation_date=date.today(),
            expiration_date=expiration_date,
        )

        session.add(donation)
        session.commit()


# -----------------------------
# Sidebar navigation
# -----------------------------
st.sidebar.title("BSAO Pantry")
st.sidebar.caption("Pantry Inventory Management")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Inventory",
        "Record Donation",
        "Donation History",
        "Distribute Supplies",
        "Distribution History",
    ]
)

# -----------------------------
# Dashboard
# -----------------------------
if page == "Dashboard":
    st.title("📦 BSAO Pantry Dashboard")
    st.write("Overview of current pantry supplies.")

    items = get_inventory()
    donations = get_donations()

    total_products = len(items)
    low_stock = [
        item for item in items
        if item["quantity"] <= item["threshold"]
    ]

    expiring_count = 0
    expired_count = 0
    cutoff = date.today() + timedelta(days=30)

    with get_session() as session:
        batches = session.scalars(
            select(Donation).where(
                Donation.expiration_date.is_not(None)
            )
        ).all()

        for batch in batches:
            if batch.expiration_date < date.today():
                expired_count += 1
            elif batch.expiration_date <= cutoff:
                expiring_count += 1

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Inventory Items", total_products)
    col2.metric("Low Stock", len(low_stock))
    col3.metric("Expiring Batches", expiring_count)
    col4.metric("Expired Batches", expired_count)

    st.subheader("Low-Stock Alerts")

    if low_stock:
        for item in low_stock:
            st.warning(
                f'{item["name"]}: {item["quantity"]} '
                f'{item["unit"]} remaining '
                f'(threshold: {item["threshold"]})'
            )
    else:
        st.success("No low-stock items.")

    st.subheader("Recent Donations")

    if donations:
        st.dataframe(
            donations[:5],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No donations have been recorded yet.")


# -----------------------------
# Inventory page
# -----------------------------

st.subheader("Edit or deactivate an item")

with get_session() as session:
    active_items = session.scalars(
        select(Inventory)
        .where(Inventory.is_active.is_(True))
        .order_by(Inventory.name)
    ).all()

    options = {
        f"{item.name} (ID: {item.id})": item.id
        for item in active_items
    }

if options:
    selected = st.selectbox(
        "Select an item",
        list(options.keys()),
        key="edit_item_select"
    )

    item_id = options[selected]

    with get_session() as session:
        item = session.get(Inventory, item_id)

        current = {
            "name": item.name,
            "category": item.category,
            "quantity": item.quantity,
            "unit": item.unit,
            "location": item.storage_location or "",
            "threshold": item.low_stock_threshold,
        }

    with st.form("edit_inventory_form"):
        new_name = st.text_input(
            "Name", value=current["name"]
        )
        new_category = st.selectbox(
            "Category",
            [
                "Canned Goods", "Grains", "Produce",
                "Dairy", "Protein", "Baby Supplies",
                "Menstrual Products",
                "Household Essentials", "Other"
            ],
            index=[
                "Canned Goods", "Grains", "Produce",
                "Dairy", "Protein", "Baby Supplies",
                "Menstrual Products",
                "Household Essentials", "Other"
            ].index(current["category"])
            if current["category"] in [
                "Canned Goods", "Grains", "Produce",
                "Dairy", "Protein", "Baby Supplies",
                "Menstrual Products",
                "Household Essentials", "Other"
            ] else 0
        )
        new_quantity = st.number_input(
            "Current Quantity",
            min_value=0,
            value=current["quantity"]
        )
        new_unit = st.text_input(
            "Unit", value=current["unit"]
        )
        new_location = st.text_input(
            "Storage Location",
            value=current["location"]
        )
        new_threshold = st.number_input(
            "Low-Stock Threshold",
            min_value=0,
            value=current["threshold"]
        )

        save = st.form_submit_button("Save Changes")

        if save:
            if not new_name.strip() or not new_unit.strip():
                st.error("Name and unit are required.")
            else:
                update_inventory_item(
                    item_id,
                    new_name,
                    new_category,
                    int(new_quantity),
                    new_unit,
                    new_location,
                    int(new_threshold),
                )
                st.success("Inventory updated!")
                st.rerun()

    if st.button("Deactivate Selected Item"):
        deactivate_inventory_item(item_id)
        st.success("Item deactivated.")
        st.rerun()
else:
    st.info("No active inventory items to edit.")

    items = get_inventory()

    if items:
        search = st.text_input("Search inventory")
        .where(Inventory.is_active.is_(True))

        filtered = [
            item for item in items
            if search.lower() in item["name"].lower()
        ]

        st.dataframe(
            [
                {
                    "ID": item["id"],
                    "Item": item["name"],
                    "Category": item["category"],
                    "Quantity": item["quantity"],
                    "Unit": item["unit"],
                    "Location": item["location"] or "Not specified",
                    "Low-Stock Threshold": item["threshold"],
                }
                for item in filtered
            ],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No inventory items yet. Add your first item above.")


# -----------------------------
# Record donation page
# -----------------------------
elif page == "Record Donation":
    st.title("Record a Donation")

    items = get_inventory()

    if not items:
        st.warning("Add an inventory item before recording a donation.")
    else:
        item_options = {
            f'{item["name"]} (ID: {item["id"]})': item["id"]
            for item in items
        }

        with st.form("donation_form"):
            selected_item = st.selectbox(
                "Select Item",
                list(item_options.keys())
            )

            donor = st.text_input("Donor or Organization")

            quantity = st.number_input(
                "Quantity Received",
                min_value=1,
                step=1,
            )

            has_expiration = st.checkbox(
                "This donation has an expiration date"
            )

            expiration = None

            if has_expiration:
                expiration = st.date_input(
                    "Expiration Date",
                    min_value=date.today(),
                    value=date.today() + timedelta(days=30),
                )

            submitted = st.form_submit_button("Record Donation")

            if submitted:
                if not donor.strip():
                    st.error("Please enter the donor name.")
                else:
                    record_donation(
                        item_options[selected_item],
                        donor,
                        int(quantity),
                        expiration,
                    )

                    st.success(
                        f"Recorded {quantity} units from {donor}."
                    )
                    st.rerun()


# -----------------------------
# Donation history page
# -----------------------------
elif page == "Donation History":
    st.title("Donation History")

    donations = get_donations()

    if donations:
        st.dataframe(
            donations,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Donation History CSV",
            data=__import__("pandas").DataFrame(
                donations
            ).to_csv(index=False),
            file_name="bsao_donation_history.csv",
            mime="text/csv",
        )
    else:
        st.info("No donation records found.")

def update_inventory_item(
    item_id,
    name,
    category,
    quantity,
    unit,
    location,
    threshold,
):
    if quantity < 0 or threshold < 0:
        raise ValueError("Quantities cannot be negative.")

    with get_session() as session:
        item = session.get(Inventory, item_id)

        if item is None:
            raise ValueError("Inventory item not found.")

        item.name = name.strip()
        item.category = category
        item.quantity = quantity
        item.unit = unit
        item.storage_location = location.strip() or None
        item.low_stock_threshold = threshold

        session.commit()


def deactivate_inventory_item(item_id):
    with get_session() as session:
        item = session.get(Inventory, item_id)

        if item is None:
            raise ValueError("Inventory item not found.")

        item.is_active = False
        session.commit()


def record_distribution(item_id, quantity, notes=""):
    if quantity <= 0:
        raise ValueError(
            "Distribution quantity must be positive."
        )

    with get_session() as session:
        item = session.get(Inventory, item_id)

        if item is None or not item.is_active:
            raise ValueError("Active inventory item not found.")

        if item.quantity < quantity:
            raise ValueError(
                f"Only {item.quantity} {item.unit} available."
            )

        item.quantity -= quantity

        distribution = Distribution(
            item_id=item_id,
            quantity_distributed=quantity,
            distribution_date=date.today(),
            notes=notes.strip() or None,
        )

        session.add(distribution)
        session.commit()

elif page == "Distribute Supplies":
    st.title("Distribute Pantry Supplies")

    items = [
        item for item in get_inventory()
        if item["quantity"] > 0
    ]

    if not items:
        st.info("No available stock to distribute.")
    else:
        options = {
            f'{item["name"]} '
            f'({item["quantity"]} {item["unit"]} available)':
            item["id"]
            for item in items
        }

        with st.form("distribution_form"):
            selected = st.selectbox(
                "Item", list(options.keys())
            )

            selected_item = next(
                item for item in items
                if item["id"] == options[selected]
            )

            quantity = st.number_input(
                "Quantity Distributed",
                min_value=1,
                max_value=selected_item["quantity"],
                value=1,
                step=1,
            )

            notes = st.text_input(
                "Notes (optional)"
            )

            submitted = st.form_submit_button(
                "Record Distribution"
            )

            if submitted:
                record_distribution(
                    options[selected],
                    int(quantity),
                    notes,
                )

                st.success("Distribution recorded!")
                st.rerun()


elif page == "Distribution History":
    st.title("Distribution History")

    with get_session() as session:
        distributions = session.scalars(
            select(Distribution).order_by(
                Distribution.distribution_date.desc(),
                Distribution.id.desc()
            )
        ).all()

        records = []

        for distribution in distributions:
            item = session.get(
                Inventory, distribution.item_id
            )

            records.append({
                "Date": distribution.distribution_date,
                "Item": item.name if item else "Unknown",
                "Quantity": distribution.quantity_distributed,
                "Unit": item.unit if item else "",
                "Notes": distribution.notes or "",
            })

    if records:
        st.dataframe(
            records,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No distributions recorded yet.")
