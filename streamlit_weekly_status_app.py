import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Weekly Status", page_icon="📊", layout="centered")

st.title("📊 Weekly Status App")

# Sidebar for API key
api_key = st.sidebar.text_input("🔑 Enter your OpenRouter API Key (optional)", type="password")

# Upload CSV
uploaded_file = st.file_uploader("Upload your weekly status CSV", type=["csv"])

# Function to get AI remark
def get_ai_remark(task, api_key):
    if not api_key:
        return ""  # If no key, return empty remark
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "http://localhost:8501/",
                "X-Title": "Weekly Status App"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "user", "content": f"Write a short remark for this task: {task}"}
                ],
                "max_tokens": 40
            }
        )
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"(Error: {str(e)})"

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # Add remarks column if not present
    if "Remarks" not in df.columns:
        df["Remarks"] = ""

    # Generate AI remarks if key is provided
    if api_key:
        with st.spinner("✨ Generating AI remarks..."):
            df["Remarks"] = df["Task"].apply(lambda x: get_ai_remark(x, api_key))

    # Show Start & End Date (separated from table)
    if "Start Date" in df.columns and "End Date" in df.columns:
        st.markdown(
            f"**📅 Reporting Period:** {df['Start Date'].iloc[0]} → {df['End Date'].iloc[0]}"
        )

    # Show final table
    st.dataframe(df, use_container_width=True)

    # Option to download updated CSV
    st.download_button(
        "📥 Download Updated CSV",
        df.to_csv(index=False).encode("utf-8"),
        "weekly_status_with_remarks.csv",
        "text/csv"
    )
