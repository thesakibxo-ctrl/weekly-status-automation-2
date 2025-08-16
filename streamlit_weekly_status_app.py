import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

st.set_page_config(layout="centered")
st.title("Weekly Status Generate")

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

    # Normalize columns
    df.columns = df.columns.str.strip().str.lower()

    # Check required columns
    required_cols = ["description", "activity", "date"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"CSV is missing required columns: {missing_cols}")
        st.stop()

    # Remove irrelevant rows
    df = df[~df["description"].isin(["", "Total", "Weekly Total"])]
    df = df.dropna(subset=["description", "activity", "date"])

    # -------------------------------
    # Step 1b: Period Covered
    # -------------------------------
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    start_date = df.iloc[0]['date']
    end_date = df.iloc[-1]['date']
    period_covered = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
    # Display period covered with copy button
    st.markdown(f"""
    <div style='display:flex; align-items:center; justify-content:flex-start; margin-bottom:10px;'>
        <span style='color:white; font-size:20px;'>Period Covered: {period_covered}</span>
        <button class="copy-btn" style="
            margin-left:10px;
            border:none;
            background:#1976d2;
            color:white;
            border-radius:4px;
            padding:2px 6px;
            font-size:12px;
            cursor:pointer;">Copy</button>
        <span class="copied-tooltip" style="
            visibility:hidden;
            background:#333;
            color:#fff;
            padding:2px 6px;
            border-radius:4px;
            font-size:12px;
            opacity:0;
            transition: opacity 0.3s;
            margin-left:10px;">Copied!</span>
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------
    # Step 2: Convert hours+minutes to decimal
    # -------------------------------
    if "hours" in df.columns and "minutes" in df.columns:
        df["spent_hours"] = df["hours"].astype(float) + df["minutes"].astype(float)/60
    elif "spent hours" in df.columns:
        df["spent_hours"] = df["spent hours"].astype(float)
    else:
        st.error("CSV must have either 'Hours' and 'Minutes' or 'Spent Hours'.")
        st.stop()

    # -------------------------------
    # Step 3: Merge tasks
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
    # Step 4: Format Spent Hours as "0h 0m"
    # -------------------------------
    def format_hours(decimal_hours):
        total_minutes = round(decimal_hours * 60)
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h}h {m}m"

    processed_tasks["Spent Hours"] = processed_tasks["Spent Hours"].apply(format_hours)

    # -------------------------------
    # Step 5: Add Weekly Total Row
    # -------------------------------
    total_minutes = processed_tasks["Spent Hours"].apply(
        lambda x: int(x.split("h")[0])*60 + int(x.split(" ")[1].replace("m",""))
    ).sum()
    total_h = total_minutes // 60
    total_m = total_minutes % 60
    weekly_total = pd.DataFrame([{
        "Task Title": "Weekly Total",
        "Spent Hours": f"{total_h}h {total_m}m"
    }])

    final_table = pd.concat([processed_tasks, weekly_total], ignore_index=True)

    # -------------------------------
    # Step 6: Display Table with Copy-on-Hover
    # -------------------------------
    def display_table_with_copy(df):
        num_rows = len(df)
        height_px = min(70*num_rows, 600)  # dynamic height, max 600px

        # Build HTML table
        table_html = f"<div style='overflow:auto; max-height:{height_px}px; background-color: rgb(19,23,32); padding:10px; border-radius:6px;'>"
        table_html += "<table style='border-collapse: collapse; margin:auto; width:100%;'>"

        # Header
        table_html += "<thead style='position: sticky; top: 0; background-color: rgb(19,23,32); color:white;'>"
        table_html += "<tr>" + "".join([f"<th style='padding:8px; border:1px solid #555;'>{col}</th>" for col in df.columns]) + "</tr>"
        table_html += "</thead>"

        # Body
        table_html += "<tbody>"
        for _, row in df.iterrows():
            table_html += "<tr style='transition: background-color 0.2s;'>"
            for val in row:
                table_html += f"""
                <td style='padding:8px; border:1px solid #555; color:white; position:relative;'>
                    {val}
                    <button class="copy-btn" style="
                        visibility:hidden;
                        position:absolute;
                        top:4px;
                        right:4px;
                        border:none;
                        background:#1976d2;
                        color:white;
                        border-radius:4px;
                        padding:2px 6px;
                        font-size:12px;
                        cursor:pointer;">Copy</button>
                    <span class="copied-tooltip" style="
                        visibility:hidden;
                        position:absolute;
                        top:4px;
                        right:50px;
                        background:#333;
                        color:#fff;
                        padding:2px 6px;
                        border-radius:4px;
                        font-size:12px;
                        opacity:0;
                        transition: opacity 0.3s;">Copied!</span>
                </td>
                """
            table_html += "</tr>"
        table_html += "</tbody></table></div>"

        # JS + CSS for hover and copy
        custom_script = """
        <style>
            td:hover .copy-btn { visibility: visible; }
            tbody tr:hover { background-color: rgba(255,255,255,0.1) !important; }
        </style>
        <script>
            const buttons = window.parent.document.querySelectorAll('.copy-btn');
            buttons.forEach(btn => {
                btn.onclick = function(e) {
                    const td = btn.parentElement;
                    const text = td.innerText.replace('Copy','').replace('Copied!','').trim();
                    navigator.clipboard.writeText(text);
                    const tooltip = td.querySelector('.copied-tooltip');
                    tooltip.style.visibility = 'visible';
                    tooltip.style.opacity = 1;
                    setTimeout(()=>{ tooltip.style.opacity = 0; tooltip.style.visibility='hidden'; }, 1000);
                }
            });
        </script>
        """
        components.html(table_html + custom_script, height=height_px+20, scrolling=True)

    st.subheader("Weekly Status Preview")
    display_table_with_copy(final_table[["Task Title", "Spent Hours"]])

    # Download CSV
    st.download_button(
        "📥 Download CSV",
        final_table.to_csv(index=False).encode("utf-8"),
        "weekly_status.csv",
        "text/csv"
    )
