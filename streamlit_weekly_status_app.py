import streamlit as st
import pandas as pd

st.title("Weekly Status Preview with Weekly Total")

# -------------------------------
# Step 1: Upload CSV
# -------------------------------
uploaded_csv = st.file_uploader("Upload your timesheet CSV", type=["csv"])

if uploaded_csv:
    df = pd.read_csv(uploaded_csv, encoding="utf-8-sig", keep_default_na=False)
    st.write(f"Loaded rows: {len(df)}")

    # -------------------------------
    # Step 2: Clean CSV
    # -------------------------------
    df = df[~df["Description"].isin(["", "Total", "Weekly Total"])]
    df = df.dropna(subset=["Description", "Category"])  # optional

    # Convert Hours + Minutes to decimal if they exist
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

    # Merge Communication tasks
    rows = []
    if not communication_tasks.empty:
        comm_hours = communication_tasks["Spent Hours"].sum()
        comm_remarks = " | ".join(communication_tasks["Description"].tolist())
        rows.append({"Task Title": "Communication", "Spent Hours": comm_hours, "Remarks": comm_remarks})

    # Merge duplicate descriptions for other tasks
    if not other_tasks.empty:
        grouped = other_tasks.groupby("Description", as_index=False).agg({"Spent Hours": "sum"})
        for _, row in grouped.iterrows():
            task_title = row["Description"]
            spent_hours = row["Spent Hours"]
            remarks = row["Description"]  # Remarks same as description
            rows.append({"Task Title": task_title, "Spent Hours": spent_hours, "Remarks": remarks})

    processed_tasks = pd.DataFrame(rows)

    # -------------------------------
    # Step 4: Format Spent Hours as "0h 0m"
    # -------------------------------
    def format_hours(decimal_hours):
        total_minutes = int(decimal_hours * 60)
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h}h {m}m"

    processed_tasks["Spent Hours"] = processed_tasks["Spent Hours"].apply(format_hours)

    # -------------------------------
    # Step 5: Add Weekly Total row
    # -------------------------------
    total_hours = processed_tasks["Spent Hours"].apply(lambda x: int(x.split("h")[0])*60 + int(x.split(" ")[1].replace("m",""))).sum()
    total_h = total_hours // 60
    total_m = total_hours % 60
    weekly_total = pd.DataFrame([{
        "Task Title": "Weekly Total",
        "Spent Hours": f"{total_h}h {total_m}m",
        "Remarks": ""
    }])

    final_table = pd.concat([processed_tasks, weekly_total], ignore_index=True)

    # -------------------------------
    # Step 6: Show Table
    # -------------------------------
    st.subheader("Weekly Status Preview")
    st.dataframe(final_table[["Task Title", "Spent Hours", "Remarks"]])
