import streamlit as st
import pandas as pd
import openpyxl

st.title("Weekly Status Generator (Hours & Minutes Columns)")

# -------------------------------
# Step 1: Upload CSV & Template
# -------------------------------
uploaded_csv = st.file_uploader("Upload your timesheet CSV", type=["csv"])
uploaded_template = st.file_uploader("Upload Weekly Status Template", type=["xlsx"])

if uploaded_csv and uploaded_template:
    df = pd.read_csv(uploaded_csv, encoding="utf-8-sig", keep_default_na=False)
    st.write(f"Loaded rows: {len(df)}")

    # -------------------------------
    # Step 2: Convert Hours + Minutes to Decimal Hours
    # -------------------------------
    if "Hours" in df.columns and "Minutes" in df.columns:
        df["Spent Hours"] = df["Hours"].astype(float) + df["Minutes"].astype(float)/60
    elif "Spent Hours" in df.columns:
        df["Spent Hours"] = df["Spent Hours"].astype(float)
    else:
        st.error("CSV must have either 'Spent Hours' or both 'Hours' and 'Minutes' columns.")
        st.stop()

    # -------------------------------
    # Step 3: Separate Communication and Other Tasks
    # -------------------------------
    communication_tasks = df[df["Category"].str.lower() == "communication"]
    other_tasks = df[df["Category"].str.lower() != "communication"]

    # Merge Communication tasks into one row
    if not communication_tasks.empty:
        total_hours_comm = communication_tasks["Spent Hours"].sum()
        comm_row = pd.DataFrame({
            "Task Title": ["Communication"],
            "Spent Hours": [total_hours_comm],
            "Remarks": [" | ".join(communication_tasks["Description"].tolist())]
        })
    else:
        comm_row = pd.DataFrame(columns=["Task Title", "Spent Hours", "Remarks"])

    # Merge duplicate descriptions for other tasks
    if not other_tasks.empty:
        other_rows = other_tasks.groupby("Description", as_index=False).agg({
            "Spent Hours": "sum",
            "Description": lambda x: " | ".join(x)
        }).rename(columns={"Description": "Task Title", "Description": "Remarks"})
    else:
        other_rows = pd.DataFrame(columns=["Task Title", "Spent Hours", "Remarks"])

    # Combine Communication and other tasks
    processed_tasks = pd.concat([comm_row, other_rows], ignore_index=True)

    # -------------------------------
    # Step 4: Format Spent Hours as "0h 0m"
    # -------------------------------
    def format_hours(decimal_hours):
        total_minutes = int(decimal_hours * 60)
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h}h {m}m"

    processed_tasks["Spent Hours"] = processed_tasks["Spent Hours"].apply(format_hours)

    st.subheader("Processed Tasks Preview")
    st.dataframe(processed_tasks[["Task Title", "Spent Hours", "Remarks"]])

    # -------------------------------
    # Step 5: Write Back into Template
    # -------------------------------
    wb = openpyxl.load_workbook(uploaded_template)
    ws = wb.worksheets[1]  # fixed 2nd sheet
    start_row = 5

    for i, row in processed_tasks.iterrows():
        ws.cell(row=start_row+i, column=1, value=row["Task Title"])
        ws.cell(row=start_row+i, column=2, value=row["Spent Hours"])
        ws.cell(row=start_row+i, column=3, value=row["Remarks"])

    output_file = "Weekly_Status_Filled.xlsx"
    wb.save(output_file)

    # -------------------------------
    # Step 6: Download Button
    # -------------------------------
    with open(output_file, "rb") as f:
        st.download_button(
            label="Download Weekly Status Report",
            data=f,
            file_name=output_file
        )

    st.success("Weekly Status Report is ready!")
