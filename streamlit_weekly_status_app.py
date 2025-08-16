import streamlit as st
import pandas as pd
import requests
import os
import time

st.title("Weekly Status Preview with Reliable AI Summaries")

# -------------------------------
# Step 0: Load OpenRouter API Key safely
# -------------------------------
api_key = st.secrets.get("openrouter", {}).get("api_key") or os.getenv("OPENROUTER_API_KEY")
if not api_key:
    st.error(
        "OpenRouter API key not found! "
        "Set it in .streamlit/secrets.toml or as environment variable OPENROUTER_API_KEY"
    )
    st.stop()

# -------------------------------
# Helper: Summarize Task with retries & fallback
# -------------------------------
def summarize_task(text, retries=3, delay=2):
    """Use OpenRouter GPT-4o-mini to summarize task description with retries."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": f"Summarize this task in one sentence: {text}"}]
    }

    for attempt in range(retries):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                return "No summary available"

# -------------------------------
# Step 1: Upload CSV
# -------------------------------
uploaded_csv = st.file_uploader("Upload your timesheet CSV", type=["csv"])

if uploaded_csv:
    try:
        df = pd.read_csv(uploaded_csv, encoding="utf-8-sig", keep_default_na=False)
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        st.stop()

    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()
    st.write("CSV Columns Detected:", df.columns.tolist())

    # -------------------------------
    # Step 2: Check required columns
    # -------------------------------
    required_cols = ["description", "activity"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"CSV is missing required columns: {missing_cols}")
        st.stop()

    # Remove irrelevant rows
    df = df[~df["description"].isin(["", "Total", "Weekly Total"])]
    df = df.dropna(subset=["description", "activity"])

    # -------------------------------
    # Step 3: Convert Hours + Minutes to decimal
    # -------------------------------
    if "hours" in df.columns and "minutes" in df.columns:
        df["spent_hours"] = df["hours"].astype(float) + df["minutes"].astype(float)/60
    elif "spent hours" in df.columns:
        df["spent_hours"] = df["spent hours"].astype(float)
    else:
        st.error("CSV must have either 'Hours' and 'Minutes' or 'Spent Hours' column.")
        st.stop()

    # -------------------------------
    # Step 4: Separate Communication & Other Tasks
    # -------------------------------
    communication_tasks = df[df["activity"].str.lower() == "communication"]
    other_tasks = df[df["activity"].str.lower() != "communication"]

    rows = []

    # Communication merged
    if not communication_tasks.empty:
        comm_hours = communication_tasks["spent_hours"].sum()
        comm_remarks_text = " | ".join(communication_tasks["description"].tolist())
        with st.spinner("Generating AI remark for Communication..."):
            ai_summary = summarize_task(comm_remarks_text)
        rows.append({
            "Task Title": "Communication",
            "Spent Hours": comm_hours,
            "Remarks": ai_summary
        })

    # Merge duplicate descriptions for other tasks
    if not other_tasks.empty:
        grouped = other_tasks.groupby("description", as_index=False).agg({"spent_hours": "sum"})
        for _, row in grouped.iterrows():
            task_title = row["description"]
            spent_hours = row["spent_hours"]
            with st.spinner(f"Generating AI remark for task: {task_title}"):
                ai_summary = summarize_task(task_title)
            rows.append({
                "Task Title": task_title,
                "Spent Hours": spent_hours,
                "Remarks": ai_summary
            })

    if not rows:
        st.warning("No valid tasks found in CSV after cleaning.")
        st.stop()

    processed_tasks = pd.DataFrame(rows)

    # -------------------------------
    # Step 5: Format Spent Hours as "0h 0m" with proper rounding
    # -------------------------------
    def format_hours(decimal_hours):
        total_minutes = round(decimal_hours * 60)
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h}h {m}m"

    processed_tasks["Spent Hours"] = processed_tasks["Spent Hours"].apply(format_hours)

    # -------------------------------
    # Step 6: Add Weekly Total Row
    # -------------------------------
    total_minutes = processed_tasks["Spent Hours"].apply(
        lambda x: int(x.split("h")[0])*60 + int(x.split(" ")[1].replace("m",""))
    ).sum()
    total_h = total_minutes // 60
    total_m = total_minutes % 60
    weekly_total = pd.DataFrame([{
        "Task Title": "Weekly Total",
        "Spent Hours": f"{total_h}h {total_m}m",
        "Remarks": ""
    }])

    final_table = pd.concat([processed_tasks, weekly_total], ignore_index=True)

    # -------------------------------
    # Step 7: Show Table Full Width
    # -------------------------------
    st.subheader("Weekly Status Preview")
    st.dataframe(final_table[["Task Title", "Spent Hours", "Remarks"]], use_container_width=True)
