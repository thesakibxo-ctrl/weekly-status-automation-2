import streamlit as st
import pandas as pd
import openpyxl
from io import BytesIO

# -------------------------------
# Streamlit Page Config
# -------------------------------
st.set_page_config(layout="centered")

# -------------------------------
# Header with logo inline
# -------------------------------
logo_svg = """
<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 102 63" fill="none">
<path d="M37 63H52L64 0H49L37 63Z" fill="white"/>
<path d="M32.5 58.5L17 31.5L32.5 4.5H16L0 31.5L16 58.5H32.5Z" fill="#E92E34"/>
<path d="M69 58.5L84.5 31.5L69 4.5H85.5L101.5 31.5L85.5 58.5H69Z" fill="#E92E34"/>
</svg>
"""

st.markdown(
    f"""
    <div style="display:flex; align-items:center; gap:10px;">
        <div>{logo_svg}</div>
        <h1 style="margin:0; color:white; font-size:32px;">Weekly Status Generate</h1>
    </div>
    """,
    unsafe_allow_html=True
)

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

    # Convert hours+minutes to decimal
    if "hours" in df.columns and "minutes" in df.columns:
        df["spent_hours"] = df["hours"].astype(float) + df["minutes"].astype(float)/60
    elif "spent hours" in df.columns:
        df["spent_hours"] = df["spent hours"].astype(float)
    else:
        st.error("CSV must have either 'Hours' and 'Minutes' or 'Spent Hours'.")
        st.stop()

    # -------------------------------
    # Step 2: Merge tasks
    # -------------------------------
    communication_tasks = df[df["activity"].str.lower() == "communication"]
    other_tasks = df[df["activity"].str.lower() != "communication"]

    rows = []

    # Merge Communication
    if not communication_tasks.empty:
        comm_hours = communication_tasks["spent_hours"].sum()
        rows.append({"Task Title": "Communication", "Spent Hours Decimal": comm_hours})

    # Merge duplicate other tasks
    if not other_tasks.empty:
        grouped = other_tasks.groupby("description", as_index=False).agg({"spent_hours": "sum"})
        for _, row in grouped.iterrows():
            rows.append({"Task Title": row["description"], "Spent Hours Decimal": row["spent_hours"]})

    processed_tasks = pd.DataFrame(rows)

    # -------------------------------
    # Step 3: Format Spent Hours as "0h 0m"
    # -------------------------------
    def format_hours(decimal_hours):
        total_minutes = round(decimal_hours * 60)
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h}h {m}m"

    processed_tasks["Spent Hours"] = processed_tasks["Spent Hours Decimal"].apply(format_hours)

    # -------------------------------
    # Step 4: Add Weekly Total Row for display
    # -------------------------------
    total_decimal_hours = processed_tasks["Spent Hours Decimal"].sum()
    total_formatted_hours = format_hours(total_decimal_hours)
    
    weekly_total = pd.DataFrame([{"Task Title": "Weekly Total", "Spent Hours": total_formatted_hours}])
    final_table_display = pd.concat([processed_tasks[["Task Title", "Spent Hours"]], weekly_total], ignore_index=True)

    # -------------------------------
    # Step 5: Display Table with Weekly Total Highlight
    # -------------------------------
    st.subheader("Weekly Status Preview")

    # Period Covered below the heading
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    start_date = df['date'].min()
    end_date = df['date'].max()
    period_covered = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
    st.markdown(
        f"<p style='color:white; font-size:16px; font-weight:bold;'>Period Covered: {period_covered}</p>",
        unsafe_allow_html=True
    )

    # Highlight Weekly Total
    def highlight_weekly_total(row):
        if row["Task Title"] == "Weekly Total":
            return ['background-color: rgba(255,255,255,0.1)']*len(row)
        return ['']*len(row)

    st.dataframe(
        final_table_display.style.apply(highlight_weekly_total, axis=1),
        use_container_width=True
    )

    # Hide index visually
    st.markdown(
        """
        <style>
        div[data-testid="stDataFrame"] table tbody th {display:none}
        div[data-testid="stDataFrame"] table thead th:first-child {display:none}
        </style>
        """,
        unsafe_allow_html=True
    )

    # -------------------------------
    # Step 6: Download Filled XLSX Template
    # -------------------------------
    try:
        # Load the template workbook from the file system
        template_path = "Enosis-Schedulewise Weekly Status Template.xlsx"
        workbook = openpyxl.load_workbook(template_path)
        
        # Select the target sheet
        sheet = workbook["Weekly Task Status V2.0"]

        # --- Data Insertion Logic ---
        start_row = 11 # As specified, data starts from row 11
        
        # Write each processed task to the sheet
        for index, task in processed_tasks.iterrows():
            current_row = start_row + index
            sheet[f'C{current_row}'] = task['Task Title']
            sheet[f'G{current_row}'] = task['Spent Hours']
        
        # Save the modified workbook to an in-memory buffer
        excel_buffer = BytesIO()
        workbook.save(excel_buffer)
        excel_buffer.seek(0) # Go to the beginning of the buffer

        st.download_button(
            "📥 Download Filled Status (.xlsx)",
            excel_buffer,
            "weekly_status_filled.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except FileNotFoundError:
        st.error(f"Error: The template file '{template_path}' was not found. Please make sure it's in the same directory as the script.")
    except KeyError:
        st.error("Error: Could not find the sheet named 'Weekly Task Status V2.0' in the Excel template. Please check the file.")
    except Exception as e:
        st.error(f"An unexpected error occurred while creating the Excel file: {e}")

# -------------------------------
# Footer
# -------------------------------
st.markdown(
    """
    <div style="
        position: fixed;
        bottom: 32px;
        width: 100%;
        text-align: left;
        color: white;
        font-size: 14px;
        opacity: 0.7;
        font-weight: 400
    ">
        Created by Sakib Hasan
    </div>
    """,
    unsafe_allow_html=True
)
