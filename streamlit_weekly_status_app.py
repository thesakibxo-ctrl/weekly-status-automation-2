import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(layout="wide")
st.title("Weekly Status Preview with AG Grid (Safe Copy)")

uploaded_csv = st.file_uploader("Upload your timesheet CSV", type=["csv"])

if uploaded_csv:
    df = pd.read_csv(uploaded_csv, encoding="utf-8-sig", keep_default_na=False)
    df.columns = df.columns.str.strip().str.lower()

    # Validate columns
    if not all(col in df.columns for col in ["description", "activity"]):
        st.error("CSV missing required columns: description, activity")
        st.stop()

    # Clean CSV
    df = df[~df["description"].isin(["", "Total", "Weekly Total"])]
    df = df.dropna(subset=["description", "activity"])

    # Convert hours to decimal
    if "hours" in df.columns and "minutes" in df.columns:
        df["spent_hours"] = df["hours"].astype(float) + df["minutes"].astype(float)/60
    elif "spent hours" in df.columns:
        df["spent_hours"] = df["spent hours"].astype(float)
    else:
        st.error("CSV must have 'Hours & Minutes' or 'Spent Hours'")
        st.stop()

    # Merge tasks
    rows = []

    comm = df[df["activity"].str.lower() == "communication"]
    if not comm.empty:
        rows.append({"Task Title": "Communication", "Spent Hours": comm["spent_hours"].sum()})

    others = df[df["activity"].str.lower() != "communication"]
    grouped = others.groupby("description", as_index=False).agg({"spent_hours": "sum"})
    for _, row in grouped.iterrows():
        rows.append({"Task Title": row["description"], "Spent Hours": row["spent_hours"]})

    processed_tasks = pd.DataFrame(rows)

    # Format hours
    def format_hours(x):
        total_min = round(x * 60)
        return f"{total_min // 60}h {total_min % 60}m"

    processed_tasks["Spent Hours"] = processed_tasks["Spent Hours"].apply(format_hours)

    # Weekly total
    total_min = processed_tasks["Spent Hours"].apply(lambda x: int(x.split("h")[0])*60 + int(x.split(" ")[1].replace("m",""))).sum()
    processed_tasks = pd.concat([processed_tasks, pd.DataFrame([{"Task Title":"Weekly Total", "Spent Hours": f"{total_min//60}h {total_min%60}m"}])], ignore_index=True)

    # -------------------------------
    # AG Grid (Safe)
    # -------------------------------
    gb = GridOptionsBuilder.from_dataframe(processed_tasks)
    gb.configure_default_column(resizable=True, editable=False, filterable=True)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(domLayout='autoHeight', enableRangeSelection=True)
    gridOptions = gb.build()

    st.subheader("Weekly Status Preview")
    AgGrid(
        processed_tasks,
        gridOptions=gridOptions,
        enable_enterprise_modules=False,
        fit_columns_on_grid_load=True
    )
