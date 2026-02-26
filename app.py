import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date
import requests

# --- 🎨 カスタムCSS ---
def local_css():
    st.markdown("""
        <style>
        .stApp {
            background-image: url("https://www.toptal.com/designers/subtlepatterns/uploads/wood_pattern.png");
            background-repeat: repeat;
            background-attachment: fixed;
        }
        [data-testid="stAppViewBlockContainer"] {
            background-color: rgba(245, 222, 179, 0.85);
            padding: 3rem;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin-top: 2rem;
        }
        [data-testid="stSidebar"] {
            background-color: #262730 !important;
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] input {
            background-color: #4b4d59 !important;
            color: white !important;
            border: none !important;
        }
        [data-testid="stSidebar"] label p {
            color: #ffffff !important;
            font-weight: bold;
        }
        .stLinkButton { display: flex; justify-content: center; padding: 20px 0; }
        div.stLinkButton > a {
            background-color: #06C755 !important;
            color: white !important;
            border-radius: 50px !important;
            padding: 1.2rem 5rem !important;
            font-size: 1.5rem !important;
            font-weight: bold !important;
            text-decoration: none !important;
        }
        .user-title { font-size: 1.3rem; color: #5d4037; margin-bottom: -5px; }
        .main-title { font-size: 3.5rem; font-weight: 900; color: #3e2723; line-height: 1.1; margin-bottom: 20px; }
        #MainMenu, footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# --- 基本設定 ---
st.set_page_config(page_title="在庫管理メモ", layout="wide")
local_css()
URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# --- 認証系関数 ---
def get_line_login_url():
    client_id = st.secrets["line"]["login_channel_id"]
    redirect_uri = "https://food-memo-app.streamlit.app"
    return (f"https://access.line.me/oauth2/v2.1/authorize?response_type=code&client_id={client_id}"
            f"&redirect_uri={redirect_uri}&state=random_string&scope=profile%20openid")

def get_line_user_info(code):
    token_url = "https://api.line.me/oauth2/v2.1/token"
    data = {
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": "https://food-memo-app.streamlit.app",
        "client_id": st.secrets["line"]["login_channel_id"],
        "client_secret": st.secrets["line"]["login_channel_secret"]
    }
    res = requests.post(token_url, data=data).json()
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

# --- 🔐 ログイン判定 ---
query_params = st.query_params
if "code" not in query_params:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #3e2723; font-size: 3.5rem;'>Stock Manager</h1>", unsafe_allow_html=True)
    st.link_button("LINEでログイン", get_line_login_url())
    st.stop()
else:
    try:
        user_info = get_line_user_info(query_params["code"])
        user_id = user_info.get("sub")
        user_name = user_info.get("displayName") or user_info.get("name") or "User"
    except:
        st.error("ログイン失敗。")
        st.stop()

# --- 🍎 メイン処理 ---
st.markdown(f"<div class='user-title'>{user_name} 様</div><div class='main-title'>在庫リスト</div>", unsafe_allow_html=True)

client = get_gspread_client()
if client:
    sh = client.open_by_url(URL)
    try:
        worksheet = sh.worksheet(user_name)
    except:
        worksheet = sh.add_worksheet(title=user_name, rows="1000", cols="10")
        worksheet.append_row(["品名", "数量", "賞味期限", "保存場所", "種類", "LINE_ID"])
        st.rerun()

    data = worksheet.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame(columns=["品名", "数量", "賞味期限", "保存場所", "種類", "LINE_ID"])

    # --- サイドバー：合算ロジック付き追加 ---
    with st.sidebar:
        st.markdown("### 在庫を追加")
        with st.form("add_form", clear_on_submit=True):
            name = st.text_input("品名")
            amount = st.number_input("数量", min_value=1, value=1)
            expiry = st.date_input("賞味期限", value=date.today()).strftime('%Y/%m/%d')
            cat1 = st.selectbox("保存場所", ["冷蔵", "冷凍", "常温", "その他"])
            cat2 = st.selectbox("種類", ["肉", "野菜", "麺", "飲み物", "その他"])
            
            if st.form_submit_button("リストに追加") and name:
                # 同一条件の検索
                match = (df['品名'] == name) & (df['賞味期限'] == expiry) & (df['保存場所'] == cat1) & (df['種類'] == cat2)
                
                if match.any():
                    # 既存あり：個数を加算
                    idx = df.index[match][0]
                    new_qty = int(df.at[idx, '数量']) + amount
                    df.at[idx, '数量'] = new_qty
                    # スプレッドシート更新（行番号は index + 2）
                    worksheet.update_cell(int(idx) + 2, 2, int(new_qty))
                    st.toast(f"{name}の数量を更新しました")
                else:
                    # 既存なし：新規追加
                    worksheet.append_row([name, int(amount), expiry, cat1, cat2, user_id])
                    st.toast(f"{name}を追加しました")
                st.rerun()

    # --- メインエリア：編集・削除機能 ---
    if not df.empty:
        df_display = df.copy()
        df_display.insert(0, "選択", False)
        
        search_query = st.text_input("検索", placeholder="品名で絞り込み...")
        if search_query:
            mask = df_display.drop(columns=["選択"]).apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)
            df_display = df_display[mask]

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("🔔 期限間近を通知"):
                today = date.today()
                alerts = [f"・{r['品名']} ({r['賞味期限']})" for _, r in df.iterrows() if (datetime.strptime(str(r["賞味期限"]), '%Y/%m/%d').date() - today).days <= 3]
                if alerts:
                    msg = f"\n【期限間近リスト】\n" + "\n".join(alerts); send_individual_line(user_id, msg); st.success("通知済")
        with c2:
            delete_btn = st.button("🗑️ 選択項目を削除", type="primary")

        # 💡 編集可能なデータエディタ（数量のみ編集可に設定）
        edited_df = st.data_editor(
            df_display.drop(columns=["LINE_ID"], errors='ignore'),
            use_container_width=True,
            hide_index=True,
            column_config={
                "選択": st.column_config.CheckboxColumn(),
                "数量": st.column_config.NumberColumn(min_value=0, step=1)
            },
            disabled=["品名", "賞味期限", "保存場所", "種類"], # 数量以外は編集不可
            key="data_editor"
        )

        # 💡 数量が変更された場合の保存処理
        if st.session_state.get("data_editor") and st.session_state["data_editor"]["edited_rows"]:
            for row_idx, changes in st.session_state["data_editor"]["edited_rows"].items():
                if "数量" in changes:
                    # 表示上のインデックスから元のDFのインデックスを特定
                    actual_idx = df_display.index[row_idx]
                    new_val = changes["数量"]
                    worksheet.update_cell(int(actual_idx) + 2, 2, int(new_val))
            st.rerun()

        # 削除処理
        if delete_btn:
            # 修正：インデックスに基づいて正確に削除
            delete_indices = edited_df[edited_df["選択"] == True].index.tolist()
            if delete_indices:
                # 削除後の全データを再構築して上書き（行数ズレ防止）
                remaining_df = df.drop(delete_indices)
                new_data = [["品名", "数量", "賞味期限", "保存場所", "種類", "LINE_ID"]] + remaining_df.values.tolist()
                worksheet.clear()
                worksheet.update('A1', new_data)
                st.rerun()
    else:
        st.info("データがありません")
