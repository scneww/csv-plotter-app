import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# Page config
st.set_page_config(page_title="Professional CSV Plotter", layout="wide")

# Styling
st.markdown("""
<style>
    .title {
        font-weight: 600;
        font-size: 2.2rem;
        color: #1f77b4;
        font-family: 'Segoe UI', sans-serif;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #555;
        margin-bottom: 1.5rem;
    }
    .stMultiSelect > div, .stDateInput > div {
        border-radius: 6px;
        background-color: #f9f9fb;
    }
</style>
""", unsafe_allow_html=True)

# Load default data function
@st.cache_data
def load_default_data():
    df = pd.read_csv("MYCOM01.csv")
    df["datetime"] = pd.to_datetime(df["Date"] + " " + df["time"], dayfirst=True)
    return df

# Excel export helper
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=True)
    output.seek(0)
    return output.read()

# Sidebar: Upload file or use default
st.sidebar.header("🔧 ตัวเลือกข้อมูล")
uploaded_file = st.sidebar.file_uploader("อัปโหลดไฟล์ CSV", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        # Try to parse datetime, adapt here if structure different
        if "datetime" not in df.columns:
            if "Date" in df.columns and "time" in df.columns:
                df["datetime"] = pd.to_datetime(df["Date"] + " " + df["time"], dayfirst=True)
            else:
                st.sidebar.error("ไฟล์ CSV ต้องมีคอลัมน์ 'Date' และ 'time' หรือ 'datetime'")
                st.stop()
        else:
            df["datetime"] = pd.to_datetime(df["datetime"])
    except Exception as e:
        st.sidebar.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์ CSV: {e}")
        st.stop()
else:
    df = load_default_data()

# Sidebar: DateTime filter
min_datetime = df["datetime"].min()
max_datetime = df["datetime"].max()

st.sidebar.header("⏰ เลือกช่วงเวลา")
start_datetime = st.sidebar.date_input(
    "วันเริ่มต้น",
    min_datetime.date(),
    min_value=min_datetime.date(),
    max_value=max_datetime.date()
)
end_datetime = st.sidebar.date_input(
    "วันสิ้นสุด",
    max_datetime.date(),
    min_value=min_datetime.date(),
    max_value=max_datetime.date()
)

# Time inputs
start_time = st.sidebar.time_input("เวลาเริ่มต้น", min_datetime.time())
end_time = st.sidebar.time_input("เวลาสิ้นสุด", max_datetime.time())

# Combine date and time
from datetime import datetime, time as dt_time

start_dt = datetime.combine(start_datetime, start_time)
end_dt = datetime.combine(end_datetime, end_time)

if start_dt > end_dt:
    st.sidebar.error("ช่วงเวลาที่เลือกไม่ถูกต้อง: วันเริ่มต้นต้องไม่มากกว่าวันสิ้นสุด")
    st.stop()

# Sidebar: Select columns to plot
exclude_cols = ['Date', 'time', 'datetime']
available_columns = [col for col in df.columns if col not in exclude_cols]

selected_columns = st.sidebar.multiselect(
    "เลือกคอลัมน์ที่ต้องการ plot",
    options=available_columns,
    default=available_columns[:2] if len(available_columns) >= 2 else available_columns
)

if not selected_columns:
    st.warning("กรุณาเลือกอย่างน้อย 1 คอลัมน์")
    st.stop()

# Button to update graph
update_button = st.sidebar.button("อัปเดตกราฟ")

# Filter data on button click or first load
if update_button or "plot_ready" not in st.session_state:
    filtered_df = df[(df["datetime"] >= pd.to_datetime(start_dt)) & (df["datetime"] <= pd.to_datetime(end_dt))]

    if filtered_df.empty:
        st.warning("ไม่มีข้อมูลในช่วงเวลาที่เลือก")
        st.stop()

    # Plot graph
    color_sequence = px.colors.qualitative.Plotly
    fig = go.Figure()

    for i, col in enumerate(selected_columns):
        fig.add_trace(go.Scatter(
            x=filtered_df["datetime"],
            y=filtered_df[col],
            mode="lines",
            name=col,
            line=dict(width=1.5, color=color_sequence[i % len(color_sequence)]),
            hovertemplate=f"<b>{col}</b>: %{{y:.2f}}<br><i>Time</i>: %{{x|%Y-%m-%d %H:%M:%S}}<extra></extra>"
        ))

    fig.update_layout(
        template="plotly_white",
        height=600,
        hovermode='x unified',
        font=dict(family="Segoe UI", size=13),
        title=dict(
            text="ข้อมูลที่เลือกแสดงผล",
            font=dict(size=20),
            x=0.5
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        xaxis=dict(
            title="Time",
            showspikes=True,
            spikemode='across',
            spikesnap='cursor',
            spikecolor="grey",
            spikethickness=1,
            showline=True,
            linecolor='black'
        ),
        yaxis=dict(
            title="Value",
            showgrid=True,
            showline=True,
            linecolor='black'
        ),
        margin=dict(l=40, r=40, t=80, b=40)
    )
    st.session_state['plot_ready'] = True
    st.session_state['filtered_df'] = filtered_df
    st.session_state['selected_columns'] = selected_columns
    st.plotly_chart(fig, use_container_width=True)

# Show summary table and download
if "plot_ready" in st.session_state:
    filtered_df = st.session_state['filtered_df']
    selected_columns = st.session_state['selected_columns']
    summary_df = filtered_df[selected_columns].agg(['min', 'mean', 'max']).T
    summary_df = summary_df.rename(columns={'min': 'Min', 'mean': 'Avg', 'max': 'Max'})

    st.markdown("### สรุปค่าทางสถิติของข้อมูลที่เลือก")
    st.dataframe(summary_df.style.format("{:.2f}"))

    excel_data = to_excel(summary_df)
    st.download_button(
        label="⬇️ ดาวน์โหลดสรุปเป็น Excel",
        data=excel_data,
        file_name="summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


#streamlit run D:\Pyt\plotdata.rev2.py

