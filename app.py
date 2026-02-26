import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date

# --- 5 & 6. モード対応とレスポンシブ設定 ---
st.set_page_config(page_title="プロ在庫管理", layout="wide")

# --- 🔑 パスワード認証 ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- 🔑 パスワード認証部分の修正案 ---
if not st.session_state.authenticated:
    st.title("🔐 在庫管理ログイン")
    password = st.text_input("アクセスパスワード", type="password")
    
    col_login, col_help = st.columns(2)
    
    with col_login:
        if st.button("ログイン"):
            if password == "ADMIN_MASTER_KEY": # 👈 あなただけが知っている救済パスワード
                st.session_state.show_rescue = True
            elif password:
                st.session_state.authenticated = True
                st.session_state.current_pw = password
                st.rerun()
    
    # 🆘 救済画面の表示
    if st.session_state.get("show_rescue"):
        st.warning("⚠️ 救済モード：現在作成されているリスト（パスワード）一覧")
        client = get_gspread_client()
        if client:
            sh = client.open_by_url(URL)
            all_sheets = [s.title for s in sh.worksheets()]
            st.write(all_sheets) # シート名（＝パスワード）をズラッと表示
            if st.button("閉じる"):
                st.session_state.show_rescue = False
                st.rerun()
    st.stop()

if not st.session_state.authenticated:
    st.title("🔐 在庫管理ログイン")
    password = st.text_input("アクセスパスワード", type="password")
    if st.button("ログイン"):
        if password:
            st.session_state.authenticated = True
            st.session_state.current_pw = password
            st.rerun()
    st.stop()

# --- Google接続設定 ---
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
        sheet_name = st.session_state.current_pw
        try:
            worksheet = sh.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="20")
            # 4. カテゴリー2(種類)を追加したヘッダー
            worksheet.append_row(["品名", "数量", "賞味期限", "保存場所", "種類"])
            st.info(f"新規作成しました。")

        # --- 4. カテゴリー設定 ---
        STORAGE_CATS = ["冷蔵", "冷凍", "常温", "その他"]
        TYPE_CATS = ["肉", "野菜", "麺", "飲み物", "その他"]

        # --- 3 & 4. サイドバー：追加と絞り込み ---
        st.sidebar.title("🛠️ 操作パネル")
        
        # 3. 絞り込み検索機能
        st.sidebar.subheader("🔍 絞り込み")
        filter_storage = st.sidebar.multiselect("保存場所で絞り込む", STORAGE_CATS)
        filter_type = st.sidebar.multiselect("種類で絞り込む", TYPE_CATS)

        with st.sidebar.form("add_form"):
            st.subheader("➕ 在庫の追加")
            name = st.text_input("品名")
            amount = st.number_input("数量", min_value=1, step=1)
            expiry_date = st.date_input("賞味期限")
            category1 = st.selectbox("保存場所", STORAGE_CATS)
            category2 = st.selectbox("種類", TYPE_CATS)
            submit_button = st.form_submit_button("追加")

        if submit_button and name:
            new_row = [name, int(amount), expiry_date.strftime('%Y/%m/%d'), category1, category2]
            worksheet.append_row(new_row)
            st.success("追加しました！")
            st.rerun()

        # --- メイン画面 ---
        st.title(f"🍎 {st.session_state.current_pw} のリスト")
        
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            
            # 3. 絞り込み実行
            if filter_storage:
                df = df[df["保存場所"].isin(filter_storage)]
            if filter_type:
                df = df[df["種類"].isin(filter_type)]

            # 1. アラート機能のロジック
            def color_expiry(val):
                try:
                    expiry = datetime.strptime(val, '%Y/%m/%d').date()
                    today = date.today()
                    diff = (expiry - today).days
                    if diff <= 1: return 'background-color: #ff4b4b; color: white' # 赤（当日・1日前）
                    if diff <= 3: return 'background-color: #ffa500; color: black' # オレンジ（3日前）
                    return 'background-color: #28a745; color: white'             # 緑（それ以外）
                except:
                    return ''

            # 2. 削除機能用チェックボックス
            df.insert(0, "削除選択", False)
            
            # 1. 色分けを適用して表示
            st.subheader("📦 在庫一覧")
            edited_df = st.data_editor(
                df.style.applymap(color_expiry, subset=['賞味期限']),
                hide_index=True,
                use_container_width=True,
                column_config={"削除選択": st.column_config.CheckboxColumn(required=True)},
                disabled=["品名", "数量", "賞味期限", "保存場所", "種類"]
            )

            # 2. 削除実行
            if st.button("🗑️ 選択した項目を削除", type="primary"):
                selected_indices = edited_df[edited_df["削除選択"] == True].index.tolist()
                if selected_indices:
                    # 実際の削除（後ろの行から）
                    all_data_len = len(data)
                    for index in sorted(selected_indices, reverse=True):
                        worksheet.delete_rows(index + 2)
                    st.success("削除完了！")
                    st.rerun()

        else:
            st.info("データがありません。")

    except Exception as e:
        st.error(f"エラー: {e}")

