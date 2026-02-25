import streamlit as st
from streamlit_gsheets import GSheetsConnection
import streamlit_authenticator as stauth
from datetime import datetime
import pandas as pd

# --- 1. ログイン設定 (以前と同じ) ---
credentials = {
    'usernames': {
        'tomoki': {'name': 'Tomo','password': '65099962'},
        'mom': {'name': 'kumippe','password': '40358253'},
        'friend1': {'name': 'kiyo','password': '80142208'},
        'friend2': {'name': 'kouha','password': '66831670'},
        'friend3': {'name': 'kake','password': '74156184'},
    }
}

authenticator = stauth.Authenticate(credentials, "fridge_v4", "signature_key", 30)

# --- 2. スプレッドシート接続 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. ログイン画面 ---
authenticator.login()

if st.session_state.get("authentication_status"):
    name = st.session_state.get("name")
    username = st.session_state.get("username")
    authenticator.logout("ログアウト", "sidebar")

    st.title(f"🍱 {name}の冷蔵庫")
    tab1, tab2 = st.tabs(["📋 在庫リスト", "➕ 食材を登録"])

    # --- データの読み込み ---
    # スプレッドシートから全データを読み込む
    df = conn.read(ttl=0) # ttl=0で常に最新を取得

    with tab2:
        st.subheader("新しい食材を追加")
        with st.form("food_form", clear_on_submit=True):
            f_name = st.text_input("食材名")
            col1, col2 = st.columns(2)
            with col1: amount = st.number_input("個数", min_value=1, value=1)
            with col2: category = st.selectbox("カテゴリ", ["肉", "野菜", "魚", "麺類", "調味料", "その他"])
            expiry = st.date_input("賞味期限")
            
            if st.form_submit_button("保存する"):
                if f_name:
                    # 新しい行を作成
                    new_data = pd.DataFrame([{
                        "name": f_name,
                        "amount": amount,
                        "expiry_date": str(expiry),
                        "category": category,
                        "user": username
                    }])
                    # 既存のデータと合体させて更新
                    updated_df = pd.concat([df, new_data], ignore_index=True)
                    #conn.update(data=updated_df)
                    st.warning("現在、書き込み機能をメンテナンス中です")
                    st.success(f"「{f_name}」を登録したよ！")
                    st.rerun()

    with tab1:
        # 自分のデータだけを抽出
        if not df.empty and "user" in df.columns:
            my_df = df[df["user"] == username].sort_values("expiry_date")
            
            if my_df.empty:
                st.info("在庫はありません。")
            else:
                today = datetime.now().date()
                for index, row in my_df.iterrows():
                    exp_date = datetime.strptime(row["expiry_date"], '%Y-%m-%d').date()
                    diff = (exp_date - today).days
                    color = "red" if diff <= 1 else "orange" if diff <= 3 else "#4CAF50"
                    
                    with st.container():
                        st.markdown(f"""
                        <div style="padding:10px; border-radius:10px; border-left:5px solid {color}; background-color:#f0f2f6; margin-bottom:10px; color:black;">
                            <b>{row['name']}</b> ({row['category']}) - {row['amount']}個<br>
                            <small>期限: {row['expiry_date']} ({diff}日後)</small>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button(f"🍴 食べた", key=f"del_{index}"):
                            # その行を消して更新
                            df = df.drop(index)
                            conn.update(data=df)
                            st.rerun()
        else:
            st.info("まだデータがありません。")

elif st.session_state.get("authentication_status") is False:
    st.error("ユーザー名またはパスワードが違います")
