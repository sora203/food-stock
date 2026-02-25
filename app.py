import streamlit as st
import pandas as pd
import streamlit_authenticator as stauth
from datetime import datetime

# --- 1. ログイン設定 (変更なし) ---
credentials = {
    'usernames': {
        'tomoki': {'name': 'Tomoki','password': '65099962'},
        'mom': {'name': 'kumippe','password': '40358253'},
        'friend1': {'name': 'kiyotake','password': '80142208'},
        'friend2': {'name': 'kouha','password': '66831670'},
        'friend3': {'name': 'kake','password': '74156184'},
    }
}
authenticator = stauth.Authenticate(credentials, "fridge_v4", "signature_key", 30)

# --- 2. スプレッドシート読み込み用の関数 ---
# 公開されているシートをCSVとして読み込む一番簡単な方法
def load_data():
    url = st.secrets["spreadsheet_url"].replace("/edit#gid=", "/export?format=csv&gid=")
    try:
        return pd.read_csv(url)
    except:
        # 万が一読み込めない場合は空のデータを作る
        return pd.DataFrame(columns=["name", "amount", "expiry_date", "category", "user"])

# --- 3. 画面表示 ---
authenticator.login()

if st.session_state.get("authentication_status"):
    username = st.session_state.get("username")
    authenticator.logout("ログアウト", "sidebar")
    st.title(f"🍱 {st.session_state.name}の冷蔵庫")

    tab1, tab2 = st.tabs(["📋 在庫リスト", "➕ 食材を登録"])
    df = load_data()

    with tab2:
        with st.form("add_form", clear_on_submit=True):
            f_name = st.text_input("食材名")
            col1, col2 = st.columns(2)
            with col1: amount = st.number_input("個数", min_value=1, value=1)
            with col2: category = st.selectbox("カテゴリ", ["肉", "野菜", "魚", "麺類", "調味料", "その他"])
            expiry = st.date_input("賞味期限")
            
            if st.form_submit_button("保存する"):
                st.info("💡 スプレッドシートを直接開いて、一番下の行に以下を追記してください（※現在、自動書き込みを調整中）")
                st.code(f"{f_name}, {amount}, {expiry}, {category}, {username}")
                # 読み込みは自動なので、手動でシートに書けばリストに反映されます！

    with tab1:
        if not df.empty and "user" in df.columns:
            my_df = df[df["user"] == username]
            for i, row in my_df.iterrows():
                st.write(f"✅ {row['name']} ({row['amount']}個) - 期限: {row['expiry_date']}")
        else:
            st.warning("スプレッドシートにデータがありません。")
