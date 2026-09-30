import io
import os
import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(
    page_title="Spotify Family Payment Tracker", page_icon="🎵", layout="wide"
)

# --- CLEAN LIGHT BLUE & WHITE CSS THEME ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #F4F8FB;
        color: #1E293B;
    }
    header[data-testid="stHeader"] {
        background-color: rgba(0,0,0,0);
    }
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    h1, h2, h3 {
        color: #0F172A !important;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    .stButton>button {
        background-color: #2563EB;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        border: none;
        font-weight: 600;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }
    .stButton>button:hover {
        background-color: #1D4ED8;
        color: white;
    }
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }
    [data-testid="stMetricValue"] {
        color: #2563EB !important;
    }
    [data-testid="stFileUploader"] {
        background-color: #FFFFFF;
        border: 2px dashed #93C5FD;
        border-radius: 12px;
        padding: 15px;
    }
    [data-testid="stDataFrame"] {
        background-color: #FFFFFF;
        border-radius: 10px;
        border: 1px solid #E2E8F0;
    }
    </style>
""",
    unsafe_allow_html=True,
)

DATA_FILE = "spotify_payments.csv"
months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


def load_data():
  if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    for m in months:
      if m in df.columns:
        df[m] = df[m].astype(bool)
    return df
  else:
    df = pd.DataFrame({
        "Member": ["Faris", "Ieda", "Husna", "Afiqah"],
        **{month: [False] * 4 for month in months},
    })
    return df


if "payment_data" not in st.session_state:
  st.session_state.payment_data = load_data()


# --- GOOGLE DRIVE UPLOAD HELPER ---
def upload_to_drive(file_obj, filename, member, month):
  try:
    # Check if credentials exist in Streamlit secrets
    if "gcp_service_account" not in st.secrets:
      return (
          False,
          "Google Drive secrets not configured yet in Streamlit settings.",
      )

    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    service = build("drive", "v3", credentials=creds)

    folder_id = st.secrets["google_drive"][
        "folder_id"
    ]  # Your Google Drive Folder ID

    file_metadata = {
        "name": f"{member}_{month}_{filename}",
        "parents": [folder_id],
    }

    media = MediaIoBaseUpload(
        io.BytesIO(file_obj.getvalue()),
        mimetype=file_obj.type,
        resumable=True,
    )

    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )
    return True, file.get("webViewLink")
  except Exception as e:
    return False, str(e)


st.title("🎵 Spotify Family Payment Tracker")
st.markdown(
    "Upload payment receipts to save them to Google Drive and update your"
    " shared billing tracker."
)

with st.sidebar:
  st.header("⚙️ Settings")
  monthly_fee = st.number_input("Monthly Spotify Plan Cost (RM)", value=24.90)
  expected_split = round(monthly_fee / 4, 2)
  st.info(f"💡 Each member owes:\n### **RM {expected_split} / month**")

  st.markdown("---")
  if st.button("🔄 Reset All Data"):
    if os.path.exists(DATA_FILE):
      os.remove(DATA_FILE)
    st.session_state.payment_data = pd.DataFrame({
        "Member": ["Faris", "Ieda", "Husna", "Afiqah"],
        **{month: [False] * 4 for month in months},
    })
    st.rerun()

col1, col2 = st.columns([1, 1], gap="medium")

with col1:
  st.subheader("📤 Upload Bank Receipt")
  uploaded_file = st.file_uploader(
      "Choose an image or PDF receipt", type=["png", "jpg", "jpeg", "pdf"]
  )

  members_list = st.session_state.payment_data["Member"].tolist()
  selected_member = st.selectbox("Assign Payment To:", members_list)
  selected_month = st.selectbox("Select Month:", months)

  if uploaded_file is not None:
    if st.button("Confirm, Upload to Drive & Tick Payment"):
      with st.spinner("Uploading receipt to Google Drive..."):
        success, info = upload_to_drive(
            uploaded_file, uploaded_file.name, selected_member, selected_month
        )

      if success:
        idx = st.session_state.payment_data[
            st.session_state.payment_data["Member"] == selected_member
        ].index[0]
        st.session_state.payment_data.at[idx, selected_month] = True
        st.session_state.payment_data.to_csv(DATA_FILE, index=False)
        st.balloons()
        st.success(f"Marked {selected_month} as PAID for {selected_member}!")
        st.success(f"Receipt successfully saved to Google Drive: {info}")
        # Removed st.rerun() temporarily so you can read any message if needed
      else:
        st.error(f"Google Drive Upload Failed Details: {info}")

with col2:
  st.subheader("📊 Summary Statistics")
  if selected_month in st.session_state.payment_data.columns:
    current_month_paid = st.session_state.payment_data[selected_month].sum()
    collected_amount = current_month_paid * expected_split
    st.metric(
        label=f"Collected for {selected_month}",
        value=f"RM {collected_amount:.2f}",
        delta=f"Target: RM {monthly_fee:.2f}",
    )

st.markdown("---")
st.subheader("📅 Yearly Payment Status")

column_cfg = {"Member": st.column_config.TextColumn("Member", disabled=True)}
for m in months:
  column_cfg[m] = st.column_config.CheckboxColumn(m, default=False)

edited_df = st.data_editor(
    st.session_state.payment_data,
    column_config=column_cfg,
    use_container_width=True,
    hide_index=True,
    key="payment_editor",
)

if not edited_df.equals(st.session_state.payment_data):
  st.session_state.payment_data = edited_df
  st.session_state.payment_data.to_csv(DATA_FILE, index=False)
  st.rerun()