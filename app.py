import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date
import requests
import urllib.parse

# --- 設定 ---
st.set_page_config(page_title="LINE在庫管理", layout="wide")
URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# --- LINEログイン用の自作関数 ---
def get_line_login_url():
    client_id = st.secrets["line"]["login_channel_id"]
    # 💡 変換ミスを防ぐため、最初から安全な文字列として定義します
    redirect_uri = "https://food-memo-app.streamlit.app"
    
    # 💡 urlencodeを使って、LINEが認める完璧な形式に変換します
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": "random_string",
        "scope": "profile openid"
    }
    url = f"https://access.line.me/oauth2/v2.1/authorize?{urllib.parse.urlencode(params)}"
    return url

def get_line_user_info(code):
    token_url = "https://api.line.me/oauth2/v2.1/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "https://food-memo-app.streamlit.app", # ここも書き換える
        "client_id": st.secrets["line"]["login_channel_id"],
        "client_secret": st.secrets["line"]["login_channel_secret"]
    }
    res = requests.post(token_url, headers=headers, data=data).json()
    id_token = res.get("id_token")
    
    # IDトークンをデコードしてユーザー情報を取得
    payload = {"id_token": id_token, "client_id": st.secrets["line"]["login_channel_id"]}
    user_info = requests.post("https://api.line.me/oauth2/v2.1/verify", data=payload).json()
    return user_info

# --- 🔐 ログイン処理 ---
# --- 🔐 ログイン処理（デバッグ版） ---
query_params = st.query_params
if "code" not in query_params:
    st.title("🔐 在庫管理ログイン")
    
    # 1. プログラムが作ったURLを取得
    login_url = get_line_login_url()
    
    # 2. 画面にURLをそのまま表示（これで中身をチェックできます）
    st.warning("⚠️ デバッグ情報：LINEに送信するURLを確認してください")
    st.code(login_url)
    
    st.info("上のURLの中にある 'redirect_uri=' の後の部分が、LINE Developersの設定と1文字でも違うとエラーになります。")

    # 3. ログインボタン
    st.markdown(f'<a href="{login_url}" target="_self" style="background-color: #00B900; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">LINEでログイン</a>', unsafe_allow_html=True)
    st.stop()

# --- 以降、メインの在庫管理プログラム（前回のものと同じ） ---
st.title(f"🍎 {user_name} さんの在庫リスト")
# (ここから下のスプレッドシート処理などはそのまま継続)




