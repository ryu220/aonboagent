import streamlit as st
import pandas as pd
import plotly.express as px

# Page configuration
st.set_page_config(
    page_title="YouTube Workflow Test App",
    page_icon="🎬",
    layout="wide"
)

# Main header
st.markdown("""
<div style="text-align: center;">
    <h1 style="color: #FF0000;">🎬 YouTube Workflow AI Assistant</h1>
    <h3>テスト版 - 動作確認用</h3>
</div>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.title("🛠️ 機能テスト")
test_option = st.sidebar.selectbox(
    "テストする機能を選択:",
    ["基本表示", "データ表示", "グラフ表示", "ユーザー入力"]
)

# Main content based on selection
if test_option == "基本表示":
    st.success("✅ Streamlitアプリが正常に動作しています！")
    st.info("🔧 この画面が表示されれば、基本的なStreamlit機能は問題ありません。")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("テスト項目", "基本表示", "✅")
    with col2:
        st.metric("ステータス", "正常", "✅")
    with col3:
        st.metric("次のステップ", "AI機能追加", "🔄")

elif test_option == "データ表示":
    st.subheader("📊 サンプルデータ表示テスト")
    
    # Sample data
    sample_data = pd.DataFrame({
        '動画タイトル': ['初心者向けYouTube入門', '再生数アップの秘訣', 'サムネイル作成講座'],
        '再生数': [1500, 2800, 3200],
        'いいね数': [45, 89, 156],
        'カテゴリ': ['教育', 'ハウツー', 'デザイン']
    })
    
    st.dataframe(sample_data, use_container_width=True)
    st.success("✅ データ表示機能は正常です！")

elif test_option == "グラフ表示":
    st.subheader("📈 グラフ表示テスト")
    
    # Sample chart data
    chart_data = pd.DataFrame({
        '日付': pd.date_range('2024-01-01', periods=30, freq='D'),
        '再生数': [100 + i*10 + (i**1.5) for i in range(30)]
    })
    
    fig = px.line(chart_data, x='日付', y='再生数', title='YouTube再生数推移（サンプル）')
    st.plotly_chart(fig, use_container_width=True)
    st.success("✅ グラフ表示機能は正常です！")

elif test_option == "ユーザー入力":
    st.subheader("✏️ ユーザー入力テスト")
    
    user_input = st.text_input("テスト用テキスト入力:")
    if user_input:
        st.write(f"入力されたテキスト: **{user_input}**")
        st.success("✅ ユーザー入力機能は正常です！")
    
    slider_value = st.slider("テスト用スライダー", 0, 100, 50)
    st.write(f"スライダーの値: **{slider_value}**")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>🧪 このテストアプリで全ての機能が正常に動作すれば、<br>
    次はAI機能（google-generativeai）を追加できます。</p>
</div>
""", unsafe_allow_html=True)