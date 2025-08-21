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
# Step 1: Upload CSV + Template
# -------------------------------
uploaded_csv = st.file_uploader("Upload your timesheet CSV", type=["csv"])
uploaded_template = st.file_uploader("Upload Weekly Status Template", type=["xlsx"])

if uploaded_csv and uploaded_template:
    try:
        df = pd.read_csv(uploaded_csv, encoding="utf-8-sig", keep_default_na=False)
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        st.stop()

    # Normalize columns
    df.columns = df.columns.str.strip().str.lower()

    # Required columns
    required_cols = ["description", "activity"]
    if not all(col in df.columns for col in required_cols):
        st.error(f"CSV must contain: {required_cols}")
        st.stop()

    # Remove irrelevant rows
    df = df[~df["description"].isin(["", "Total", "Weekly Total"])]
    df = df.dropna(subset=["description", "activity"])

    # Handle Spent Hours
    if "hours" in df.columns and "minutes" in df.columns:
        df["spent_hours"] = df["hours"].astype(float) + df["minutes"].astype(float) / 60
    elif "spent hours" in df.columns:
        df["spent_hours"] = df["spent hours"].astype(float)
    else:
        st.error("CSV must have either 'Hours' and 'Minutes' or 'Spent Hours'.")
        st.stop()

    # -------------------------------
    # Step 2: Merge Tasks
    # -------------------------------
    communication_tasks = df[df["activity"].str.lower() == "communication"]
    other_tasks = df[df["activity"].str.lower() != "communication"]

    rows = []

    # Communication
    if not communication_tasks.empty:
        comm_hours = communication_tasks["spent_hours"].sum()
        rows.append({"Task Title": "Communication", "Spent Hours": comm_hours})

    # Other tasks
    if not other_tasks.empty:
        grouped = other_tasks.groupby("description", as_index=False).agg({"spent_hours": "sum"})
        for _, row in grouped.iterrows():
            rows.append({"Task Title": row["description"], "Spent Hours": row["spent_hours"]})

    processed_tasks = pd.DataFrame(rows)

    # -------------------------------
    # Step 3: Format Hours as "0h 0m"
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

    start_row = 11
    for i, row in processed_tasks.iterrows():
        current_row = start_row + i
        ws[f"C{current_row}"] = row["Task Title"]   # merged C:E → write only to C
        ws[f"G{current_row}"] = row["Spent Hours"]  # spent hours

    # -------------------------------
    # Step 5: Period Covered (from CSV Date column)
    # -------------------------------
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        if not df.empty:
            start_date = df["date"].min()
            end_date = df["date"].max()
            period_text = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
            ws["G5"] = period_text
            ws["H5"] = ""  # merged with G5
            ws["E12"] = period_text

    # -------------------------------
    # Step 6: Save to Bytes & Download
    # -------------------------------
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    st.download_button(
        "📥 Download Weekly Status Report",
        output,
        file_name="Weekly_Status_Filled.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Preview in app
    st.subheader("Weekly Status Preview")
    st.dataframe(processed_tasks, use_container_width=True)
