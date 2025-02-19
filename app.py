import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import os

# --- Load Custom CSS from assets/style.css ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

css_file = os.path.join("assets", "style.css")
local_css(css_file)

# --- App Title ---
st.title("💰 Personal Finance Manager")

# --- Sidebar Navigation ---
menu = st.sidebar.radio(
    "Navigation", 
    ["Dashboard", "Add Transaction", "Analytics", "Manage Transactions"]
)

# --- Initialize Session State for Transactions ---
if 'transactions' not in st.session_state:
    st.session_state['transactions'] = pd.DataFrame(
        columns=["Date", "Category", "Type", "Amount", "Description"]
    )

# For editing transactions: store the index of the transaction being edited
if 'edit_idx' not in st.session_state:
    st.session_state.edit_idx = None

# --- Functions ---
def add_transaction(date, category, trans_type, amount, description):
    """Add a new transaction to the session state."""
    new_transaction = pd.DataFrame({
        "Date": [date],
        "Category": [category],
        "Type": [trans_type],
        "Amount": [amount],
        "Description": [description]
    })
    st.session_state.transactions = pd.concat(
        [st.session_state.transactions, new_transaction], ignore_index=True
    )

def delete_transaction(idx):
    """Delete a transaction by index."""
    st.session_state.transactions.drop(idx, inplace=True)
    st.session_state.transactions.reset_index(drop=True, inplace=True)
    st.success("Transaction deleted successfully!")

def update_transaction(idx, date, category, trans_type, amount, description):
    """Update an existing transaction."""
    st.session_state.transactions.at[idx, "Date"] = date
    st.session_state.transactions.at[idx, "Category"] = category
    st.session_state.transactions.at[idx, "Type"] = trans_type
    st.session_state.transactions.at[idx, "Amount"] = amount
    st.session_state.transactions.at[idx, "Description"] = description
    st.success("Transaction updated successfully!")
    st.session_state.edit_idx = None

# --- Navigation: Add Transaction ---
if menu == "Add Transaction":
    st.header("Add a New Transaction")
    with st.form("transaction_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", value=datetime.date.today())
            trans_type = st.selectbox("Type", options=["Income", "Expense"])
        with col2:
            category = st.text_input("Category", value="General")
            amount = st.number_input("Amount ($)", min_value=0.0, format="%.2f")
        description = st.text_area("Description")
        submitted = st.form_submit_button("Add Transaction")
        if submitted:
            add_transaction(date, category, trans_type, amount, description)
            st.success("Transaction added successfully!")

# --- Navigation: Dashboard ---
elif menu == "Dashboard":
    st.header("Dashboard")
    
    # --- Filter Options ---
    with st.expander("Filter Transactions", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", value=datetime.date.today())
        trans_types = st.multiselect("Transaction Type", options=["Income", "Expense"], default=["Income", "Expense"])
        # Get dynamic category list if available
        categories = st.session_state.transactions["Category"].unique().tolist() if not st.session_state.transactions.empty else []
        selected_categories = st.multiselect("Category", options=categories, default=categories)
        filter_button = st.button("Apply Filters")
    
    df = st.session_state.transactions.copy()
    if not df.empty:
        # Ensure Date is in datetime format
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Apply filters if requested
        if filter_button:
            df = df[(df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))]
            df = df[df['Type'].isin(trans_types)]
            if selected_categories:
                df = df[df['Category'].isin(selected_categories)]
        
        # --- Display Key Metrics ---
        total_income = df[df["Type"] == "Income"]["Amount"].sum()
        total_expense = df[df["Type"] == "Expense"]["Amount"].sum()
        balance = total_income - total_expense

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"${total_income:,.2f}")
        col2.metric("Total Expense", f"${total_expense:,.2f}")
        col3.metric("Balance", f"${balance:,.2f}")

        st.subheader("Recent Transactions")
        st.dataframe(df.sort_values(by="Date", ascending=False).reset_index(drop=True))

        # --- Download CSV Option ---
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Transactions as CSV",
            data=csv,
            file_name='transactions.csv',
            mime='text/csv'
        )
    else:
        st.info("No transactions recorded yet. Please add some transactions.")

# --- Navigation: Analytics ---
elif menu == "Analytics":
    st.header("Analytics")
    df = st.session_state.transactions.copy()
    if df.empty:
        st.info("No transactions recorded yet. Please add some transactions.")
    else:
        df['Date'] = pd.to_datetime(df['Date'])
        
        # --- Monthly Summary for Income vs Expense ---
        df['Month'] = df['Date'].dt.to_period('M').astype(str)
        monthly = df.groupby(['Month', 'Type'])['Amount'].sum().reset_index()
        
        st.subheader("Monthly Income vs Expense")
        fig_bar = px.bar(
            monthly, 
            x="Month", 
            y="Amount", 
            color="Type", 
            barmode="group",
            title="Monthly Income vs Expense",
            labels={"Amount": "Total Amount ($)", "Month": "Month"}
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # --- Expense Distribution Pie Chart ---
        expense_df = df[df["Type"] == "Expense"]
        if not expense_df.empty:
            pie_data = expense_df.groupby("Category")["Amount"].sum().reset_index()
            st.subheader("Expense Distribution by Category")
            fig_pie = px.pie(
                pie_data, 
                names='Category', 
                values='Amount', 
                title="Expense Distribution"
            )
            st.plotly_chart(fig_pie, use_container_width=True)

# --- Navigation: Manage Transactions ---
elif menu == "Manage Transactions":
    st.header("Manage Transactions")
    df = st.session_state.transactions.copy()
    if df.empty:
        st.info("No transactions recorded yet.")
    else:
        df['Date'] = pd.to_datetime(df['Date'])
        st.dataframe(df.sort_values(by="Date", ascending=False).reset_index(drop=True))
        st.write("Manage your transactions:")
        
        # Iterate over transactions and show Delete and Edit buttons for each
        for idx, row in df.iterrows():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{row['Date'].date()} - {row['Type']}**: ${row['Amount']:,.2f} in *{row['Category']}*")
                st.write(f"_{row['Description']}_")
            with col2:
                if st.button("Edit", key=f"edit_{idx}"):
                    st.session_state.edit_idx = idx
                    
            with col3:
                if st.button("Delete", key=f"delete_{idx}"):
                    delete_transaction(idx)
                    
    # --- Edit Transaction Form ---
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        st.subheader("Edit Transaction")
        # Pre-fill the form with current values
        current = st.session_state.transactions.loc[idx]
        with st.form("edit_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_date = st.date_input("Date", value=pd.to_datetime(current["Date"]).date())
                new_trans_type = st.selectbox("Type", options=["Income", "Expense"], index=0 if current["Type"]=="Income" else 1)
            with col2:
                new_category = st.text_input("Category", value=current["Category"])
                new_amount = st.number_input("Amount ($)", min_value=0.0, value=float(current["Amount"]), format="%.2f")
            new_description = st.text_area("Description", value=current["Description"])
            updated = st.form_submit_button("Update Transaction")
            if updated:
                update_transaction(idx, new_date, new_category, new_trans_type, new_amount, new_description)
