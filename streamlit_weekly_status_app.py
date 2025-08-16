import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("Weekly Status Preview (Hover Copy Enabled)")

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

    df.columns = df.columns.str.strip()

    # -------------------------------
    # Step 2: Display Table with Hover Copy
    # -------------------------------
    table_html = df.to_html(index=False, escape=False, classes="hover-copy-table")

    st.markdown(
        f"""
        <style>
        /* Make table full width and cells padded */
        .hover-copy-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .hover-copy-table th, .hover-copy-table td {{
            border: 1px solid #ddd;
            padding: 8px;
            position: relative;
        }}
        .hover-copy-table td:hover::after {{
            content: '📋';
            position: absolute;
            right: 5px;
            top: 50%;
            transform: translateY(-50%);
            cursor: pointer;
            font-size: 14px;
        }}
        .hover-copy-table th {{
            background-color: #f2f2f2;
            text-align: left;
        }}
        </style>

        <script>
        const tds = window.parent.document.querySelectorAll('.hover-copy-table td');
        tds.forEach(td => {{
            td.addEventListener('click', () => {{
                navigator.clipboard.writeText(td.innerText);
            }});
        }});
        </script>

        {table_html}
        """,
        unsafe_allow_html=True
    )
