import streamlit as st
import gspread
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="在庫管理アプリ", layout="wide")
st.title("🍎 食品在庫管理システム")

URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# 🔑 手動でGoogleにログインする関数
def get_gspread_client():
    try:
        # Secretsから情報を直接取り出す
        raw_key = st.secrets["connections"]["gsheets"]["private_key"]
        # 改行トラブルを完全に除去
        fixed_key = raw_key.replace("\\n", "\n").strip()
        
        creds = {
            "type": "service_account",
            "project_id": "my-food-stock-app",
            "private_key": fixed_key,
            "client_email": st.secrets["connections"]["gsheets"]["client_email"],
            "token_uri": "https://www.googleapis.com/oauth2/v4/token",
        }
        # st.connectionを通さず、gspreadで直接ログイン
        return gspread.service_account_from_dict(creds)
    except Exception as e:
        st.error(f"Googleへのログインに失敗しました: {e}")
        return None

# クライアントの取得
client = get_gspread_client()

if client:
    try:
        sh = client.open_by_url(URL)
        worksheet = sh.get_worksheet(0)
        
        # --- 入力フォーム ---
        st.sidebar.header("新しい在庫の追加")
        with st.sidebar.form("add_form"):
            name = st.text_input("品名")
            amount = st.number_input("数量", min_value=1, step=1)
            expiry_date = st.date_input("賞味期限")
            category = st.selectbox("カテゴリー", ["冷蔵", "冷凍", "常温", "その他"])
            submit_button = st.form_submit_button("在庫を追加する")

        if submit_button and name:
            # データの追加
            new_row = [name, int(amount), expiry_date.strftime('%Y/%m/%d'), category]
            worksheet.append_row(new_row)
            st.success(f"「{name}」を追加しました！")
            st.balloons()

        # --- 一覧表示 ---
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("データがまだありません。サイドバーから追加してください。")

    except Exception as e:
        st.error(f"スプレッドシートの操作エラー: {e}")

