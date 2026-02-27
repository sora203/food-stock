import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date
import requests
import time  # 💡 リトライ待ち時間のために追加

# --- 🎨 デザイン ---
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
        header { background-color: rgba(0,0,0,0) !important; }
        [data-testid="stHeader"] button { color: white !important; fill: white !important; }
        .user-title { font-size: 1.2rem; color: #5d4037; margin-bottom: -5px; }
        .main-title { font-size: 3.5rem; font-weight: 900; color: #3e2723; line-height: 1.1; margin-bottom: 20px; }
        #MainMenu, footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

st.set_page_config(page_title="在庫管理メモ", layout="wide")
local_css()

# --- 設定 ---
URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"
SHEET_NAME = "在庫データ"

# --- 💡 リトライ機能付きの読み込み関数 ---
def get_records_with_retry(ws, retries=3):
    for i in range(retries):
        try:
            return ws.get_all_records()
        except Exception:
            if i < retries - 1:
                time.sleep(2) # 2秒待って再試行
                continue
            else:
                raise # 3回ダメならエラーを出す

# --- LINE連携 ---
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

# --- 🔐 ログイン管理 ---
if "user_id" not in st.session_state:
    qp = st.query_params
    if "code" not in qp:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #3e2723; font-size: 3.5rem;'>Stock Manager</h1>", unsafe_allow_html=True)
        st.link_button("LINEでログイン", get_line_login_url())
        st.stop()
    else:
        try:
            u_info = get_line_user_info(qp["code"])
            st.session_state.user_id = str(u_info.get("sub"))
            st.session_state.user_name = u_info.get("displayName") or "利用者"
            st.query_params.clear()
        except:
            st.error("認証エラーが発生しました。再ログインしてください。")
            st.stop()

uid = st.session_state.user_id
uname = st.session_state.user_name

# --- 🍎 メイン ---
st.markdown(f"<div class='user-title'>{uname} 様</div><div class='main-title'>在庫リスト</div>", unsafe_allow_html=True)

client = get_gspread_client()
if client:
    sh = client.open_by_url(URL)
    try:
        ws = sh.worksheet(SHEET_NAME)
    except:
        ws = sh.add_worksheet(title=SHEET_NAME, rows="1000", cols="10")
        ws.append_row(["品名", "数量", "賞味期限", "保存場所", "種類", "LINE_ID"])
        st.rerun()

    # 💡 読み込み（失敗してもリトライする）
    try:
        all_recs = get_records_with_retry(ws)
        all_df = pd.DataFrame(all_recs) if all_recs else pd.DataFrame(columns=["品名", "数量", "賞味期限", "保存場所", "種類", "LINE_ID"])
    except:
        st.warning("Google接続が不安定です。再読み込み中...")
        time.sleep(2)
        st.rerun()
    
    # フィルタリング
    if not all_df.empty:
        all_df["LINE_ID"] = all_df["LINE_ID"].astype(str)
        df = all_df[all_df["LINE_ID"] == uid].copy()
    else:
        df = pd.DataFrame(columns=["品名", "数量", "賞味期限", "保存場所", "種類", "LINE_ID"])

    with st.sidebar:
        st.markdown("### 在庫を追加")
        with st.form("add_form", clear_on_submit=True):
            n = st.text_input("品名")
            a = st.number_input("数量", min_value=1, value=1)
            e = st.date_input("賞味期限", value=date.today()).strftime('%Y/%m/%d')
            c1 = st.selectbox("保存場所", ["冷蔵", "冷凍", "常温", "その他"])
            c2 = st.selectbox("種類", ["肉", "野菜", "麺", "飲み物", "その他"])
            if st.form_submit_button("追加") and n:
                m = (all_df['品名'] == n) & (all_df['賞味期限'] == e) & (all_df['保存場所'] == c1) & (all_df['種類'] == c2) & (all_df['LINE_ID'] == uid)
                try:
                    if m.any():
                        idx = all_df.index[m][0]
                        new_val = int(all_df.at[idx, '数量']) + a
                        ws.update_cell(int(idx) + 2, 2, int(new_val))
                    else:
                        ws.append_row([n, int(a), e, c1, c2, uid])
                    st.rerun()
                except:
                    st.error("保存に失敗しました。少し待ってから再度「追加」を押してください。")

    if not df.empty:
        df_disp = df.copy()
        df_disp.insert(0, "選択", False)
        df_disp = df_disp[["選択", "品名", "数量", "賞味期限", "保存場所", "種類"]]

        search = st.text_input("検索")
        if search:
            df_disp = df_disp[df_disp.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("🔔 期限通知"):
                today = date.today()
                alrt = [f"・{r['品名']} ({r['賞味期限']})" for _, r in df.iterrows() if (datetime.strptime(str(r["賞味期限"]), '%Y/%m/%d').date() - today).days <= 3]
                if alrt:
                    requests.post("https://api.line.me/v2/bot/message/push", 
                                  headers={"Content-Type": "application/json", "Authorization": f"Bearer {st.secrets['line']['channel_access_token']}"},
                                  json={"to": uid, "messages": [{"type": "text", "text": "\n".join(alrt)}]})
                    st.success("通知済")
        with c2:
            del_btn = st.button("🗑️ 削除実行", type="primary")

        ed_res = st.data_editor(df_disp, use_container_width=True, hide_index=True, key="ed",
                                column_config={"選択": st.column_config.CheckboxColumn(), "数量": st.column_config.NumberColumn(min_value=0)},
                                disabled=["品名", "賞味期限", "保存場所", "種類"])

        # 数量変更
        if st.session_state.ed["edited_rows"]:
            for r_idx, chg in st.session_state.ed["edited_rows"].items():
                if "数量" in chg:
                    actual_idx = df_disp.index[r_idx]
                    try:
                        ws.update_cell(int(actual_idx) + 2, 2, int(chg["数量"]))
                        st.rerun()
                    except: st.error("API制限中です...")

        # 削除
        if del_btn:
            del_list = ed_res[ed_res["選択"] == True].index.tolist()
            if del_list:
                new_all = all_df.drop(del_list)
                ws.clear()
                ws.update('A1', [all_df.columns.tolist()] + new_all.values.tolist())
                st.rerun()
    else:
        st.info("データがありません。")
