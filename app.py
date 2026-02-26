import streamlit as st
import gspread
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="個別在庫管理アプリ", layout="wide")

# --- 🔑 パスワード認証 & シート選択機能 ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 在庫管理ログイン")
    password = st.text_input("アクセスパスワードを入力してください", type="password")
    if st.button("ログイン"):
        if password: # 何か入力されていればOKとする設定
            st.session_state.authenticated = True
            st.session_state.current_pw = password
            st.rerun()
        else:
            st.error("パスワードを入力してください")
    st.stop()

# --- ログイン後の処理 ---
st.title(f"🍎 {st.session_state.current_pw} の在庫リスト")
if st.button("ログアウト"):
    st.session_state.authenticated = False
    st.rerun()

URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

def get_gspread_client():
    try:
        raw_key = st.secrets["connections"]["gsheets"]["private_key"]
        fixed_key = raw_key.replace("\\n", "\n").strip()
        creds = {
            "type": "service_account",
            "project_id": "my-food-stock-app",
            "private_key": fixed_key,
            "client_email": st.secrets["connections"]["gsheets"]["client_email"],
            "token_uri": "https://www.googleapis.com/oauth2/v4/token",
        }
        return gspread.service_account_from_dict(creds)
    except Exception as e:
        st.error(f"認証エラー: {e}")
        return None

client = get_gspread_client()

if client:
    try:
        sh = client.open_by_url(URL)
        
        # 💡 パスワードと同じ名前のシートを開く。なければ新しく作る。
        sheet_name = st.session_state.current_pw
        try:
            worksheet = sh.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # シートが存在しない場合、ヘッダー付きで新規作成
            worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="20")
            worksheet.append_row(["name", "amount", "expiry_date", "category"])
            st.info(f"新しいリスト「{sheet_name}」を作成しました。")

        # --- サイドバー：在庫追加 ---
        st.sidebar.header("在庫の追加")
        with st.sidebar.form("add_form"):
            name = st.text_input("品名")
            amount = st.number_input("数量", min_value=1, step=1)
            expiry_date = st.date_input("賞味期限")
            category = st.selectbox("カテゴリー", ["冷蔵", "冷凍", "常温", "その他"])
            submit_button = st.form_submit_button("追加")

        if submit_button and name:
            new_row = [name, int(amount), expiry_date.strftime('%Y/%m/%d'), category]
            worksheet.append_row(new_row)
            st.success("追加完了！")
            st.balloons()

        # --- メイン画面：一覧表示 ---
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("まだデータがありません。")

    except Exception as e:
        st.error(f"操作エラー: {e}")
