import streamlit as st
import os
from datetime import datetime
import json

# ページ設定
st.set_page_config(
    page_title="YouTube Workflow AI Assistant",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 YouTube Workflow AI Assistant")
st.write("YouTubeコンテンツ制作を支援するアプリケーション")

# セッション状態の初期化
if 'workflow_step' not in st.session_state:
    st.session_state.workflow_step = 0
if 'current_data' not in st.session_state:
    st.session_state.current_data = {}

# ワークフロー定義
WORKFLOWS = {
    "channel_concept": {
        "name": "チャンネルコンセプト設計",
        "description": "SEOキーワードとペルソナに基づいたチャンネル戦略立案",
        "icon": "🎯"
    },
    "video_marketing": {
        "name": "動画マーケティング支援",
        "description": "動画の内容からサムネイル文言とタイトルを生成",
        "icon": "🎨"
    }
}

# ワークフロー選択
cols = st.columns(2)
selected_workflow = None

for i, (key, workflow) in enumerate(WORKFLOWS.items()):
    with cols[i % 2]:
        if st.button(
            f"{workflow['icon']} {workflow['name']}", 
            key=f"btn_{key}",
            use_container_width=True,
            help=workflow['description']
        ):
            st.session_state.selected_workflow = key
            st.session_state.workflow_step = 0

# 選択されたワークフローの処理
if 'selected_workflow' in st.session_state and st.session_state.selected_workflow:
    workflow = WORKFLOWS[st.session_state.selected_workflow]
    
    st.markdown(f"## {workflow['icon']} {workflow['name']}")
    st.markdown(f"*{workflow['description']}*")
    
    # チャンネルコンセプト設計の例
    if st.session_state.selected_workflow == "channel_concept":
        if st.session_state.workflow_step == 0:
            st.markdown("### Step 1: 商品情報入力")
            
            product_name = st.text_input("商品・サービス名")
            product_description = st.text_area("商品・サービスの詳細")
            
            if st.button("次へ →", type="primary"):
                if product_name and product_description:
                    st.session_state.current_data = {
                        "product_name": product_name,
                        "product_description": product_description
                    }
                    st.session_state.workflow_step = 1
                    st.rerun()
                else:
                    st.error("必須項目を入力してください")
                    
        elif st.session_state.workflow_step == 1:
            st.markdown("### Step 2: 結果生成")
            st.write("入力された情報:")
            st.json(st.session_state.current_data)
            
            # ここでAI処理の代わりにダミーデータを表示
            st.success("✅ 処理完了！")
            st.write("""
            **生成されたコンセプト案:**
            1. 「〇〇専門チャンネル」- ターゲット層に特化した専門情報を提供
            2. 「初心者向け〇〇講座」- 分かりやすい解説で初心者を支援
            3. 「〇〇の裏技チャンネル」- 知られていないテクニックを紹介
            """)
            
            if st.button("← 戻る"):
                st.session_state.workflow_step = 0
                st.rerun()

# フッター
st.markdown("---")
st.markdown("💡 **注意**: 現在、AI機能は制限されています。")

# APIキー設定の案内
with st.expander("🔑 API設定について"):
    st.write("""
    完全な機能を使用するには、以下のAPIキーが必要です：
    - Gemini API Key (Google AI Studio)
    - Keyword Tool API Key (オプション)
    
    Streamlit CloudのSecretsに設定してください。
    """)