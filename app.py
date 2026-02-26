import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="在庫管理アプリ", layout="wide")
st.title("🍎 食品在庫管理システム")

URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# 🔑 鍵の形式をプログラム側で強制的に整える
try:
    raw_key = st.secrets["connections"]["gsheets"]["private_key"]
    # 改行が \n という文字になってしまっている場合に備えて変換
    fixed_key = raw_key.replace("\\n", "\n")
    
    # 接続設定を上書きして作成
    conn = st.connection(
        "gsheets",
        type=GSheetsConnection,
        client_email=st.secrets["connections"]["gsheets"]["client_email"],
        private_key=fixed_key
    )
except Exception as e:
    st.error(f"認証情報の準備に失敗しました: {e}")
    st.stop()

# --- 入力フォーム ---
st.sidebar.header("新しい在庫の追加")
with st.sidebar.form("add_form"):
    name = st.text_input("品名")
    amount = st.number_input("数量", min_value=1, step=1)
    expiry_date = st.date_input("賞味期限")
    category = st.selectbox("カテゴリー", ["冷蔵", "冷凍", "常温", "その他"])
    submit_button = st.form_submit_button("在庫を追加する")

if submit_button and name:
    try:
        existing_data = conn.read(spreadsheet=URL, ttl=0)
        new_row = pd.DataFrame([{
            "name": name,
            "amount": int(amount),
            "expiry_date": expiry_date.strftime('%Y/%m/%d'),
            "category": category
        }])
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        conn.update(spreadsheet=URL, data=updated_df)
        st.success(f"「{name}」を追加しました！")
        st.balloons()
    except Exception as e:
        st.error(f"追加エラーが発生しました: {e}")

# --- 表示 ---
try:
    df = conn.read(spreadsheet=URL, ttl=0)
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error(f"データの読み込みに失敗しました: {e}")
