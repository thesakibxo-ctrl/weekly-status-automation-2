import streamlit as st
import pandas as pd

st.title("Weekly Status Preview (No Excel Output)")

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
    if not communication_tasks.empty:
        comm_row = pd.DataFrame({
            "Task Title": ["Communication"],
            "Spent Hours": [communication_tasks["Spent Hours"].sum()],
            "Remarks": [" | ".join(communication_tasks["Description"].tolist())]
        })
    else:
        comm_row = pd.DataFrame(columns=["Task Title", "Spent Hours", "Remarks"])

    # Merge duplicate descriptions for other tasks
    if not other_tasks.empty:
        other_rows = (
            other_tasks.groupby("Description", as_index=False)
            .agg({
                "Spent Hours": "sum",
                "Description": lambda x: " | ".join(x)
            })
            .rename(columns={"Description": "Remarks"})
        )
        other_rows["Task Title"] = other_rows["Remarks"]  # Task Title = description
    else:
        other_rows = pd.DataFrame(columns=["Task Title", "Spent Hours", "Remarks"])

    # Combine all tasks
    processed_tasks = pd.concat([comm_row, other_rows], ignore_index=True)

    # -------------------------------
    # Step 4: Format Hours as "0h 0m"
    # -------------------------------
    def format_hours(decimal_hours):
        total_minutes = int(decimal_hours * 60)
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h}h {m}m"

    processed_tasks["Spent Hours"] = processed_tasks["Spent Hours"].apply(format_hours)

    # -------------------------------
    # Step 5: Show Table in Streamlit
    # -------------------------------
    st.subheader("Weekly Status Preview")
    st.dataframe(processed_tasks[["Task Title", "Spent Hours", "Remarks"]])
