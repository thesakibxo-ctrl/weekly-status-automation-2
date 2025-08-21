import streamlit as st
import pandas as pd
import openpyxl
from io import BytesIO

# -------------------------------
# Streamlit Page Config
# -------------------------------
st.set_page_config(layout="centered")
st.title("Weekly Status Generate")

# -------------------------------
# Step 1: Upload CSV
# -------------------------------
uploaded_csv = st.file_uploader("Upload your timesheet CSV", type=["csv"])
uploaded_template = "Enosis-Schedulewise Weekly Status Template.xlsx"  # local template file

if uploaded_csv:
    try:
        df = pd.read_csv(uploaded_csv, encoding="utf-8-sig", keep_default_na=False)
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        st.stop()

    # Normalize columns
    df.columns = df.columns.str.strip().str.lower()

    # Check required columns
    required_cols = ["description", "activity"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"CSV is missing required columns: {missing_cols}")
        st.stop()

    # Remove irrelevant rows
    df = df[~df["description"].isin(["", "Total", "Weekly Total"])]
    df = df.dropna(subset=["description", "activity"])

    # Convert hours+minutes to decimal
    if "hours" in df.columns and "minutes" in df.columns:
        df["spent_hours"] = df["hours"].astype(float) + df["minutes"].astype(float)/60
    elif "spent hours" in df.columns:
        df["spent_hours"] = df["spent hours"].astype(float)
    else:
        st.error("CSV must have either 'Hours' and 'Minutes' or 'Spent Hours'.")
        st.stop()

    # -------------------------------
    # Step 2: Merge tasks
    # -------------------------------
    communication_tasks = df[df["activity"].str.lower() == "communication"]
    other_tasks = df[df["activity"].str.lower() != "communication"]

    rows = []

    # Merge Communication
    if not communication_tasks.empty:
        comm_hours = communication_tasks["spent_hours"].sum()
        rows.append({
            "Task Title": "Communication",
            "Spent Hours": comm_hours
        })

    # Merge duplicate other tasks
    if not other_tasks.empty:
        grouped = other_tasks.groupby("description", as_index=False).agg({"spent_hours": "sum"})
        for _, row in grouped.iterrows():
            rows.append({
                "Task Title": row["description"],
                "Spent Hours": row["spent_hours"]
            })

    processed_tasks = pd.DataFrame(rows)

    # -------------------------------
    # Step 3: Format Spent Hours as "0h 0m"
    # -------------------------------
    def format_hours(decimal_hours):
        total_minutes = round(decimal_hours * 60)
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h}h {m}m"

    processed_tasks["Spent Hours"] = processed_tasks["Spent Hours"].apply(format_hours)

    # -------------------------------
    # Step 4: Insert into Template
    # -------------------------------
    wb = openpyxl.load_workbook(uploaded_template)
    ws = wb["Weekly Task Status V2.0"]

    start_row = 11  # First row for tasks

    for i, row in processed_tasks.iterrows():
        ws[f"C{start_row+i}"] = row["Task Title"]   # Task Title
        ws[f"G{start_row+i}"] = row["Spent Hours"]  # Spent Hours
        # Status (D/E) and Remarks stay untouched

    # Save to memory
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    # -------------------------------
    # Step 5: Download Filled XLSX
    # -------------------------------
    st.download_button(
        label="📥 Download Weekly Status (XLSX)",
        data=output,
        file_name="Weekly_Status_Filled.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
