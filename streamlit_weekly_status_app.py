import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# ------------------ SETTINGS ------------------
st.set_page_config(page_title="Weekly Status", layout="centered")
st.markdown("<h1 style='text-align: center;'>📊 Weekly Status Report</h1>", unsafe_allow_html=True)

# ------------------ CSV UPLOAD ------------------
uploaded_file = st.file_uploader("Upload your weekly status CSV", type=["csv"])

# ------------------ HELPER: Convert hours/minutes ------------------
def parse_hours(text):
    if pd.isna(text):
        return 0
    text = str(text)
    h, m = 0, 0
    if 'h' in text:
        h = int(text.split('h')[0])
    if 'm' in text:
        m = int(text.split('h')[-1].replace('m','').strip())
    return h * 60 + m

def format_hours(minutes):
    h = minutes // 60
    m = minutes % 60
    return f"{h}h {m}m"

# ------------------ COPY-ON-HOVER TABLE FUNCTION ------------------
def display_table_with_copy(df):
    table_html = "<div style='overflow:auto; max-height:70vh;'>"
    table_html += "<table style='border-collapse: collapse; margin:auto;'>"
    
    # headers
    table_html += "<thead style='position:sticky; top:0; background:#f0f0f0;'>"
    table_html += "<tr>" + "".join(
        [f"<th style='padding:8px; border:1px solid #ccc;'>{col}</th>" for col in df.columns]
    ) + "</tr>"
    table_html += "</thead>"
    
    # rows
    table_html += "<tbody>"
    for _, row in df.iterrows():
        is_total = str(row[0]).strip().lower() == "weekly total"
        bg_color = "#fff9c4" if is_total else "#ffffff"  # highlight weekly total
        table_html += f"<tr style='transition: background-color 0.2s;'>"
        for val in row:
            table_html += f"""
            <td style='padding:8px; border:1px solid #ccc; position:relative; background-color:{bg_color};'>
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
                    cursor:pointer;
                ">Copy</button>
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

    # CSS + JS for hover, copy button, and tooltip animation
    custom_script = """
    <style>
        td:hover .copy-btn { visibility: visible; }
        tbody tr:hover { background-color: #e6f7ff !important; }
    </style>
    <script>
        const buttons = window.parent.document.querySelectorAll('.copy-btn');
        buttons.forEach(btn => {
            btn.onclick = function(e) {
                const td = btn.parentElement;
                const text = td.innerText.replace('Copy','').replace('Copied!','').trim();
                navigator.clipboard.writeText(text);
                
                // Show tooltip animation
                const tooltip = td.querySelector('.copied-tooltip');
                tooltip.style.visibility = 'visible';
                tooltip.style.opacity = 1;
                setTimeout(()=>{ tooltip.style.opacity = 0; tooltip.style.visibility='hidden'; }, 1000);
            }
        });
    </script>
    """
    components.html(table_html + custom_script, height=400, scrolling=True)

# ------------------ SHOW TABLE ------------------
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    if 'Date' not in df.columns:
        st.error("❌ CSV must contain a 'Date' column to extract week range.")
    else:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])

        # Format dates like "July 27 - August 02, 2025"
        start_date = df['Date'].min()
        end_date = df['Date'].max()
        start_str = start_date.strftime("%B %d")
        end_str = end_date.strftime("%B %d, %Y")
        project_covered_text = f"{start_str} - {end_str}"
        st.markdown(f"<h3 style='text-align:center; font-size:20px;'>Project Covered: {project_covered_text}</h3>", unsafe_allow_html=True)

        # Calculate weekly total hours if 'Spent Hours' exists
        if 'Spent Hours' in df.columns:
            total_minutes = df['Spent Hours'].apply(parse_hours).sum()
            weekly_total_row = pd.DataFrame({col: [""] for col in df.columns})
            weekly_total_row.loc[0, 'Task Title' if 'Task Title' in df.columns else df.columns[0]] = "Weekly Total"
            weekly_total_row.loc[0, 'Spent Hours'] = format_hours(total_minutes)
            df = pd.concat([df, weekly_total_row], ignore_index=True)

        # Display table
        display_table_with_copy(df)

        # Download CSV
        st.download_button(
            "📥 Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            "weekly_status.csv",
            "text/csv"
        )
