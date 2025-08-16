import streamlit as st
import pandas as pd

st.set_page_config(layout="centered")
st.title("Weekly Status Generate")

uploaded_csv = st.file_uploader("Upload your timesheet CSV", type=["csv"])

if uploaded_csv:
    df = pd.read_csv(uploaded_csv, encoding="utf-8-sig", keep_default_na=False)
    df.columns = df.columns.str.strip().str.lower()
    required_cols = ["description", "activity", "date"]
    if any(col not in df.columns for col in required_cols):
        st.error("CSV missing required columns.")
        st.stop()

    df = df[~df["description"].isin(["", "Total", "Weekly Total"])]
    df = df.dropna(subset=["description", "activity", "date"])

    if "hours" in df.columns and "minutes" in df.columns:
        df["spent_hours"] = df["hours"].astype(float) + df["minutes"].astype(float)/60
    elif "spent hours" in df.columns:
        df["spent_hours"] = df["spent hours"].astype(float)
    else:
        st.error("CSV must have Hours/Minutes or Spent Hours")
        st.stop()

    communication_tasks = df[df["activity"].str.lower() == "communication"]
    other_tasks = df[df["activity"].str.lower() != "communication"]

    rows = []
    if not communication_tasks.empty:
        rows.append({"Task Title": "Communication", "Spent Hours": communication_tasks["spent_hours"].sum()})
    if not other_tasks.empty:
        grouped = other_tasks.groupby("description", as_index=False).agg({"spent_hours": "sum"})
        for _, row in grouped.iterrows():
            rows.append({"Task Title": row["description"], "Spent Hours": row["spent_hours"]})

    processed_tasks = pd.DataFrame(rows)

    def format_hours(decimal_hours):
        total_minutes = round(decimal_hours * 60)
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h}h {m}m"

    processed_tasks["Spent Hours"] = processed_tasks["Spent Hours"].apply(format_hours)

    total_minutes = processed_tasks["Spent Hours"].apply(
        lambda x: int(x.split("h")[0])*60 + int(x.split(" ")[1].replace("m",""))
    ).sum()
    total_h = total_minutes // 60
    total_m = total_minutes % 60
    weekly_total = pd.DataFrame([{"Task Title": "Weekly Total", "Spent Hours": f"{total_h}h {total_m}m"}])
    final_table = pd.concat([processed_tasks, weekly_total], ignore_index=True)

    st.subheader("Weekly Status Preview")

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    start_date = df.iloc[0]['date']
    end_date = df.iloc[-1]['date']
    period_covered = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
    st.markdown(
        f"<p style='color:white; font-size:16px; font-weight:bold;'>Period Covered: {period_covered}</p>",
        unsafe_allow_html=True
    )

    def highlight_weekly_total(row):
        if row["Task Title"] == "Weekly Total":
            return ['background-color: rgba(255,255,255,0.1)']*len(row)
        return ['']*len(row)

    # Hide index (works in Pandas ≥ 2.0)
    st.dataframe(
        final_table[["Task Title", "Spent Hours"]].style.apply(highlight_weekly_total, axis=1).hide_index(),
        use_container_width=True
    )

    st.download_button("📥 Download CSV",
                       final_table.to_csv(index=False).encode("utf-8"),
                       "weekly_status.csv",
                       "text/csv")
