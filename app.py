import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="在庫管理アプリ", layout="wide")
st.title("🍎 食品在庫管理システム")

# スプレッドシートのURL
URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# 💡 修正：Secretsから必要な認証情報だけを渡す
try:
    conn = st.connection("gsheets", type=GSheetsConnection, 
                         type_service_account=st.secrets["type"],
                         project_id=st.secrets["project_id"],
                         private_key_id=st.secrets["private_key_id"],
                         private_key=st.secrets["private_key"],
                         client_email=st.secrets["client_email"])
except Exception as e:
    st.error("認証情報の読み込みに失敗しました。")
    st.stop()

# --- 入力フォーム ---
st.sidebar.header("新しい在庫の追加")
with st.sidebar.form("add_form"):
    name = st.text_input("品名")
    amount = st.number_input("数量", min_value=1, step=1)
    expiry_date = st.date_input("賞味期限")
    category = st.selectbox("カテゴリー", ["肉", "野菜", "海鮮", "麺", "その他"])
    submit_button = st.form_submit_button("在庫を追加する")

if submit_button and name:
    # 既存データを読み込んで追加
    existing_data = conn.read(spreadsheet=URL, ttl=0)
    new_row = pd.DataFrame([{
        "name": name,
        "amount": amount,
        "expiry_date": expiry_date.strftime('%Y/%m/%d'),
        "category": category
    }])
    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
    
    # 書き込み実行！
    conn.update(spreadsheet=URL, data=updated_df)
    st.success(f"「{name}」を追加しました！")
    st.balloons()

# --- 表示 ---
df = conn.read(spreadsheet=URL, ttl=0)
st.dataframe(df, use_container_width=True)
