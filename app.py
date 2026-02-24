import streamlit as st
import sqlite3
from datetime import datetime
import streamlit_authenticator as stauth

# --- 1. ログイン設定 ---
credentials = {
    'usernames': {
        'tomoki': {'name': 'tomo','password': '65099962'},
        'mom': {'name': 'kumippe','password': '40358253'},
        'friend1': {'name': 'kiyo','password': '80142208'},
        'friend2': {'name': 'kouha','password': '66831670'},
        'friend3': {'name': 'kake','password': '74156184'},
    }
}

# Cookie名を v4 に変更して強制リセット
authenticator = stauth.Authenticate(
    credentials,
    "fridge_v4", 
    "signature_key_unique_v4",
    30
)

# --- 2. データベース設定 ---
def init_db():
    conn = sqlite3.connect('food_stock_web.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS foods 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    name TEXT, amount INTEGER, expiry_date TEXT, category TEXT, user TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 3. 画面表示の制御 ---
# ログインフォームをまず呼ぶ（これがセッション状態を更新してくれる）
authenticator.login()

if st.session_state.get("authentication_status"):
    # ログイン成功時
    name = st.session_state.get("name")
    username = st.session_state.get("username")
    
    authenticator.logout("ログアウト", "sidebar")

    st.title(f"🍱 {name}の冷蔵庫")
    
    tab1, tab2 = st.tabs(["📋 在庫リスト", "➕ 食材を登録"])

    with tab2:
        st.subheader("新しい食材を追加")
        with st.form("food_form"):
            f_name = st.text_input("食材名")
            col1, col2 = st.columns(2)
            with col1: amount = st.number_input("個数", min_value=1, value=1)
            with col2: category = st.selectbox("カテゴリ", ["肉", "野菜", "魚", "麺類", "調味料", "その他"])
            expiry = st.date_input("賞味期限")
            submit = st.form_submit_button("保存する")

            if submit:
                if f_name:
                    conn = sqlite3.connect('food_stock_web.db')
                    cur = conn.cursor()
                    cur.execute("INSERT INTO foods (name, amount, expiry_date, category, user) VALUES (?, ?, ?, ?, ?)",
                                (f_name, amount, str(expiry), category, username))
                    conn.commit()
                    conn.close()
                    st.success(f"「{f_name}」を登録したよ！")
                    # rerunを使わずに、メッセージだけ出すのが一番安全です
                else:
                    st.warning("食材名を入力してね！")

    with tab1:
        today = datetime.now().date()
        conn = sqlite3.connect('food_stock_web.db')
        cur = conn.cursor()
        cur.execute("SELECT id, name, amount, expiry_date, category FROM foods WHERE user = ? ORDER BY expiry_date ASC", (username,))
        rows = cur.fetchall()
        conn.close()

        if not rows:
            st.info("在庫はありません。")
        else:
            for fid, f_n, amt, exp, cat in rows:
                exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                diff = (exp_date - today).days
                color = "red" if diff <= 1 else "orange" if diff <= 3 else "#4CAF50"
                
                with st.container():
                    st.write(f"**{f_n}** ({cat}) - {amt}個")
                    st.caption(f"期限: {exp} ({diff}日後)")
                    if st.button(f"🍴 食べた ({f_n})", key=f"del_{fid}"):
                        conn = sqlite3.connect('food_stock_web.db')
                        cur = conn.cursor()
                        cur.execute("DELETE FROM foods WHERE id = ?", (fid,))
                        conn.commit()
                        conn.close()
                        st.rerun()

elif st.session_state.get("authentication_status") is False:
    st.error("ユーザー名またはパスワードが違います")
else:
    # authentication_status is None (未入力)
    st.title("🍱 冷蔵庫ログイン")
    st.info("IDとパスワードを入力してください")
