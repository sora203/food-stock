import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date
import requests

# --- モード対応とレスポンシブ設定 ---
st.set_page_config(page_title="プロ在庫管理", layout="wide")

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

# --- 💬 LINE通知関数 ---
def send_line_message(message):
    try:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {st.secrets['line']['channel_access_token']}"
        }
        payload = {
            "to": st.secrets['line']['user_id'],
            "messages": [{"type": "text", "text": message}]
        }
        res = requests.post(url, headers=headers, json=payload)
        return res.status_code
    except Exception as e:
        st.error(f"LINE送信失敗: {e}")
        return None

# --- 🔑 パスワード認証 ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 在庫管理ログイン")
    password = st.text_input("アクセスパスワード", type="password")
    if st.button("ログイン"):
        if password == "admin1234": # 救済キー
            st.session_state.show_rescue = True
        elif password:
            st.session_state.authenticated = True
            st.session_state.current_pw = password
            st.rerun()
    
    if st.session_state.get("show_rescue"):
        st.warning("⚠️ 登録済みパスワード一覧")
        client = get_gspread_client()
        if client:
            sh = client.open_by_url(URL)
            all_sheets = [s.title for s in sh.worksheets() if s.title != "admin_log"]
            st.code(all_sheets)
    st.stop()

# --- ログイン後のメイン処理 ---
st.title(f"🍎 {st.session_state.current_pw} のリスト")
col_header1, col_header2 = st.columns([8, 2])
with col_header2:
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
            
            # 管理ログ記録
            try:
                log_sheet = sh.worksheet("admin_log")
            except:
                log_sheet = sh.add_worksheet(title="admin_log", rows="100", cols="2")
                log_sheet.append_row(["作成日時", "使用パスワード"])
            log_sheet.append_row([datetime.now().strftime('%Y/%m/%d %H:%M:%S'), sheet_name])

        # カテゴリー・サイドバー
        STORAGE_CATS = ["冷蔵", "冷凍", "常温", "その他"]
        TYPE_CATS = ["肉", "野菜", "麺", "飲み物", "その他"]
        st.sidebar.title("🛠️ 操作パネル")
        filter_storage = st.sidebar.multiselect("保存場所で絞り込む", STORAGE_CATS)
        filter_type = st.sidebar.multiselect("種類で絞り込む", TYPE_CATS)

        with st.sidebar.form("add_form"):
            st.subheader("➕ 在庫の追加")
            name = st.text_input("品名")
            amount = st.number_input("数量", min_value=1, step=1)
            expiry_date = st.date_input("賞味期限")
            category1 = st.selectbox("保存場所", STORAGE_CATS)
            category2 = st.selectbox("種類", TYPE_CATS)
            if st.form_submit_button("追加"):
                worksheet.append_row([name, int(amount), expiry_date.strftime('%Y/%m/%d'), category1, category2])
                st.success("追加完了！")
                st.rerun()

        # データ表示
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            if filter_storage: df = df[df["保存場所"].isin(filter_storage)]
            if filter_type: df = df[df["種類"].isin(filter_type)]

            # 📢 LINE通知ボタン
            st.subheader("📢 通知")
            if st.button("期限が近い在庫をLINEに送る"):
                today = date.today()
                alerts = []
                for _, row in df.iterrows():
                    try:
                        d = datetime.strptime(row["賞味期限"], '%Y/%m/%d').date()
                        diff = (d - today).days
                        if diff <= 3: alerts.append(f"・{row['品名']} ({row['賞味期限']})")
                    except: continue
                
                if alerts:
                    msg = f"\n【賞味期限アラート】\n" + "\n".join(alerts) + "\n早めに使いましょう！"
                    if send_line_message(msg) == 200: st.success("LINEに通知しました！")
                else:
                    st.info("3日以内の期限切れはありません。")

            # 在庫一覧表示（色分け）
            def color_expiry(val):
                try:
                    diff = (datetime.strptime(val, '%Y/%m/%d').date() - date.today()).days
                    if diff <= 1: return 'background-color: #ff4b4b; color: white'
                    if diff <= 3: return 'background-color: #ffa500; color: black'
                    return 'background-color: #28a745; color: white'
                except: return ''

            df.insert(0, "削除", False)
            edited_df = st.data_editor(
                df.style.applymap(color_expiry, subset=['賞味期限']),
                hide_index=True, use_container_width=True,
                column_config={"削除": st.column_config.CheckboxColumn(required=True)},
                disabled=["品名", "数量", "賞味期限", "保存場所", "種類"]
            )

            if st.button("🗑️ 選択項目を削除", type="primary"):
                idx = edited_df[edited_df["削除"] == True].index.tolist()
                for i in sorted(idx, reverse=True): worksheet.delete_rows(i + 2)
                st.rerun()
        else:
            st.info("データがありません。")

    except Exception as e:
        st.error(f"エラー: {e}")
