import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# -------------------------------
# Streamlit Page Config
# -------------------------------
st.set_page_config(page_title="Weekly Status", layout="centered")
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
        rows.append({"Task Title": "Communication", "Spent Hours": comm_hours})

    # Merge duplicate other tasks
    if not other_tasks.empty:
        grouped = other_tasks.groupby("description", as_index=False).agg({"spent_hours": "sum"})
        for _, row in grouped.iterrows():
            rows.append({"Task Title": row["description"], "Spent Hours": row["spent_hours"]})

    processed_tasks = pd.DataFrame(rows)

    # -------------------------------
    # Step 3: Format Spent Hours as "0h 0m"
    # -------------------------------
    def format_hours(decimal_hours):
        total_minutes = round(decimal_hours * 60)
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h}h {m}m"

    processed_tasks["Spent Hours"] = processed_tasks["Spent Hours"].apply(format_hours)

    # -------------------------------
    # Step 4: Add Weekly Total Row
    # -------------------------------
    total_minutes = processed_tasks["Spent Hours"].apply(
        lambda x: int(x.split("h")[0])*60 + int(x.split(" ")[1].replace("m",""))
    ).sum()
    total_h = total_minutes // 60
    total_m = total_minutes % 60
    weekly_total = pd.DataFrame([{"Task Title": "Weekly Total", "Spent Hours": f"{total_h}h {total_m}m"}])
    final_table = pd.concat([processed_tasks, weekly_total], ignore_index=True)

    # -------------------------------
    # Step 5: Period Covered
    # -------------------------------
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    start_date = df['date'].min()
    end_date = df['date'].max()
    period_covered = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

    st.subheader("Weekly Status Preview")
    st.markdown(
        f"<p style='color:white; font-size:16px; font-weight:bold;'>Period Covered: {period_covered}</p>",
        unsafe_allow_html=True
    )

    # -------------------------------
    # Step 6: Generate Tailwind / Flowbite Table
    # -------------------------------
    table_html = f"""
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <div class="overflow-x-auto p-2 bg-gray-900 rounded" style="max-height:70vh;">
        <table class="min-w-full divide-y divide-gray-700">
            <thead class="bg-gray-800 text-white sticky top-0">
                <tr>
                    {"".join([f"<th class='px-4 py-2 text-left'>{col}</th>" for col in final_table.columns])}
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-700 text-gray-900">
    """

    for _, row in final_table.iterrows():
        bg_class = "bg-white/10" if row["Task Title"] == "Weekly Total" else ""
        table_html += f"<tr class='{bg_class} hover:bg-white/20 transition-colors'>"
        for val in row:
            table_html += f"""
            <td class='px-4 py-2 relative'>{val}
                <button class="copy-btn hidden absolute top-1 right-1 text-xs bg-blue-600 text-white px-1 rounded">Copy</button>
            </td>
            """
        table_html += "</tr>"

    table_html += """
            </tbody>
        </table>
    </div>
    <script>
    const buttons = document.querySelectorAll('.copy-btn');
    buttons.forEach(btn => {
        btn.parentElement.addEventListener('mouseenter', () => btn.classList.remove('hidden'));
        btn.parentElement.addEventListener('mouseleave', () => btn.classList.add('hidden'));
        btn.onclick = function() {
            const text = btn.parentElement.innerText.replace('Copy','').trim();
            navigator.clipboard.writeText(text);
            const tooltip = document.createElement('span');
            tooltip.innerText = 'Copied!';
            tooltip.className = 'absolute top-1 right-10 bg-black text-white text-xs px-1 rounded';
            btn.parentElement.appendChild(tooltip);
            setTimeout(()=>{ tooltip.remove(); }, 1000);
        };
    });
    </script>
    """

    components.html(table_html, height=500, scrolling=True)

    # -------------------------------
    # Step 7: Download CSV
    # -------------------------------
    st.download_button(
        "📥 Download CSV",
        final_table.to_csv(index=False).encode("utf-8"),
        "weekly_status.csv",
        "text/csv"
    )
