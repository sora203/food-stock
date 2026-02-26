import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="在庫管理アプリ", layout="wide")
st.title("🍎 食品在庫管理システム")

URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# Secretsから自動的に認証情報を読み込む（一番安全な方法）
conn = st.connection("gsheets", type=GSheetsConnection)

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
        # データの読み込み
        existing_data = conn.read(spreadsheet=URL, ttl=0)
        
        # 新しいデータの作成
        new_row = pd.DataFrame([{
            "name": name, 
            "amount": int(amount), 
            "expiry_date": expiry_date.strftime('%Y/%m/%d'), 
            "category": category
        }])
        
        # データの結合
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        
        # スプレッドシートの更新（ここでSecretsの認証が使われます）
        conn.update(spreadsheet=URL, data=updated_df)
        
        st.success(f"「{name}」を追加しました！")
        st.balloons()
    except Exception as e:
        st.error(f"追加エラーが発生しました: {e}")

# --- 一覧表示 ---
df = conn.read(spreadsheet=URL, ttl=0)
st.dataframe(df, use_container_width=True)
