import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="在庫管理アプリ", layout="wide")
st.title("🍎 食品在庫管理システム")

URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# 🔑 認証情報を整理して接続する
try:
    # Secretsから生データを取得
    raw_secrets = st.secrets["connections"]["gsheets"]
    
    # 鍵の中身をクリーニング（改行トラブル対策）
    fixed_key = raw_secrets["private_key"].replace("\\n", "\n")
    
    # ライブラリが受け付ける「正式な形式」の辞書を作成
    credentials_info = {
        "type": "service_account",
        "project_id": "my-food-stock-app",
        "private_key": fixed_key,
        "client_email": raw_secrets["client_email"],
        "token_uri": "https://oauth2.google.com/token",
    }
    
    # 💡 修正：辞書をそのまま渡すのではなく、ライブラリの内部仕様に合わせて接続
    conn = st.connection("gsheets", type=GSheetsConnection, credentials=credentials_info)

except Exception as e:
    st.error(f"接続の準備に失敗しました: {e}")
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
