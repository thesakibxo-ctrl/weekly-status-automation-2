import streamlit as st
import pandas as pd

# ------------------ SETTINGS ------------------
st.set_page_config(page_title="Weekly Status", layout="centered")
st.title("📊 Weekly Status Report")

# ------------------ INPUTS ------------------
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date")
with col2:
    end_date = st.date_input("End Date")

uploaded_file = st.file_uploader("Upload your weekly status CSV", type=["csv"])

# ------------------ HELPER: COPY TABLE ------------------
def make_table_with_copy(df):
    table_html = "<table style='border-collapse: collapse; margin: auto;'>"
    # headers
    table_html += "<tr>" + "".join(
        [f"<th style='padding:8px;border:1px solid #ccc;'>{col}</th>" for col in df.columns]
    ) + "</tr>"
    # rows
    for _, row in df.iterrows():
        table_html += "<tr>"
        for val in row:
            table_html += f"""
            <td style='padding:8px; border:1px solid #ccc; position:relative;'>
                {val}
                <span class="copy-icon" style="
                    visibility:hidden;
                    cursor:pointer;
                    position:absolute;
                    right:4px;
                    top:4px;
                    font-size:12px;
                    color:#888;">📋</span>
            </td>
            """
        table_html += "</tr>"
    table_html += "</table>"

    # CSS + JS for copy-on-hover
    custom_script = """
    <style>
        td:hover .copy-icon { visibility: visible; }
    </style>
    <script>
        const icons = window.parent.document.querySelectorAll('.copy-icon');
        icons.forEach(icon => {
            icon.onclick = function(e) {
                const text = icon.parentElement.innerText.replace('📋','').trim();
                navigator.clipboard.writeText(text);
                icon.innerText = "✅";
                setTimeout(()=>{ icon.innerText = "📋"; }, 1000);
            }
        });
    </script>
    """
    return table_html + custom_script

# ------------------ SHOW TABLE ------------------
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # Show reporting period
    st.subheader(f"📅 Reporting Period: {start_date} → {end_date}")
    
    # Show table with copy-on-hover
    st.markdown(make_table_with_copy(df), unsafe_allow_html=True)
    
    # Optional: download button
    st.download_button(
        "📥 Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        "weekly_status.csv",
        "text/csv"
    )
