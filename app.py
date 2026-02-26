import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date
import requests

# --- 🎨 カスタムCSS（デザイン維持） ---
def local_css():
    st.markdown("""
        <style>
        .stApp { background-image: url("https://www.toptal.com/designers/subtlepatterns/uploads/wood_pattern.png"); background-repeat: repeat; background-attachment: fixed; }
        [data-testid="stAppViewBlockContainer"] { background-color: rgba(245, 222, 179, 0.7); padding: 3rem; border-radius: 15px; margin-top: 2rem; }
        [data-testid="stSidebar"] { background-color: #262730 !important; }
        [data-testid="stSidebar"] input, [data-testid="stSidebar"] div[data-baseweb="select"] > div, [data-testid="stSidebar"] .stNumberInput div, [data-testid="stSidebar"] .stDateInput div {
            background-color: #3e404b !important; color: #ffffff !important; border: none !important; box-shadow: none !important;
        }
        [data-testid="stSidebar"] label p { color: #ffffff !important; font-weight: bold; }
        .stLinkButton { display: flex; justify-content: center; padding: 20px 0; }
        div.stLinkButton > a { background-color: #06C755 !important; color: white !important; border-radius: 50px !important; padding: 1.2rem 5rem !important; font-size: 1.5rem !important; font-weight: bold !important; text-decoration: none !important; }
        .user-title { font-size: 1.2rem; color: #5d4037; margin-bottom: -5px; }
        .main-title { font-size: 3.5rem; font-weight: 900; color: #3e2723; line-height: 1.1; margin-bottom: 20px; }
        header {visibility: hidden;} #MainMenu, footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# --- 設定 ---
st.set_page_config(page_title="在庫管理メモ", layout="wide")
local_css()
URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"
SHEET_NAME = "在庫データ"

# --- LINE連携関数 ---
def get_line_login_url():
    client_id = st.secrets["line"]["login_channel_id"]
    redirect_uri = "https://food-memo-app.streamlit.app"
    return (f"https://access.line.me/oauth2/v2.1/authorize?response_type=code&client_id={client_id}"
            f"&redirect_uri={redirect_uri}&state=random_string&scope=profile%20openid")

def get_line_user_info(code):
    token_url = "https://api.line.me/oauth2/v2.1/token"
    data = {"grant_type": "authorization_code", "code": code, "redirect_uri": "https://food-memo-app.streamlit.app",
            "client_id": st.secrets["line"]["login_channel_id"], "client_secret": st.secrets["line"]["login_channel_secret"]}
    res = requests.post(token_url, data=data).json()
    id_token = res.get("id_token")
    payload = {"id_token": id_token, "client_id": st.secrets["line"]["login_channel_id"]}
    return requests.post("https://api.line.me/oauth2/v2.1/verify", data=payload).json()

@st.cache_resource(ttl=600)
def get_gspread_client():
    try:
        raw_key = st.secrets["connections"]["gsheets"]["private_key"].replace("\\n", "\n").strip()
        creds = {"type": "service_account", "project_id": "my-food-stock-app", "private_key": raw_key,
                 "client_email": st.secrets["connections"]["gsheets"]["client_email"], "token_uri": "https://www.googleapis.com/oauth2/v4/token"}
        return gspread.service_account_from_dict(creds)
    except: return None

def send_individual_line(to_id, message):
    try:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {st.secrets['line']['channel_access_token']}"}
        payload = {"to": to_id, "messages": [{"type": "text", "text": message}]}
        requests.post(url, headers=headers, json=payload)
    except: pass

# --- 🔐 ログイン管理 ---
if "user_id" not in st.session_state:
    query_params = st.query_params
    if "code" not in query_params:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #3e2723; font-size: 3.5rem;'>Stock Manager</h1>", unsafe_allow_html=True)
        st.link_button("LINEでログイン", get_line_login_url())
        st.stop()
    else:
        try:
            user_info = get_line_user_info(query_params["code"])
            st.session_state.user_id = user_info.get("sub")
            st.session_state.user_name = user_info.get("displayName") or user_info.get("name") or "User"
        except:
            st.error("ログイン情報が取得できません。再ログインしてください。")
            st.stop()

user_id = st.session_state.user_id
user_name = st.session_state.user_name

# --- 🍎 メイン処理 ---
st.markdown(f"<div class='user-title'>{user_name} 様</div><div class='main-title'>在庫リスト</div>", unsafe_allow_html=True)

client = get_gspread_client()
if client:
    sh = client.open_by_url(URL)
    try:
        worksheet = sh.worksheet(SHEET_NAME)
    except:
        worksheet = sh.add_worksheet(title=SHEET_NAME, rows="5000", cols="10")
        worksheet.append_row(["品名", "数量", "賞味期限", "保存場所", "種類", "LINE_ID"])
        st.rerun()

    all_records = worksheet.get_all_records()
    all_df = pd.DataFrame(all_records) if all_records else pd.DataFrame(columns=["品名", "数量", "賞味期限", "保存場所", "種類", "LINE_ID"])
    
    # LINE IDを文字列として比較して抽出
    df = all_df[all_df["LINE_ID"].astype(str) == str(user_id)].copy()

    with st.sidebar:
        st.markdown("### 在庫を追加")
        with st.form("add_form", clear_on_submit=True):
            n = st.text_input("品名")
            a = st.number_input("数量", min_value=1, value=1)
            e = st.date_input("賞味期限", value=date.today()).strftime('%Y/%m/%d')
            c1 = st.selectbox("保存場所", ["冷蔵", "冷凍", "常温", "その他"])
            c2 = st.selectbox("種類", ["肉", "野菜", "麺", "飲み物", "その他"])
            if st.form_submit_button("リストに追加") and n:
                match = (all_df['品名'] == n) & (all_df['賞味期限'] == e) & (all_df['保存場所'] == c1) & (all_df['種類'] == c2) & (all_df['LINE_ID'].astype(str) == str(user_id))
                if match.any():
                    idx = all_df.index[match][0]
                    new_q = int(all_df.at[idx, '数量']) + a
                    worksheet.update_cell(int(idx) + 2, 2, int(new_q))
                else:
                    # 💡 LINE_IDを確実に含めて追加
                    worksheet.append_row([n, int(a), e, c1, c2, str(user_id)])
                st.rerun()

    if not df.empty:
        df_disp = df.copy()
        df_disp.insert(0, "選択", False)
        df_disp = df_disp[["選択", "品名", "数量", "賞味期限", "保存場所", "種類"]]

        search = st.text_input("検索")
        if search:
            df_disp = df_disp[df_disp.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔔 期限通知"):
                today = date.today()
                alerts = [f"・{r['品名']} ({r['賞味期限']})" for _, r in df.iterrows() if (datetime.strptime(str(r["賞味期限"]), '%Y/%m/%d').date() - today).days <= 3]
                if alerts: send_individual_line(user_id, "\n".join(alerts)); st.success("通知済")
        with col2:
            del_btn = st.button("🗑️ 選択項目を削除", type="primary")

        edited_df = st.data_editor(df_disp, use_container_width=True, hide_index=True, key="ed",
                                   column_config={"選択": st.column_config.CheckboxColumn(), "数量": st.column_config.NumberColumn(min_value=0)},
                                   disabled=["品名", "賞味期限", "保存場所", "種類"])

        if st.session_state.ed["edited_rows"]:
            for row_idx, changes in st.session_state.ed["edited_rows"].items():
                if "数量" in changes:
                    actual_idx = df_disp.index[row_idx]
                    worksheet.update_cell(int(actual_idx) + 2, 2, int(changes["数量"]))
            st.rerun()

        if del_btn:
            del_indices = edited_df[edited_df["選択"] == True].index.tolist()
            if del_indices:
                new_all_df = all_df.drop(del_indices)
                worksheet.clear()
                worksheet.update('A1', [all_df.columns.tolist()] + new_all_df.values.tolist())
                st.rerun()
    else:
        st.info("表示できる在庫データがありません。サイドバーから追加してください。")
