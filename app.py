import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="在庫管理アプリ", layout="wide")
st.title("🍎 食品在庫管理システム")

# 接続設定
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# --- 入力フォーム ---
st.sidebar.header("新しい在庫の追加")
with st.sidebar.form("add_form"):
    name = st.text_input("品名")
    amount = st.number_input("数量", min_value=1, step=1)
    expiry_date = st.date_input("賞味期限")
    category = st.selectbox("カテゴリー", ["冷蔵", "冷凍", "常温", "その他"])
    submit_button = st.form_submit_button("在庫を追加する")

# --- 追加ボタンが押された時の処理 ---
if submit_button:
    if name:
        # 現在のデータを読み込む
        existing_data = conn.read(spreadsheet=url, usecols=[0,1,2,3], ttl=0)
        
        # 新しい行を作成
        new_row = pd.DataFrame([{
            "name": name,
            "amount": amount,
            "expiry_date": expiry_date.strftime('%Y/%m/%d'),
            "category": category
        }])
        
        # 既存データと結合
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        
        # スプレッドシートを更新
        conn.update(spreadsheet=url, data=updated_df)
        
        st.success(f"「{name}」を追加しました！")
        st.balloons()
    else:
        st.error("品名を入力してください。")

# --- 在庫一覧の表示 ---
st.subheader("現在の在庫一覧")
df = conn.read(spreadsheet=url, ttl=0)
st.dataframe(df, use_container_width=True)
