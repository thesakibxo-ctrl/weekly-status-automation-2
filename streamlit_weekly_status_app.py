"""
Streamlit app: Weekly Status Auto-Filler
- Upload your CSV (timesheet export)
- Upload your weekly status Excel template (optional)
- Configure CSV columns if necessary (Date, Task, Hours)
- App groups tasks by original task name, sums hours, counts days
- Generates short "Remark" for each grouped task (AI via Hugging Face optional)
- Writes results into a copy of the uploaded Excel template in a new sheet named 'AutoFilled'
- Download the completed Excel

Usage:
- Install dependencies: pip install -r requirements.txt
- Run: streamlit run streamlit_weekly_status_app.py

Optional: if you want AI-generated remarks using Hugging Face Inference API, set your HF_API_KEY in Streamlit secrets or environment variables.

"""

import io
import math
import datetime
from collections import defaultdict

import pandas as pd
import streamlit as st
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

# ---------------------------
# Configuration / Helpers
# ---------------------------

REMARK_MAX_CHARS = 180

st.set_page_config(page_title="Weekly Status Auto-Filler", layout="wide")


def detect_date_column(df):
    # try common date column names
    candidates = ["date", "day", "work_date", "activity_date", "Timestamp", "timestamp"]
    for c in df.columns:
        if c.lower() in candidates:
            return c
    # fallback: first column that can be parsed as date
    for c in df.columns:
        try:
            pd.to_datetime(df[c])
            return c
        except Exception:
            continue
    return None


def detect_hours_column(df):
    candidates = ["hours", "time", "duration", "hrs"]
    for c in df.columns:
        if c.lower() in candidates:
            return c
    # fallback: numeric column with small values
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if numeric:
        # choose the numeric column with median < 24
        for c in numeric:
            if df[c].median() < 24:
                return c
        return numeric[0]
    return None


def detect_task_column(df):
    candidates = ["task", "activity", "description", "work", "title", "summary"]
    for c in df.columns:
        if c.lower() in candidates:
            return c
    # fallback: first object dtype column
    for c in df.columns:
        if pd.api.types.is_object_dtype(df[c]):
            return c
    return None


def simple_remark(task_name, days_count, total_hours):
    # Generate a compact human-readable remark
    if days_count <= 1:
        return f"Worked on {task_name} for {total_hours:.2f} hours."
    else:
        return f"Worked on {task_name} across {days_count} days, totalling {total_hours:.2f} hours."


def hf_summarize(texts, hf_api_key, model="google/pegasus-xsum" ):  # model can be changed
    """
    Simple Hugging Face Inference API summarizer wrapper.
    Provide HF API key in environment or secrets, otherwise this won't run.
    This function concatenates texts and asks model to summarize into a short sentence.
    """
    import requests
    if not hf_api_key:
        raise ValueError("Missing Hugging Face API key")

    prompt = " ".join([str(t) for t in texts])
    # cut off to reasonable size
    prompt = prompt[:1200]

    headers = {"Authorization": f"Bearer {hf_api_key}"}
    api_url = f"https://api-inference.huggingface.co/models/{model}"
    payload = {"inputs": prompt, "parameters": {"max_length": 60, "min_length": 10}}
    r = requests.post(api_url, headers=headers, json=payload, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"HF inference call failed: {r.status_code} {r.text}")
    data = r.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"HF error: {data}")
    # data is usually a list of dicts with 'summary_text' or 'generated_text'
    if isinstance(data, list):
        txt = data[0].get("summary_text") or data[0].get("generated_text") or str(data[0])
    else:
        txt = str(data)
    return txt.strip()


# ---------------------------
# Streamlit UI
# ---------------------------

st.title("📄 Weekly Status — Auto-fill from CSV")
st.markdown(
    "Upload your exported CSV timesheet and (optionally) your weekly status Excel template. The app will group tasks by the original task name, sum hours, create short remarks and write the results into a copy of your template (in a new sheet named 'AutoFilled')."
)

with st.sidebar:
    st.header("Options")
    hf_key = st.text_input("Hugging Face API Key (optional)", type="password")
    use_ai = st.checkbox("Use AI for remark generation (Hugging Face)", value=False)
    if use_ai and not hf_key:
        st.info("Provide a Hugging Face API key above to enable AI remarks.")
    st.markdown("---")
    st.caption("If you don't provide a template, a simple workbook will be created containing the AutoFilled sheet.")

uploaded_csv = st.file_uploader("Upload your timesheet CSV", type=["csv"], help="CSV exported from your internal system")
uploaded_template = st.file_uploader("Upload your weekly status Excel template (optional)", type=["xlsx"], help="Optional. If omitted the app creates a simple workbook with AutoFilled sheet")

if uploaded_csv:
    try:
        df = pd.read_csv(uploaded_csv)
    except Exception:
        uploaded_csv.seek(0)
        df = pd.read_csv(uploaded_csv, encoding='latin1')

    st.success("CSV loaded — preview below")
    st.dataframe(df.head(10))

    # Auto-detect columns
    detected_date = detect_date_column(df)
    detected_task = detect_task_column(df)
    detected_hours = detect_hours_column(df)

    st.markdown("### Column mapping")
    col_date = st.selectbox("Date column", options=df.columns, index=list(df.columns).index(detected_date) if detected_date in df.columns else 0)
    col_task = st.selectbox("Task/Activity column", options=df.columns, index=list(df.columns).index(detected_task) if detected_task in df.columns else 0)
    col_hours = st.selectbox("Hours column", options=df.columns, index=list(df.columns).index(detected_hours) if detected_hours in df.columns else 0)

    btn_process = st.button("Process and Generate Weekly Status")

    if btn_process:
        with st.spinner("Processing..."):
            # Clean dataframe
            df_local = df[[col_date, col_task, col_hours]].copy()
            # parse date
            try:
                df_local[col_date] = pd.to_datetime(df_local[col_date])
            except Exception:
                # if date parse fails, leave as string
                pass

            # normalize task (keep original for output)
            df_local['__task_orig'] = df_local[col_task].astype(str)
            df_local['__hours'] = pd.to_numeric(df_local[col_hours], errors='coerce').fillna(0.0)

            # determine week range
            try:
                min_date = df_local[col_date].min()
                max_date = df_local[col_date].max()
                # if parsed as datetime-like
                if pd.api.types.is_datetime64_any_dtype(df_local[col_date]):
                    start_date = min_date.date()
                    end_date = max_date.date()
                else:
                    start_date = str(min_date)
                    end_date = str(max_date)
            except Exception:
                start_date = ""
                end_date = ""

            # grouping
            group = df_local.groupby('__task_orig')
            results = []
            for task_name, sub in group:
                total_hours = sub['__hours'].sum()
                days_count = sub[col_date].nunique() if col_date in sub.columns else sub.shape[0]

                # Create remark
                if use_ai and hf_key:
                    # pass the distinct rows (or first few) to HF summarizer
                    texts = list(sub[col_task].astype(str).unique())[:8]
                    try:
                        remark = hf_summarize(texts, hf_key)
                        if len(remark) > REMARK_MAX_CHARS:
                            remark = remark[:REMARK_MAX_CHARS].rsplit(' ', 1)[0] + '...'
                    except Exception as e:
                        st.warning(f"AI summarization failed for task '{task_name}': {e}. Falling back to simple remark.")
                        remark = simple_remark(task_name, days_count, total_hours)
                else:
                    remark = simple_remark(task_name, days_count, total_hours)

                results.append({
                    'Task (original)': task_name,
                    'Hours': round(float(total_hours), 2),
                    'Remark': remark,
                    'Days Covered': int(days_count)
                })

            results_df = pd.DataFrame(results).sort_values('Hours', ascending=False)

            st.success("Grouped tasks ready")
            st.dataframe(results_df)

            # Prepare output workbook
            if uploaded_template:
                uploaded_template.seek(0)
                out_wb = load_workbook(filename=uploaded_template)
            else:
                # create a simple workbook
                from openpyxl import Workbook
                out_wb = Workbook()
                # remove default sheet if necessary
                if 'Sheet' in out_wb.sheetnames and len(out_wb.sheetnames) == 1:
                    out_wb.remove(out_wb['Sheet'])

            sheet_name = 'AutoFilled'
            if sheet_name in out_wb.sheetnames:
                ws = out_wb[sheet_name]
                # clear existing
                for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
                    for cell in row:
                        cell.value = None
            else:
                ws = out_wb.create_sheet(sheet_name)

            # Write header metadata
            ws['A1'] = 'Start Date'
            ws['B1'] = start_date
            ws['A2'] = 'Status Date'
            ws['B2'] = datetime.date.today().isoformat()
            ws['A3'] = 'Period Covered'
            ws['B3'] = f"{start_date} to {end_date}"

            # Write table headers at row 5
            headers = ['Task (original)', 'Hours', 'Remark', 'Days Covered']
            start_row = 5
            for i, h in enumerate(headers, start=1):
                ws.cell(row=start_row, column=i, value=h)

            # Write rows
            for r_idx, row in enumerate(results_df.itertuples(index=False), start=start_row + 1):
                ws.cell(row=r_idx, column=1, value=row[0])
                ws.cell(row=r_idx, column=2, value=row[1])
                ws.cell(row=r_idx, column=3, value=row[2])
                ws.cell(row=r_idx, column=4, value=row[3])

            # Save workbook to bytes
            output_stream = io.BytesIO()
            out_wb.save(output_stream)
            output_stream.seek(0)

            st.success("Weekly status Excel is ready")

            st.download_button(label="Download completed weekly status Excel",
                               data=output_stream.getvalue(),
                               file_name=f"weekly_status_autofilled_{datetime.date.today().isoformat()}.xlsx",
                               mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

else:
    st.info("Please upload a CSV file to begin.")

# ---------------------------
# Footer / Help
# ---------------------------
st.markdown("---")
st.markdown("**Notes & Tips:**\n\n- If you want more polished AI remarks, provide a Hugging Face API key and enable AI in the sidebar.\n- The app writes results into a new sheet named `AutoFilled` so your original template remains untouched.\n- If your template expects dates and tasks in specific cells, tell me the cell locations and I can modify the app to write into those exact cells.\n")


# Requirements file suggestion
st.expander("Show recommended requirements.txt")
with st.expander("requirements.txt"):
    st.code("""streamlit
pandas
openpyxl
requests
""")

