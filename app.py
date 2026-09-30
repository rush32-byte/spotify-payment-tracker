import os
import pandas as pd
import streamlit as st

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
RECEIPTS_DIR = "receipts"
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

# Ensure receipts folder exists locally
if not os.path.exists(RECEIPTS_DIR):
  os.makedirs(RECEIPTS_DIR)


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

st.title("🎵 Spotify Family Payment Tracker")
st.markdown(
    "Upload payment receipts, track monthly payments, and filter receipts by"
    " member."
)

with st.sidebar:
  st.header("⚙️ Settings")
  monthly_fee = st.number_input("Monthly Spotify Plan Cost (RM)", value=28.0)
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
    if st.button("Confirm, Save Receipt & Tick Payment"):
      file_extension = os.path.splitext(uploaded_file.name)[1]
      safe_filename = f"{selected_member}_{selected_month}{file_extension}"
      file_path = os.path.join(RECEIPTS_DIR, safe_filename)

      with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

      idx = st.session_state.payment_data[
          st.session_state.payment_data["Member"] == selected_member
      ].index[0]
      st.session_state.payment_data.at[idx, selected_month] = True
      st.session_state.payment_data.to_csv(DATA_FILE, index=False)

      st.balloons()
      st.success(
          f"Successfully saved receipt and marked {selected_month} as PAID for"
          f" {selected_member}!"
      )
      st.rerun()

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

# --- MEMBER-FILTERED RECEIPT GALLERY VIEWER ---
st.markdown("---")
st.subheader("📂 Member Receipt Gallery")

if os.path.exists(RECEIPTS_DIR):
  all_receipt_files = os.listdir(RECEIPTS_DIR)

  # Select which member's receipts to view
  members_list = st.session_state.payment_data["Member"].tolist()
  gallery_member = st.selectbox(
      "View receipts for member:", members_list, key="gallery_member_select"
  )

  # Filter files matching the selected member
  member_receipts = [
      f for f in all_receipt_files if f.startswith(f"{gallery_member}_")
  ]

  if member_receipts:
    selected_receipt = st.selectbox(
        f"Select {gallery_member}'s receipt file:",
        member_receipts,
        key="gallery_receipt_select",
    )
    if selected_receipt:
      file_path = os.path.join(RECEIPTS_DIR, selected_receipt)
      if selected_receipt.lower().endswith((".png", ".jpg", ".jpeg")):
        st.image(
            file_path, caption=selected_receipt, use_container_width=True
        )
      else:
        st.info(f"Selected file: {selected_receipt} (PDF format)")
        with open(file_path, "rb") as f:
          st.download_button(
              label=f"Download {selected_receipt}",
              data=f,
              file_name=selected_receipt,
          )

      # Delete button specific to that receipt
      if st.button("🗑️️ Delete Selected Receipt", key="delete_receipt_btn"):
        if os.path.exists(file_path):
          os.remove(file_path)

        try:
          name_part = os.path.splitext(selected_receipt)[0]
          parts = name_part.split("_")
          if len(parts) >= 2:
            m_name, m_month = parts[0], parts[1]
            if (
                m_name in st.session_state.payment_data["Member"].values
                and m_month in months
            ):
              idx = st.session_state.payment_data[
                  st.session_state.payment_data["Member"] == m_name
              ].index[0]
              st.session_state.payment_data.at[idx, m_month] = False
              st.session_state.payment_data.to_csv(DATA_FILE, index=False)
        except Exception:
          pass

        st.success(
            f"Successfully deleted {selected_receipt} and updated payment"
            " status!"
        )
        st.rerun()
  else:
    st.info(f"No receipts uploaded yet for {gallery_member}.")
else:
  st.info("Receipts folder not found.")