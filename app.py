import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date
import requests
import urllib.parse

# --- 設定 ---
st.set_page_config(page_title="LINE在庫管理システム", layout="wide")
URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# --- LINEログイン用の関数 ---
def get_line_login_url():
    client_id = st.secrets["line"]["login_channel_id"]
    redirect_uri = "https://food-memo-app.streamlit.app"
    url = (
        f"https://access.line.me/oauth2/v2.1/authorize?"
        f"response_type=code&"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"state=random_string&"
        f"scope=profile%20openid"
    )
    return url

def get_line_user_info(code):
    token_url = "https://api.line.me/oauth2/v2.1/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": "https://food-memo-app.streamlit.app",
        "client_id": st.secrets["line"]["login_channel_id"],
        "client_secret": st.secrets["line"]["login_channel_secret"]
    }
    res = requests.post(token_url, headers=headers, data=data).json()
    id_token = res.get("id_token")
    payload = {"id_token": id_token, "client_id": st.secrets["line"]["login_channel_id"]}
    return requests.post("https://api.line.me/oauth2/v2.1/verify", data=payload).json()

def get_gspread_client():
    try:
        raw_key = st.secrets["connections"]["gsheets"]["private_key"]
        fixed_key = raw_key.replace("\\n", "\n").strip()
        creds = {
            "type": "service_account", "project_id": "my-food-stock-app",
            "private_key": fixed_key, "client_email": st.secrets["connections"]["gsheets"]["client_email"],
            "token_uri": "https://www.googleapis.com/oauth2/v4/token",
        }
        return gspread.service_account_from_dict(creds)
    except: return None

def send_individual_line(to_id, message):
    try:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {st.secrets['line']['channel_access_token']}"}
        payload = {"to": to_id, "messages": [{"type": "text", "text": message}]}
        return requests.post(url, headers=headers, json=payload).status_code
    except: return None

# --- 🔐 ログイン処理 ---
query_params = st.query_params
if "code" not in query_params:
    st.title("🔐 在庫管理ログイン")
    st.link_button("LINEでログイン", get_line_login_url(), type="primary")
    st.stop()
else:
    try:
        user_info = get_line_user_info(query_params["code"])
        user_id = user_info.get("sub")
        user_name = user_info.get("displayName") or user_info.get("name") or "User"
    except:
        st.error("ログイン失敗。再試行してください。")
        st.stop()

# --- 🍎 メイン画面 ---
st.title(f"🍱 {user_name} さんの在庫リスト")

client = get_gspread_client()
if client:
    sh = client.open_by_url(URL)
    try:
        worksheet = sh.worksheet(user_name)
    except:
        worksheet = sh.add_worksheet(title=user_name, rows="1000", cols="10")
        worksheet.append_row(["品名", "数量", "賞味期限", "保存場所", "種類", "LINE_ID"])
        st.rerun()

    # --- サイドバー：追加 ---
    with st.sidebar.form("add_form"):
        st.subheader("➕ 在庫の追加")
        name = st.text_input("品名")
        amount = st.number_input("数量", min_value=1)
        expiry = st.date_input("賞味期限")
        cat1 = st.selectbox("保存場所", ["冷蔵", "冷凍", "常温", "その他"])
        cat2 = st.selectbox("種類", ["肉", "野菜", "麺", "飲み物", "その他"])
        if st.form_submit_button("追加") and name:
            worksheet.append_row([name, int(amount), expiry.strftime('%Y/%m/%d'), cat1, cat2])
            st.success("追加しました！")
            st.rerun()

    # --- メインエリア：検索・表示・削除 ---
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        # 削除用のチェックボックス列を追加（初期値はFalse）
        df.insert(0, "削除", False)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            search_query = st.text_input("🔍 在庫を検索", placeholder="品名や場所で検索...")
        
        # 検索フィルタリング
        df_filtered = df.copy()
        if search_query:
            mask = df_filtered.drop(columns=["削除"]).apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)
            df_filtered = df_filtered[mask]

        # 期限通知ボタン
        if st.button("🔔 期限が近い在庫をLINEに通知"):
            today = date.today()
            alerts = [f"・{r['品名']} ({r['賞味期限']})" for _, r in df.iterrows() if (datetime.strptime(str(r["賞味期限"]), '%Y/%m/%d').date() - today).days <= 3]
            if alerts:
                msg = f"\n【{user_name}さんの期限間近リスト】\n" + "\n".join(alerts) + "\n早めに使いましょう！"
                send_individual_line(user_id, msg); st.success("LINEに通知しました！")
            else: st.info("期限が近いものはありません。")

        # 💡 在庫一覧（編集・選択モード）
        st.write("---")
        edited_df = st.data_editor(
            df_filtered.drop(columns=["LINE_ID"], errors='ignore'),
            use_container_width=True,
            hide_index=True,
            column_config={"削除": st.column_config.CheckboxColumn(help="削除したい項目にチェック")}
        )

        # 🗑️ 削除実行ボタン
        if st.button("🗑️ 選択した在庫を削除する", type="secondary"):
            # チェックが入った行の「品名」を取得（完全一致で削除するため）
            delete_names = edited_df[edited_df["削除"] == True]["品名"].tolist()
            if delete_names:
                # スプレッドシートを更新（逆順に削除しないと行番号がズレるため一工夫）
                # 今回はシンプルに、削除対象以外のデータを上書きする方法をとります
                new_data = [list(data[0].keys())] # ヘッダー
                keep_rows = [r for r in data if r["品名"] not in delete_names]
                for r in keep_rows:
                    new_data.append(list(r.values()))
                
                worksheet.clear()
                worksheet.update('A1', new_data)
                st.warning(f"{len(delete_names)}件の在庫を削除しました。")
                st.rerun()
            else:
                st.toast("削除する項目にチェックを入れてください")
    else:
        st.info("データがありません。")
