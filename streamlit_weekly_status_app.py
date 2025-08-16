import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

st.set_page_config(layout="wide")
st.title("Weekly Status Preview with Click-to-Copy")

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

    df.columns = df.columns.str.strip().str.lower()
    required_cols = ["description", "activity"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"CSV is missing required columns: {missing_cols}")
        st.stop()

    # Clean CSV
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
    # Step 2: Merge Tasks
    # -------------------------------
    communication_tasks = df[df["activity"].str.lower() == "communication"]
    other_tasks = df[df["activity"].str.lower() != "communication"]

    rows = []

    if not communication_tasks.empty:
        comm_hours = communication_tasks["spent_hours"].sum()
        rows.append({"Task Title": "Communication", "Spent Hours": comm_hours})

    if not other_tasks.empty:
        grouped = other_tasks.groupby("description", as_index=False).agg({"spent_hours": "sum"})
        for _, row in grouped.iterrows():
            rows.append({"Task Title": row["description"], "Spent Hours": row["spent_hours"]})

    processed_tasks = pd.DataFrame(rows)

    # Format hours as "0h 0m"
    def format_hours(decimal_hours):
        total_minutes = round(decimal_hours * 60)
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h}h {m}m"

    processed_tasks["Spent Hours"] = processed_tasks["Spent Hours"].apply(format_hours)

    # Weekly total
    total_minutes = processed_tasks["Spent Hours"].apply(
        lambda x: int(x.split("h")[0])*60 + int(x.split(" ")[1].replace("m",""))
    ).sum()
    total_h = total_minutes // 60
    total_m = total_minutes % 60
    weekly_total = pd.DataFrame([{"Task Title": "Weekly Total", "Spent Hours": f"{total_h}h {total_m}m"}])

    final_table = pd.concat([processed_tasks, weekly_total], ignore_index=True)

    # -------------------------------
    # Step 3: AG Grid with Click-to-Copy
    # -------------------------------
    gb = GridOptionsBuilder.from_dataframe(final_table)
    gb.configure_default_column(resizable=True, editable=False)
    gb.configure_grid_options(domLayout='autoHeight')  # full width

    # JS cell renderer for click-to-copy
    copy_js = JsCode("""
    function(params) {
        const span = document.createElement('span');
        span.style.position = 'relative';
        span.innerText = params.value;

        const btn = document.createElement('span');
        btn.innerText = ' 📋';
        btn.style.cursor = 'pointer';
        btn.title = 'Click to copy';
        btn.style.color = '#555';
        btn.onmouseover = () => btn.style.color = 'black';
        btn.onmouseout = () => btn.style.color = '#555';
        btn.onclick = () => navigator.clipboard.writeText(params.value);

        span.appendChild(btn);
        return span;
    }
    """)

    gb.configure_columns(["Task Title", "Spent Hours"], cellRenderer=copy_js)
    gridOptions = gb.build()

    st.subheader("Weekly Status Preview")
    AgGrid(
        final_table,
        gridOptions=gridOptions,
        enable_enterprise_modules=False,
        fit_columns_on_grid_load=True
    )
