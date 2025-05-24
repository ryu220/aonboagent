import streamlit as st

st.title("YouTube Workflow AI Assistant - Simple Version")
st.write("This is a test version to check if deployment works.")

# Basic functionality without google-generativeai
workflow_types = [
    "チャンネルコンセプト設計",
    "動画マーケティング支援", 
    "動画企画生成＆SEO最適化",
    "YouTube Shorts企画生成",
    "Shorts台本生成",
    "コンテンツスコアリング",
    "キーワード戦略シミュレーション",
    "長尺動画台本生成"
]

selected = st.selectbox("ワークフローを選択してください", workflow_types)

if selected:
    st.write(f"選択されたワークフロー: {selected}")
    
    user_input = st.text_area("内容を入力してください")
    
    if st.button("生成"):
        st.write("⚠️ 現在、AI機能は一時的に無効化されています。")
        st.write("入力内容:", user_input)