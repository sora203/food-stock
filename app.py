import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("食品在庫管理アプリ")

try:
    # 接続の作成
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # URLをここで直接指定（Secretsの読み込みミスを回避！）
    url = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"
    
    df = conn.read(spreadsheet=url, ttl=0)
    st.write("### 現在の在庫一覧")
    st.dataframe(df)

except Exception as e:
    st.error("データの読み込みに失敗しました。")
    st.code(e)
