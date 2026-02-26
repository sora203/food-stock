import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date

# --- モード対応とレスポンシブ設定 ---
st.set_page_config(page_title="プロ在庫管理", layout="wide")

# --- Google接続設定 (救済モードでも使うため先頭に配置) ---
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

# --- 🔑 パスワード認証 & 救済機能 ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 在庫管理ログイン")
    password = st.text_input("アクセスパスワード", type="password")
    
    col_login, col_help = st.columns(2)
    
    with col_login:
        if st.button("ログイン"):
            # 💡 ADMIN_MASTER_KEY を自分の好きな秘密の言葉に変えてください！
            if password == "masterpass": 
                st.session_state.show_rescue = True
            elif password:
                st.session_state.authenticated = True
                st.session_state.current_pw = password
                st.rerun()
            else:
                st.error("パスワードを入力してください")
    
    # 🆘 救済画面（マスターパスワードが一致した時だけ表示）
    if st.session_state.get("show_rescue"):
        st.warning("⚠️ 救済モード：現在作成されているリスト（パスワード）一覧")
        client = get_gspread_client()
        if client:
            sh = client.open_by_url(URL)
            all_sheets = [s.title for s in sh.worksheets()]
            st.write("登録済みのパスワード一覧:")
            st.code(all_sheets) # コピーしやすいようにコード形式で表示
            if st.button("閉じる"):
                st.session_state.show_rescue = False
                st.rerun()
    st.stop() # ログインしていない場合はここで止める

# --- ログイン後のメイン処理 ---
st.title(f"🍎 {st.session_state.current_pw} のリスト")
if st.button("ログアウト"):
    st.session_state.authenticated = False
    st.rerun()

client = get_gspread_client()

if client:
    try:
        sh = client.open_by_url(URL)
        sheet_name = st.session_state.current_pw
        try:
            worksheet = sh.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="20")
            worksheet.append_row(["品名", "数量", "賞味期限", "保存場所", "種類"])
            st.info(f"新規作成しました。")

        # カテゴリー設定
        STORAGE_CATS = ["冷蔵", "冷凍", "常温", "その他"]
        TYPE_CATS = ["肉", "野菜", "麺", "飲み物", "その他"]

        # サイドバー：操作パネル
        st.sidebar.title("🛠️ 操作パネル")
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
            st.success("追加完了！")
            st.rerun()

        # データ表示
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            
            if filter_storage:
                df = df[df["保存場所"].isin(filter_storage)]
            if filter_type:
                df = df[df["種類"].isin(filter_type)]

            def color_expiry(val):
                try:
                    expiry = datetime.strptime(val, '%Y/%m/%d').date()
                    today = date.today()
                    diff = (expiry - today).days
                    if diff <= 1: return 'background-color: #ff4b4b; color: white'
                    if diff <= 3: return 'background-color: #ffa500; color: black'
                    return 'background-color: #28a745; color: white'
                except:
                    return ''

            df.insert(0, "削除選択", False)
            st.subheader("📦 在庫一覧")
            edited_df = st.data_editor(
                df.style.applymap(color_expiry, subset=['賞味期限']),
                hide_index=True,
                use_container_width=True,
                column_config={"削除選択": st.column_config.CheckboxColumn(required=True)},
                disabled=["品名", "数量", "賞味期限", "保存場所", "種類"]
            )

            if st.button("🗑️ 選択した項目を削除", type="primary"):
                selected_indices = edited_df[edited_df["削除選択"] == True].index.tolist()
                if selected_indices:
                    for index in sorted(selected_indices, reverse=True):
                        worksheet.delete_rows(index + 2)
                    st.success("削除しました！")
                    st.rerun()
        else:
            st.info("データがありません。")

    except Exception as e:
        st.error(f"エラー: {e}")

