import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# ------------------ SETTINGS ------------------
st.set_page_config(page_title="Weekly Status", layout="centered")

# Add Enosis logo
st.markdown(
    """
    <div style="text-align: center; margin-bottom:10px;">
        <img src="https://www.enosisbd.com/wp-content/uploads/2020/07/enosis-logo@2x.png" width="200" alt="Enosis Logo">
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("<h2 style='text-align: center; color:white;'>📊 Weekly Status Report</h2>", unsafe_allow_html=True)

# ------------------ CSV UPLOAD ------------------
uploaded_file = st.file_uploader("Upload your weekly status CSV", type=["csv"])

# ------------------ COPY-ON-HOVER TABLE FUNCTION ------------------
def display_table_with_copy(df):
    # Build HTML table
    table_html = f"<div style='overflow:auto; max-height:70vh; background-color: rgb(19,23,32); padding:10px; border-radius:6px;'>"
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
            <td style='padding:8px; border:1px solid #555; color:black; position:relative;'>
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
    components.html(table_html + custom_script, height=400, scrolling=True)

# ------------------ SHOW TABLE ------------------
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # Extract week range from Date column for Project Covered
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        start_date = df['Date'].min()
        end_date = df['Date'].max()
        start_str = start_date.strftime("%B %d")
        end_str = end_date.strftime("%B %d, %Y")
        project_covered_text = f"{start_str} - {end_str}"
        st.markdown(f"<h3 style='text-align:center; font-size:20px; color:white;'>Project Covered: {project_covered_text}</h3>", unsafe_allow_html=True)

    display_table_with_copy(df)

    # Download CSV
    st.download_button(
        "📥 Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        "weekly_status.csv",
        "text/csv"
    )
