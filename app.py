import streamlit as st
import sqlite3
from datetime import datetime

# --- app.py の上部に追加 ---

st.markdown("""
    <style>
    /* 1. ライトモードとダークモードで共通の基本設定 */
    .stApp {
        border-radius: 0px;
    }

    /* 2. スマホ風カードのデザイン */
    .food-card {
        padding: 1.5rem;
        border-radius: 1rem;
        margin-bottom: 1rem;
        border-left: 6px solid #4CAF50;
        /* ライト/ダーク両方で違和感のない影 */
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    /* 3. モードによって色を自動で変える魔法のコード */
    @media (prefers-color-scheme: light) {
        .food-card {
            background-color: #FFFFFF;
            color: #31333F;
        }
        .stApp {
            background-color: #F8F9FA;
        }
    }

    @media (prefers-color-scheme: dark) {
        .food-card {
            background-color: #262730;
            color: #FAFAFA;
        }
        .stApp {
            background-color: #0E1117;
        }
    }

    /* ボタンはどちらのモードでも目立つ色に固定 */
    div.stButton > button {
        background-color: #4CAF50;
        color: white;
        border-radius: 2rem;
        font-weight: bold;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('food_stock_web.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS foods 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    name TEXT, amount INTEGER, expiry_date TEXT, category TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- タイトルとスマホ用設定 ---
st.set_page_config(page_title="食材管理アプリ", page_icon="🍱")

# カスタムCSSでスマホっぽくデザインを整える
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 10px; }
    .food-card {
        padding: 15px;
        border-radius: 10px;
        background-color: white;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🍱 食材管理")

# --- メインタブ（スマホの画面切り替え） ---
tab1, tab2 = st.tabs(["📋 在庫リスト", "➕ 食材を登録"])

# ---------------------------------------------------------
# 【登録画面】
# ---------------------------------------------------------
with tab2:
    st.subheader("新しい食材を追加")
    with st.form("register_form", clear_on_submit=True):
        name = st.text_input("食材名", placeholder="例: 豚バラ肉")
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("個数", min_value=1, value=1)
        with col2:
            category = st.selectbox("カテゴリ", ["肉", "野菜", "魚", "麺類", "調味料", "その他"])
        
        expiry = st.date_input("賞味期限")
        submit = st.form_submit_button("この内容で保存する")

        if submit and name:
            conn = sqlite3.connect('food_stock_web.db')
            cur = conn.cursor()
            cur.execute("INSERT INTO foods (name, amount, expiry_date, category) VALUES (?, ?, ?, ?)",
                        (name, amount, str(expiry), category))
            conn.commit()
            conn.close()
            st.success(f"「{name}」を登録したよ！")
            st.balloons() # お祝いのエフェクト

# ---------------------------------------------------------
# 【一覧画面】
# ---------------------------------------------------------
with tab1:
    # 1. 通知バナー機能
    conn = sqlite3.connect('food_stock_web.db')
    cur = conn.cursor()
    cur.execute("SELECT name, expiry_date FROM foods")
    rows_all = cur.fetchall()
    
    today = datetime.now().date()
    urgent = []
    warning = []
    for r_name, r_exp in rows_all:
        diff = (datetime.strptime(r_exp, '%Y-%m-%d').date() - today).days
        if diff <= 1: urgent.append(r_name)
        elif diff <= 3: warning.append(r_name)

    if urgent:
        st.error(f"⚠️ **期限直近！すぐ食べて！**\n\n{', '.join(urgent)}")
    elif warning:
        st.warning(f"🕒 **あと3日以内:** {', '.join(warning)}")

    # 2. 検索・絞り込み
    st.subheader("在庫をチェック")
    search_col, filter_col = st.columns([2, 1])
    with search_col:
        search_query = st.text_input("", placeholder="🔍 食材名で検索...", label_visibility="collapsed")
    with filter_col:
        filter_cat = st.selectbox("", ["すべて", "肉", "野菜", "魚", "麺類", "調味料", "その他"], label_visibility="collapsed")

    # 3. リスト表示 (SQL実行)
    query = "SELECT id, name, amount, expiry_date, category FROM foods WHERE name LIKE ?"
    params = [f"%{search_query}%"]
    if filter_cat != "すべて":
        query += " AND category = ?"
        params.append(filter_cat)
    query += " ORDER BY expiry_date ASC"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    # 4. カード形式で表示
    if not rows:
        st.info("食材が見つかりません。")
    else:
        for fid, name, amt, exp, cat in rows:
            exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
            diff = (exp_date - today).days
            
            # 期限による色分けバッジ
            if diff <= 1: color = "red"
            elif diff <= 3: color = "orange"
            else: color = "gray"
            
            # スマホ風カード
            with st.container():
                c1, c2, c3 = st.columns([1, 4, 1])
                with c1:
                    st.write(f"### ●") # 色分けの点（実際はCSSでもっと綺麗にできます）
                with c2:
                    st.markdown(f"**{name}** ({cat})")
                    st.caption(f"個数: {amt}個 | 期限: {exp}")
                with c3:
                    if st.button("🍴", key=f"del_{fid}"):
                        conn = sqlite3.connect('food_stock_web.db')
                        cur = conn.cursor()
                        cur.execute("DELETE FROM foods WHERE id = ?", (fid,))
                        conn.commit()
                        conn.close()
                        st.rerun()