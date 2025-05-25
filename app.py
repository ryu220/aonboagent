import streamlit as st

# Page configuration - Must be first Streamlit command
st.set_page_config(
    page_title="YouTube Workflow AI Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

import os
import sys
from datetime import datetime
import json
from typing import Dict, List, Any, Optional

# デバッグ情報を表示
st.write("Python version:", sys.version)
st.write("Current working directory:", os.getcwd())

# インストール済みパッケージを確認
try:
    from importlib.metadata import distributions
    installed_packages = [dist.metadata['name'].lower() for dist in distributions()]
    if "google-generativeai" in installed_packages:
        st.success("google-generativeai is installed")
    else:
        st.error("google-generativeai is NOT installed")
        st.write("Installed packages:", sorted(installed_packages)[:20])  # 最初の20個を表示
except Exception as e:
    st.error(f"Error checking packages: {e}")
    # Fallback: 直接インポートを試す
    try:
        import google.generativeai
        st.success("google-generativeai detected via direct import")
    except ImportError:
        st.error("google-generativeai is not available")

# Google Generative AIをインポート
try:
    import google.generativeai as genai
    st.success("Successfully imported google.generativeai")
except ImportError as e:
    st.error(f"Failed to import google.generativeai: {e}")
    st.error("Trying alternative import...")
    try:
        import google.generativeai as genai
    except Exception as e2:
        st.error(f"Second attempt failed: {e2}")
        genai = None

from streamlit_option_menu import option_menu
import requests
import yaml
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize session state
if 'workflow_history' not in st.session_state:
    st.session_state.workflow_history = []
if 'current_data' not in st.session_state:
    st.session_state.current_data = {}
if 'selected_workflow' not in st.session_state:
    st.session_state.selected_workflow = None
if 'workflow_step' not in st.session_state:
    st.session_state.workflow_step = 0

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF0000;
        text-align: center;
        margin-bottom: 2rem;
    }
    .workflow-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border-left: 4px solid #FF0000;
    }
    .result-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 8px;
        margin-top: 1rem;
        border: 1px solid #b8d4e3;
    }
    .step-indicator {
        display: flex;
        justify-content: space-between;
        margin-bottom: 2rem;
    }
    .step {
        flex: 1;
        text-align: center;
        padding: 0.5rem;
        background-color: #e0e0e0;
        margin: 0 0.25rem;
        border-radius: 5px;
        font-weight: bold;
    }
    .step.active {
        background-color: #FF0000;
        color: white;
    }
    .step.completed {
        background-color: #4CAF50;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Workflow definitions
WORKFLOWS = {
    "channel_concept": {
        "name": "チャンネルコンセプト設計",
        "description": "YouTubeチャンネルのコンセプトを設計し、SEOキーワードとペルソナに基づいた戦略を立案",
        "icon": "🎯",
        "steps": ["商品情報入力", "キーワード分析", "ペルソナ設計", "コンセプト生成"]
    },
    "video_marketing": {
        "name": "動画マーケティング支援",
        "description": "動画の内容からサムネイル文言とタイトルを生成",
        "icon": "🎨",
        "steps": ["動画内容入力", "ペルソナ分析", "サムネ・タイトル生成", "最適化"]
    },
    "video_planning": {
        "name": "動画企画生成＆SEO最適化",
        "description": "SEOキーワードに基づいた動画企画とタイトル案を生成",
        "icon": "📋",
        "steps": ["キーワード入力", "競合分析", "企画生成", "評価・選定"]
    },
    "shorts_planning": {
        "name": "YouTube Shorts企画生成",
        "description": "ショート動画向けの企画案を大量生成し、ランキング評価",
        "icon": "📱",
        "steps": ["キーワード入力", "競合分析", "企画生成", "ランキング評価"]
    },
    "shorts_script": {
        "name": "Shorts台本生成",
        "description": "最新トレンドを踏まえたショート動画台本を作成",
        "icon": "📝",
        "steps": ["企画入力", "リサーチ", "台本生成", "最適化"]
    },
    "content_scoring": {
        "name": "コンテンツスコアリング",
        "description": "作成したコンテンツの品質を評価し、改善点をフィードバック",
        "icon": "📊",
        "steps": ["コンテンツ入力", "ペルソナ分析", "評価実施", "改善提案"]
    },
    "keyword_strategy": {
        "name": "キーワード戦略シミュレーション",
        "description": "YouTube運用のためのキーワード戦略を多角的に分析・提案",
        "icon": "🔍",
        "steps": ["初期情報入力", "キーワード収集", "評価分析", "戦略提案"]
    },
    "long_content": {
        "name": "長尺動画台本生成",
        "description": "様々なスタイルの長尺動画台本を生成",
        "icon": "🎬",
        "steps": ["スタイル選択", "情報入力", "台本生成", "最適化"]
    }
}

class YouTubeWorkflowApp:
    def __init__(self):
        self.setup_apis()
        
    def setup_apis(self):
        """APIの初期設定"""
        # Gemini API setup - Streamlit CloudのSecretsまたは環境変数から取得
        gemini_api_key = None
        
        # Streamlit Cloudの場合
        if "GEMINI_API_KEY" in st.secrets:
            gemini_api_key = st.secrets["GEMINI_API_KEY"]
        # ローカル環境の場合
        else:
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        else:
            self.model = None
            st.warning("⚠️ Gemini APIキーが設定されていません。アプリの機能が制限されます。")
            
        # Keyword Tool API setup
        if "KEYWORD_TOOL_API_KEY" in st.secrets:
            self.keyword_api_key = st.secrets["KEYWORD_TOOL_API_KEY"]
        else:
            self.keyword_api_key = os.getenv("KEYWORD_TOOL_API_KEY")
            
        self.keyword_api_url = "https://api.keywordtool.io/v2/search/suggestions/youtube"
        
    def get_keywords(self, keyword: str, country: str = "jp", language: str = "ja") -> List[Dict]:
        """Keyword Tool APIを使用してキーワードを取得"""
        if not self.keyword_api_key:
            # モックデータを返す（API keyがない場合）
            return self._get_mock_keywords(keyword)
            
        params = {
            "apikey": self.keyword_api_key,
            "keyword": keyword,
            "country": country,
            "language": language,
            "metrics": "true",
            "output": "json"
        }
        
        try:
            response = requests.get(self.keyword_api_url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])[:30]  # Top 30 keywords
            else:
                st.error(f"Keyword API Error: {response.status_code}")
                return self._get_mock_keywords(keyword)
        except Exception as e:
            st.error(f"Keyword API Error: {str(e)}")
            return self._get_mock_keywords(keyword)
            
    def _get_mock_keywords(self, keyword: str) -> List[Dict]:
        """モックキーワードデータを生成"""
        base_keywords = [
            f"{keyword} やり方",
            f"{keyword} 方法",
            f"{keyword} 初心者",
            f"{keyword} おすすめ",
            f"{keyword} 比較",
            f"{keyword} 2024",
            f"{keyword} 始め方",
            f"{keyword} コツ",
            f"{keyword} 注意点",
            f"{keyword} メリット"
        ]
        
        return [
            {
                "keyword": kw,
                "search_volume": 1000 + (i * 100),
                "competition": round(0.3 + (i * 0.05), 2),
                "cpc": round(50 + (i * 10), 2)
            }
            for i, kw in enumerate(base_keywords)
        ]
        
    def generate_with_gemini(self, prompt: str) -> str:
        """Gemini APIを使用してコンテンツを生成"""
        if not self.model:
            return "⚠️ Gemini APIが設定されていません。環境変数 GEMINI_API_KEY を設定してください。"
            
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            st.error(f"Gemini API Error: {str(e)}")
            return f"エラーが発生しました: {str(e)}"
            
    def save_to_history(self, workflow_type: str, data: Dict):
        """作業履歴を保存"""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "workflow_type": workflow_type,
            "data": data
        }
        st.session_state.workflow_history.append(history_entry)
        st.session_state.current_data.update(data)
        
    def load_prompts(self) -> Dict:
        """YAMLファイルからプロンプトを読み込む"""
        try:
            with open("prompts.yaml", "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return self._get_default_prompts()
            
    def _get_default_prompts(self) -> Dict:
        """デフォルトのプロンプトを返す"""
        return {
            "channel_concept": {
                "step1": """
                #TASK_EXECUTION[TYPE=YouTubeチャンネル設計支援]
                
                Step1: ユーザー入力から販売商品情報を収集する。
                商品情報: {product_info}
                サービスURL: {service_url}
                
                Step2: 商品と関連性があり、検索ボリュームが高いYouTube SEOキーワードを30個抽出し、ボリューム順にランキング
                """,
                "step2": """
                Step3: 上位3キーワードに対して、それぞれユーザーペルソナ像を3つずつ抽出
                キーワード: {keywords}
                """,
                "step3": """
                Step4: 合計9ペルソナから最も相関性の高い3ペルソナを選定
                Step5: 3ペルソナが達成したい未来像（ゴールイメージ）を3つ作成
                ペルソナ情報: {personas}
                """,
                "step4": """
                Step6: 3つのゴールイメージとTOP3キーワードに基づいて、チャンネルコンセプト案を30個生成
                タイトルは13文字以内、コンセプト名にはYouTube SEOキーワードを入れる
                
                ゴールイメージ: {goals}
                キーワード: {keywords}
                """
            }
        }

def main():
    app = YouTubeWorkflowApp()
    
    # Header
    st.markdown('<h1 class="main-header">🎬 YouTube Workflow AI Assistant</h1>', unsafe_allow_html=True)
    
    # Workflow selection with icons
    cols = st.columns(4)
    selected_workflow = None
    
    for i, (key, workflow) in enumerate(WORKFLOWS.items()):
        with cols[i % 4]:
            if st.button(
                f"{workflow['icon']} {workflow['name']}", 
                key=f"btn_{key}",
                use_container_width=True,
                help=workflow['description']
            ):
                st.session_state.selected_workflow = key
                st.session_state.workflow_step = 0
                
    # Display selected workflow
    if st.session_state.selected_workflow:
        workflow = WORKFLOWS[st.session_state.selected_workflow]
        
        # Workflow header
        st.markdown(f"## {workflow['icon']} {workflow['name']}")
        st.markdown(f"*{workflow['description']}*")
        
        # Step indicator
        st.markdown('<div class="step-indicator">', unsafe_allow_html=True)
        step_html = ""
        for i, step_name in enumerate(workflow['steps']):
            status = "completed" if i < st.session_state.workflow_step else "active" if i == st.session_state.workflow_step else ""
            step_html += f'<div class="step {status}">{i+1}. {step_name}</div>'
        st.markdown(step_html + '</div>', unsafe_allow_html=True)
        
        # Workflow specific UI
        if st.session_state.selected_workflow == "channel_concept":
            handle_channel_concept_workflow(app)
        elif st.session_state.selected_workflow == "video_marketing":
            handle_video_marketing_workflow(app)
        elif st.session_state.selected_workflow == "video_planning":
            handle_video_planning_workflow(app)
        elif st.session_state.selected_workflow == "shorts_planning":
            handle_shorts_planning_workflow(app)
        elif st.session_state.selected_workflow == "shorts_script":
            handle_shorts_script_workflow(app)
        elif st.session_state.selected_workflow == "content_scoring":
            handle_content_scoring_workflow(app)
        elif st.session_state.selected_workflow == "keyword_strategy":
            handle_keyword_strategy_workflow(app)
        elif st.session_state.selected_workflow == "long_content":
            handle_long_content_workflow(app)
    
    # History sidebar
    with st.sidebar:
        st.markdown("## 📜 作業履歴")
        if st.session_state.workflow_history:
            for i, entry in enumerate(reversed(st.session_state.workflow_history[-10:])):
                workflow_name = WORKFLOWS.get(entry['workflow_type'], {}).get('name', 'Unknown')
                st.markdown(f"**{i+1}. {workflow_name}**")
                st.caption(f"{entry['timestamp'][:19]}")
                if st.button(f"データを再利用", key=f"reuse_{i}"):
                    st.session_state.current_data.update(entry['data'])
                    st.rerun()
                st.divider()

def handle_channel_concept_workflow(app: YouTubeWorkflowApp):
    """チャンネルコンセプト設計ワークフロー"""
    if st.session_state.workflow_step == 0:
        # Step 1: 商品情報入力
        st.markdown("### Step 1: 商品情報入力")
        
        col1, col2 = st.columns(2)
        with col1:
            product_name = st.text_input("商品・サービス名", value=st.session_state.current_data.get("product_name", ""))
            service_url = st.text_input("サービスURL（任意）", value=st.session_state.current_data.get("service_url", ""))
        
        with col2:
            target_audience = st.text_area("ターゲット層", value=st.session_state.current_data.get("target_audience", ""))
            product_description = st.text_area("商品・サービスの詳細", value=st.session_state.current_data.get("product_description", ""))
        
        if st.button("次へ →", type="primary", use_container_width=True):
            if product_name and product_description:
                data = {
                    "product_name": product_name,
                    "service_url": service_url,
                    "target_audience": target_audience,
                    "product_description": product_description
                }
                app.save_to_history("channel_concept", data)
                st.session_state.workflow_step = 1
                st.rerun()
            else:
                st.error("必須項目を入力してください")
                
    elif st.session_state.workflow_step == 1:
        # Step 2: キーワード分析
        st.markdown("### Step 2: キーワード分析")
        
        # キーワード検索
        search_keyword = st.text_input("検索キーワード", value=st.session_state.current_data.get("product_name", ""))
        
        if st.button("キーワード分析実行", type="primary"):
            with st.spinner("キーワードを分析中..."):
                # Keyword Tool API
                keywords = app.get_keywords(search_keyword)
                
                # Geminiでの分析
                prompt = f"""
                商品情報:
                - 商品名: {st.session_state.current_data.get('product_name')}
                - 説明: {st.session_state.current_data.get('product_description')}
                - ターゲット: {st.session_state.current_data.get('target_audience')}
                
                以下のキーワードリストから、YouTube SEOに最適な上位30個のキーワードを選定し、
                検索ボリュームと商品との関連性を考慮してランキングしてください：
                
                {json.dumps(keywords, ensure_ascii=False, indent=2)}
                
                出力形式:
                1. キーワード名 - 推定月間検索数 - 商品との関連性スコア(10点満点)
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['keywords_analysis'] = result
                st.session_state.current_data['keywords'] = keywords[:3]  # Top 3 for next step
                
                # 結果表示
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### 分析結果")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # キーワードチャート
                if keywords:
                    df = pd.DataFrame(keywords[:10])
                    fig = px.bar(df, x='keyword', y='search_volume', 
                                title='キーワード検索ボリューム Top 10',
                                labels={'search_volume': '月間検索数', 'keyword': 'キーワード'})
                    st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.workflow_step = 0
                st.rerun()
        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                if 'keywords_analysis' in st.session_state.current_data:
                    st.session_state.workflow_step = 2
                    st.rerun()
                else:
                    st.error("キーワード分析を実行してください")
                    
    elif st.session_state.workflow_step == 2:
        # Step 3: ペルソナ設計
        st.markdown("### Step 3: ペルソナ設計")
        
        if st.button("ペルソナ分析実行", type="primary"):
            with st.spinner("ペルソナを分析中..."):
                prompt = f"""
                上位3キーワード: {st.session_state.current_data.get('keywords', [])}
                商品情報: {st.session_state.current_data.get('product_description')}
                
                各キーワードに対して、検索する可能性の高いユーザーペルソナを3つずつ（計9つ）作成してください。
                各ペルソナには以下を含めてください：
                - 名前（仮名）
                - 年齢・性別
                - 職業・ライフスタイル
                - 悩み・課題
                - 目標・願望
                - YouTubeの利用傾向
                
                その後、9つのペルソナから最も商品と相関性の高い3つを選定し、その理由も説明してください。
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['personas_analysis'] = result
                
                # 結果表示
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### ペルソナ分析結果")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.workflow_step = 1
                st.rerun()
        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                if 'personas_analysis' in st.session_state.current_data:
                    st.session_state.workflow_step = 3
                    st.rerun()
                else:
                    st.error("ペルソナ分析を実行してください")
                    
    elif st.session_state.workflow_step == 3:
        # Step 4: コンセプト生成
        st.markdown("### Step 4: チャンネルコンセプト生成")
        
        if st.button("コンセプト生成実行", type="primary"):
            with st.spinner("コンセプトを生成中..."):
                prompt = f"""
                選定した3つのペルソナ: {st.session_state.current_data.get('personas_analysis')}
                TOP3キーワード: {st.session_state.current_data.get('keywords', [])}
                商品情報: {st.session_state.current_data.get('product_description')}
                
                以下の条件でチャンネルコンセプト案を30個生成してください：
                1. タイトルは13文字以内
                2. YouTube SEOキーワードを必ず含める
                3. 3つのペルソナの願望を実現できる内容
                4. 商品・サービスとの関連性を明確に
                
                各コンセプトには以下を含めてください：
                - コンセプト名（13文字以内）
                - サブタイトル（説明文）
                - ターゲットペルソナとの親和性（どのペルソナに特に刺さるか）
                - 想定される動画コンテンツ例（3つ）
                - 差別化ポイント
                
                最後に、最も推奨する上位5つをランキング形式で提示してください。
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['concepts'] = result
                
                # 結果表示
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### チャンネルコンセプト案")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # 完了メッセージ
                st.success("✅ チャンネルコンセプト設計が完了しました！")
                
                # エクスポート機能
                if st.button("結果をダウンロード", type="secondary"):
                    result_text = f"""
チャンネルコンセプト設計結果
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

【商品情報】
商品名: {st.session_state.current_data.get('product_name')}
URL: {st.session_state.current_data.get('service_url')}
説明: {st.session_state.current_data.get('product_description')}
ターゲット: {st.session_state.current_data.get('target_audience')}

【キーワード分析】
{st.session_state.current_data.get('keywords_analysis')}

【ペルソナ分析】
{st.session_state.current_data.get('personas_analysis')}

【チャンネルコンセプト】
{st.session_state.current_data.get('concepts')}
"""
                    st.download_button(
                        label="テキストファイルをダウンロード",
                        data=result_text,
                        file_name=f"channel_concept_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )
        
        if st.button("← 戻る", use_container_width=True):
            st.session_state.workflow_step = 2
            st.rerun()

# 他のワークフローハンドラー関数も同様に実装...

def handle_video_marketing_workflow(app: YouTubeWorkflowApp):
    """動画マーケティング支援ワークフロー"""
    if st.session_state.workflow_step == 0:
        # Step 1: 動画内容入力
        st.markdown("### Step 1: 動画内容入力")
        
        col1, col2 = st.columns(2)
        with col1:
            video_title = st.text_input("動画タイトル（仮）", value=st.session_state.current_data.get("video_title", ""))
            video_url = st.text_input("動画URL（任意）", value=st.session_state.current_data.get("video_url", ""))
            target_keywords = st.text_input("ターゲットキーワード", value=st.session_state.current_data.get("target_keywords", ""))
        
        with col2:
            video_content = st.text_area("動画の内容・概要", height=150, value=st.session_state.current_data.get("video_content", ""))
            channel_concept = st.text_area("チャンネルコンセプト（任意）", value=st.session_state.current_data.get("channel_concept", ""))
        
        if st.button("次へ →", type="primary", use_container_width=True):
            if video_title and video_content:
                data = {
                    "video_title": video_title,
                    "video_url": video_url,
                    "target_keywords": target_keywords,
                    "video_content": video_content,
                    "channel_concept": channel_concept
                }
                app.save_to_history("video_marketing", data)
                st.session_state.workflow_step = 1
                st.rerun()
            else:
                st.error("必須項目を入力してください")
                
    elif st.session_state.workflow_step == 1:
        # Step 2: ペルソナ分析
        st.markdown("### Step 2: ペルソナ分析")
        
        if st.button("ペルソナ分析実行", type="primary"):
            with st.spinner("視聴者ペルソナを分析中..."):
                prompt = f"""
                動画内容: {st.session_state.current_data.get('video_content')}
                ターゲットキーワード: {st.session_state.current_data.get('target_keywords')}
                チャンネルコンセプト: {st.session_state.current_data.get('channel_concept')}
                
                この動画を視聴する可能性が高いペルソナを3つ作成してください。
                各ペルソナには以下を含めてください：
                - 年齢・性別・職業
                - 興味関心事項
                - 悩みや課題
                - この動画から得たい情報
                - YouTubeの利用パターン
                - サムネイルで響く要素
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['persona_analysis'] = result
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### ペルソナ分析結果")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.workflow_step = 0
                st.rerun()
        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                if 'persona_analysis' in st.session_state.current_data:
                    st.session_state.workflow_step = 2
                    st.rerun()
                else:
                    st.error("ペルソナ分析を実行してください")
                    
    elif st.session_state.workflow_step == 2:
        # Step 3: サムネ・タイトル生成
        st.markdown("### Step 3: サムネイル文言とタイトル生成")
        
        if st.button("生成実行", type="primary"):
            with st.spinner("サムネイル文言とタイトルを生成中..."):
                prompt = f"""
                動画内容: {st.session_state.current_data.get('video_content')}
                ペルソナ分析: {st.session_state.current_data.get('persona_analysis')}
                ターゲットキーワード: {st.session_state.current_data.get('target_keywords')}
                
                以下を生成してください：
                
                1. サムネイル文言案（10個）
                   - インパクトのある短い文言
                   - 感情に訴える表現
                   - 数字や具体性を含む
                   - 最大15文字程度
                
                2. 動画タイトル案（10個）
                   - SEOキーワードを含む
                   - クリック率を高める要素
                   - 60文字以内
                   - ペルソナの関心を引く内容
                
                3. 各案の推奨度とその理由
                
                4. 最も効果的な組み合わせTOP3
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['thumbnails_titles'] = result
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### 生成結果")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.workflow_step = 1
                st.rerun()
        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                if 'thumbnails_titles' in st.session_state.current_data:
                    st.session_state.workflow_step = 3
                    st.rerun()
                else:
                    st.error("生成を実行してください")
                    
    elif st.session_state.workflow_step == 3:
        # Step 4: 最適化
        st.markdown("### Step 4: 最適化とフィードバック")
        
        # ユーザーが選択できるように
        st.markdown("#### 生成された案から選択")
        selected_thumbnail = st.text_input("使用するサムネイル文言", value=st.session_state.current_data.get("selected_thumbnail", ""))
        selected_title = st.text_input("使用するタイトル", value=st.session_state.current_data.get("selected_title", ""))
        
        if st.button("最適化分析実行", type="primary"):
            with st.spinner("最適化案を生成中..."):
                prompt = f"""
                選択されたサムネイル文言: {selected_thumbnail}
                選択されたタイトル: {selected_title}
                動画内容: {st.session_state.current_data.get('video_content')}
                ペルソナ: {st.session_state.current_data.get('persona_analysis')}
                
                以下の観点で最適化案を提供してください：
                
                1. クリック率向上のための改善案
                   - サムネイル文言の微調整案（3個）
                   - タイトルの微調整案（3個）
                
                2. A/Bテスト案
                   - テストすべきバリエーション
                   - 測定指標と期待される効果
                
                3. 関連動画対策
                   - 説明文に含めるべきキーワード
                   - タグの推奨リスト（20個）
                   - 関連動画として表示されやすくなる工夫
                
                4. 公開タイミングの推奨
                   - 最適な公開曜日と時間帯
                   - その理由
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['optimization'] = result
                st.session_state.current_data['selected_thumbnail'] = selected_thumbnail
                st.session_state.current_data['selected_title'] = selected_title
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### 最適化提案")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.success("✅ 動画マーケティング支援が完了しました！")
                
                # エクスポート
                if st.button("結果をダウンロード", type="secondary"):
                    result_text = f"""
動画マーケティング支援結果
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

【動画情報】
タイトル: {st.session_state.current_data.get('video_title')}
内容: {st.session_state.current_data.get('video_content')}
キーワード: {st.session_state.current_data.get('target_keywords')}

【ペルソナ分析】
{st.session_state.current_data.get('persona_analysis')}

【サムネイル・タイトル案】
{st.session_state.current_data.get('thumbnails_titles')}

【選択した案】
サムネイル: {selected_thumbnail}
タイトル: {selected_title}

【最適化提案】
{st.session_state.current_data.get('optimization')}
"""
                    st.download_button(
                        label="テキストファイルをダウンロード",
                        data=result_text,
                        file_name=f"video_marketing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )
        
        if st.button("← 戻る", use_container_width=True):
            st.session_state.workflow_step = 2
            st.rerun()

def handle_video_planning_workflow(app: YouTubeWorkflowApp):
    """動画企画生成ワークフロー"""
    if st.session_state.workflow_step == 0:
        # Step 1: キーワード入力
        st.markdown("### Step 1: キーワード入力")
        
        col1, col2 = st.columns(2)
        with col1:
            main_keyword = st.text_input("メインキーワード", value=st.session_state.current_data.get("main_keyword", ""))
            target_audience = st.text_input("ターゲット層", value=st.session_state.current_data.get("target_audience", ""))
        
        with col2:
            channel_name = st.text_input("チャンネル名", value=st.session_state.current_data.get("channel_name", ""))
            channel_theme = st.text_area("チャンネルテーマ・コンセプト", value=st.session_state.current_data.get("channel_theme", ""))
        
        video_style = st.multiselect(
            "希望する動画スタイル",
            ["解説・教育", "エンターテインメント", "ハウツー・チュートリアル", "レビュー・比較", "Vlog・日常", "ニュース・情報"],
            default=st.session_state.current_data.get("video_style", [])
        )
        
        if st.button("次へ →", type="primary", use_container_width=True):
            if main_keyword and channel_name:
                data = {
                    "main_keyword": main_keyword,
                    "target_audience": target_audience,
                    "channel_name": channel_name,
                    "channel_theme": channel_theme,
                    "video_style": video_style
                }
                app.save_to_history("video_planning", data)
                st.session_state.workflow_step = 1
                st.rerun()
            else:
                st.error("必須項目を入力してください")
                
    elif st.session_state.workflow_step == 1:
        # Step 2: 競合分析
        st.markdown("### Step 2: 競合分析")
        
        search_keyword = st.text_input("検索キーワード", value=st.session_state.current_data.get("main_keyword", ""))
        
        if st.button("競合分析実行", type="primary"):
            with st.spinner("キーワードと競合を分析中..."):
                # キーワード取得
                keywords = app.get_keywords(search_keyword)
                
                prompt = f"""
                メインキーワード: {st.session_state.current_data.get('main_keyword')}
                関連キーワード: {json.dumps(keywords[:10], ensure_ascii=False, indent=2)}
                チャンネルテーマ: {st.session_state.current_data.get('channel_theme')}
                
                以下を分析してください：
                
                1. キーワードの検索トレンド分析
                   - 季節性やトレンドの有無
                   - 関連トピックの人気度
                   - 競合性の評価
                
                2. 想定される競合動画の特徴
                   - よくある動画構成
                   - 人気コンテンツの共通点
                   - 差別化のポイント
                
                3. 狙うべきニッチキーワード
                   - ロングテールキーワード10個
                   - 各キーワードの狙い目度
                
                4. 成功する動画の要素
                   - タイトルの特徴
                   - サムネイルの傾向
                   - 動画時間の目安
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['competitive_analysis'] = result
                st.session_state.current_data['keywords_data'] = keywords[:10]
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### 競合分析結果")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # キーワードチャート
                if keywords:
                    df = pd.DataFrame(keywords[:10])
                    fig = px.scatter(df, x='search_volume', y='competition', 
                                    text='keyword', size='search_volume',
                                    title='キーワード分析（検索ボリューム vs 競合性）',
                                    labels={'search_volume': '月間検索数', 'competition': '競合性'})
                    fig.update_traces(textposition='top center')
                    st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.workflow_step = 0
                st.rerun()
        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                if 'competitive_analysis' in st.session_state.current_data:
                    st.session_state.workflow_step = 2
                    st.rerun()
                else:
                    st.error("競合分析を実行してください")
                    
    elif st.session_state.workflow_step == 2:
        # Step 3: 企画生成
        st.markdown("### Step 3: 動画企画生成")
        
        generation_count = st.slider("生成する企画数", min_value=10, max_value=50, value=30, step=5)
        
        if st.button("企画生成実行", type="primary"):
            with st.spinner(f"{generation_count}個の企画を生成中..."):
                prompt = f"""
                チャンネル情報:
                - 名前: {st.session_state.current_data.get('channel_name')}
                - テーマ: {st.session_state.current_data.get('channel_theme')}
                - スタイル: {st.session_state.current_data.get('video_style')}
                
                キーワード: {st.session_state.current_data.get('main_keyword')}
                競合分析: {st.session_state.current_data.get('competitive_analysis')}
                ターゲット層: {st.session_state.current_data.get('target_audience')}
                
                {generation_count}個の動画企画を生成してください。各企画には以下を含めてください：
                
                1. 動画タイトル（SEO最適化済み、60文字以内）
                2. 動画の概要（3行程度）
                3. 想定再生時間
                4. 主要なコンテンツポイント（5つ）
                5. サムネイル案
                6. 想定視聴者層
                7. 期待される効果（視聴者維持率、クリック率など）
                8. 制作難易度（低・中・高）
                9. 必要なリソース
                
                企画は以下のカテゴリーに分けて生成してください：
                - 教育・解説系（{generation_count//3}個）
                - エンタメ・体験系（{generation_count//3}個）
                - 実践・実演系（{generation_count//3}個）
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['video_plans'] = result
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### 生成された動画企画")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.workflow_step = 1
                st.rerun()
        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                if 'video_plans' in st.session_state.current_data:
                    st.session_state.workflow_step = 3
                    st.rerun()
                else:
                    st.error("企画生成を実行してください")
                    
    elif st.session_state.workflow_step == 3:
        # Step 4: 評価・選定
        st.markdown("### Step 4: 企画評価と選定")
        
        if st.button("企画評価実行", type="primary"):
            with st.spinner("企画を評価中..."):
                prompt = f"""
                生成された企画: {st.session_state.current_data.get('video_plans')}
                チャンネル情報: {st.session_state.current_data.get('channel_name')} - {st.session_state.current_data.get('channel_theme')}
                
                各企画を以下の観点で評価し、TOP10をランキングしてください：
                
                評価基準（各10点満点）：
                1. SEO効果: キーワード最適化とYouTube検索での発見されやすさ
                2. 視聴者興味: ターゲット層の関心を引く度合い
                3. 実現可能性: 制作の容易さとリソース効率
                4. 差別化: 競合との差別化度合い
                5. 成長可能性: シリーズ化や関連動画への展開可能性
                
                各企画について：
                - 総合スコア（50点満点）
                - 各項目の点数と理由
                - 改善提案
                - 優先順位
                
                最後に、TOP10の企画について：
                - 制作順序の推奨
                - 相乗効果を生む組み合わせ
                - 初動で狙うべき3本
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['evaluation'] = result
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### 企画評価結果")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.success("✅ 動画企画生成が完了しました！")
                
                # エクスポート
                if st.button("結果をダウンロード", type="secondary"):
                    result_text = f"""
動画企画生成結果
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

【基本情報】
チャンネル名: {st.session_state.current_data.get('channel_name')}
テーマ: {st.session_state.current_data.get('channel_theme')}
メインキーワード: {st.session_state.current_data.get('main_keyword')}
ターゲット層: {st.session_state.current_data.get('target_audience')}

【競合分析】
{st.session_state.current_data.get('competitive_analysis')}

【生成された企画】
{st.session_state.current_data.get('video_plans')}

【評価結果】
{st.session_state.current_data.get('evaluation')}
"""
                    st.download_button(
                        label="テキストファイルをダウンロード",
                        data=result_text,
                        file_name=f"video_planning_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )
        
        if st.button("← 戻る", use_container_width=True):
            st.session_state.workflow_step = 2
            st.rerun()

def handle_shorts_planning_workflow(app: YouTubeWorkflowApp):
    """Shorts企画生成ワークフロー"""
    if st.session_state.workflow_step == 0:
        # Step 1: キーワード入力
        st.markdown("### Step 1: 基本情報入力")
        
        col1, col2 = st.columns(2)
        with col1:
            shorts_theme = st.text_input("Shortsのテーマ・ジャンル", value=st.session_state.current_data.get("shorts_theme", ""))
            target_keywords = st.text_input("ターゲットキーワード", value=st.session_state.current_data.get("target_keywords", ""))
            channel_name = st.text_input("チャンネル名", value=st.session_state.current_data.get("channel_name", ""))
        
        with col2:
            target_age = st.selectbox(
                "メインターゲット年齢層",
                ["10代", "20代前半", "20代後半", "30代", "40代", "50代以上", "全年齢"],
                index=1 if not st.session_state.current_data.get("target_age") else 
                      ["10代", "20代前半", "20代後半", "30代", "40代", "50代以上", "全年齢"].index(st.session_state.current_data.get("target_age"))
            )
            content_style = st.multiselect(
                "コンテンツスタイル",
                ["面白系", "感動系", "お役立ち系", "驚き系", "癒し系", "教育系", "ニュース系"],
                default=st.session_state.current_data.get("content_style", ["面白系"])
            )
        
        trends_consideration = st.checkbox("最新トレンドを考慮する", value=st.session_state.current_data.get("trends_consideration", True))
        
        if st.button("次へ →", type="primary", use_container_width=True):
            if shorts_theme and target_keywords:
                data = {
                    "shorts_theme": shorts_theme,
                    "target_keywords": target_keywords,
                    "channel_name": channel_name,
                    "target_age": target_age,
                    "content_style": content_style,
                    "trends_consideration": trends_consideration
                }
                app.save_to_history("shorts_planning", data)
                st.session_state.workflow_step = 1
                st.rerun()
            else:
                st.error("必須項目を入力してください")
                
    elif st.session_state.workflow_step == 1:
        # Step 2: 競合分析
        st.markdown("### Step 2: Shorts市場分析")
        
        if st.button("市場分析実行", type="primary"):
            with st.spinner("Shorts市場を分析中..."):
                # キーワード分析
                keywords = app.get_keywords(st.session_state.current_data.get("target_keywords"))
                
                prompt = f"""
                Shortsテーマ: {st.session_state.current_data.get('shorts_theme')}
                キーワード: {st.session_state.current_data.get('target_keywords')}
                関連キーワード: {json.dumps(keywords[:10], ensure_ascii=False, indent=2)}
                ターゲット層: {st.session_state.current_data.get('target_age')}
                
                YouTube Shortsの市場分析を行ってください：
                
                1. 現在のトレンド分析
                   - 人気のShorts形式（構成パターン）
                   - バズりやすいコンテンツの特徴
                   - 使われている音楽・効果音の傾向
                   - ハッシュタグトレンド
                
                2. 競合Shorts分析
                   - 同ジャンルの成功パターン
                   - 平均視聴回数と再生時間
                   - エンゲージメント率の高い要素
                   - サムネイルとタイトルの特徴
                
                3. 視聴者行動分析
                   - Shortsの視聴パターン
                   - スワイプされやすい要因
                   - リピート視聴を促す要素
                   - コメント・シェアを促すポイント
                
                4. 差別化ポイント
                   - 未開拓のニッチ領域
                   - 新しい切り口のアイデア
                   - 独自性を出せる要素
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['market_analysis'] = result
                st.session_state.current_data['keywords_data'] = keywords[:10]
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### 市場分析結果")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.workflow_step = 0
                st.rerun()
        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                if 'market_analysis' in st.session_state.current_data:
                    st.session_state.workflow_step = 2
                    st.rerun()
                else:
                    st.error("市場分析を実行してください")
                    
    elif st.session_state.workflow_step == 2:
        # Step 3: 企画生成
        st.markdown("### Step 3: Shorts企画大量生成")
        
        generation_count = st.slider("生成する企画数", min_value=30, max_value=100, value=50, step=10)
        
        if st.button("企画生成実行", type="primary"):
            with st.spinner(f"{generation_count}個のShorts企画を生成中..."):
                prompt = f"""
                基本情報:
                - テーマ: {st.session_state.current_data.get('shorts_theme')}
                - キーワード: {st.session_state.current_data.get('target_keywords')}
                - ターゲット: {st.session_state.current_data.get('target_age')}
                - スタイル: {st.session_state.current_data.get('content_style')}
                
                市場分析: {st.session_state.current_data.get('market_analysis')}
                
                {generation_count}個のYouTube Shorts企画を生成してください。
                各企画には以下を含めてください：
                
                1. タイトル（30文字以内、フック効果重視）
                2. 冒頭3秒のフック（視聴者を引き込む仕掛け）
                3. メインコンテンツ（15-30秒の構成）
                4. オチ・結末（最後まで見たくなる工夫）
                5. 使用する音楽・効果音の提案
                6. 必要な素材・準備物
                7. 撮影・編集のポイント
                8. 想定視聴回数（低/中/高）
                9. バズる可能性（★1-5で評価）
                
                企画のバリエーション：
                - トレンド系（{generation_count//5}個）
                - オリジナル系（{generation_count//5}個）
                - リアクション系（{generation_count//5}個）
                - 教育・豆知識系（{generation_count//5}個）
                - チャレンジ系（{generation_count//5}個）
                
                各企画は60秒以内で完結し、モバイル縦画面に最適化された内容にしてください。
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['shorts_plans'] = result
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### 生成されたShorts企画")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.workflow_step = 1
                st.rerun()
        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                if 'shorts_plans' in st.session_state.current_data:
                    st.session_state.workflow_step = 3
                    st.rerun()
                else:
                    st.error("企画生成を実行してください")
                    
    elif st.session_state.workflow_step == 3:
        # Step 4: ランキング評価
        st.markdown("### Step 4: 企画ランキング評価")
        
        if st.button("ランキング評価実行", type="primary"):
            with st.spinner("企画をランキング評価中..."):
                prompt = f"""
                生成された企画: {st.session_state.current_data.get('shorts_plans')}
                チャンネル情報: {st.session_state.current_data.get('channel_name')}
                ターゲット: {st.session_state.current_data.get('target_age')} - {st.session_state.current_data.get('content_style')}
                
                全企画を以下の基準で評価し、TOP20をランキングしてください：
                
                評価基準（各20点満点、合計100点）：
                1. フック力: 最初の3秒で視聴者を掴む力
                2. 完視聴率: 最後まで見たくなる構成力
                3. バイラル性: シェア・拡散されやすさ
                4. 制作容易性: 撮影・編集の手軽さ
                5. 独自性: 他にない新しさ・面白さ
                
                各企画について：
                - 総合スコア（100点満点）
                - 各項目の詳細評価
                - 想定される視聴者反応
                - 改善提案
                
                TOP20の企画について：
                1. 詳細なランキング（1位〜20位）
                2. カテゴリー別ベスト3
                3. 制作優先順位の提案
                4. シリーズ化できる企画の組み合わせ
                5. 初心者でも作れるTOP5
                6. バズる可能性が最も高いTOP5
                
                最後に、選ばれたTOP20を使った1ヶ月の投稿スケジュール案も提示してください。
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['ranking_evaluation'] = result
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### ランキング評価結果")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.success("✅ Shorts企画生成が完了しました！")
                
                # エクスポート
                if st.button("結果をダウンロード", type="secondary"):
                    result_text = f"""
YouTube Shorts企画生成結果
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

【基本情報】
テーマ: {st.session_state.current_data.get('shorts_theme')}
キーワード: {st.session_state.current_data.get('target_keywords')}
チャンネル: {st.session_state.current_data.get('channel_name')}
ターゲット: {st.session_state.current_data.get('target_age')}
スタイル: {st.session_state.current_data.get('content_style')}

【市場分析】
{st.session_state.current_data.get('market_analysis')}

【生成された企画】
{st.session_state.current_data.get('shorts_plans')}

【ランキング評価】
{st.session_state.current_data.get('ranking_evaluation')}
"""
                    st.download_button(
                        label="テキストファイルをダウンロード",
                        data=result_text,
                        file_name=f"shorts_planning_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )
        
        if st.button("← 戻る", use_container_width=True):
            st.session_state.workflow_step = 2
            st.rerun()

def handle_shorts_script_workflow(app: YouTubeWorkflowApp):
    """Shorts台本生成ワークフロー"""
    if st.session_state.workflow_step == 0:
        # Step 1: 企画入力
        st.markdown("### Step 1: Shorts企画情報入力")
        
        video_concept = st.text_area(
            "動画企画・コンセプト",
            height=100,
            value=st.session_state.current_data.get("video_concept", ""),
            placeholder="例：料理の時短テクニックを30秒で紹介する動画"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            video_title = st.text_input("動画タイトル（30文字以内）", value=st.session_state.current_data.get("video_title", ""))
            target_duration = st.selectbox(
                "目標尺数",
                ["15秒", "30秒", "45秒", "60秒"],
                index=1 if not st.session_state.current_data.get("target_duration") else 
                      ["15秒", "30秒", "45秒", "60秒"].index(st.session_state.current_data.get("target_duration"))
            )
        
        with col2:
            video_style = st.selectbox(
                "動画スタイル",
                ["解説系", "実演系", "ストーリー系", "クイズ系", "比較系", "リアクション系"],
                index=0 if not st.session_state.current_data.get("video_style") else 
                      ["解説系", "実演系", "ストーリー系", "クイズ系", "比較系", "リアクション系"].index(st.session_state.current_data.get("video_style"))
            )
            hook_type = st.selectbox(
                "フックのタイプ",
                ["質問型", "衝撃事実型", "ビフォーアフター型", "共感型", "予告型"],
                index=0 if not st.session_state.current_data.get("hook_type") else 
                      ["質問型", "衝撃事実型", "ビフォーアフター型", "共感型", "予告型"].index(st.session_state.current_data.get("hook_type"))
            )
        
        target_emotion = st.multiselect(
            "狙う感情反応",
            ["驚き", "笑い", "感動", "共感", "好奇心", "満足感"],
            default=st.session_state.current_data.get("target_emotion", ["驚き"])
        )
        
        if st.button("次へ →", type="primary", use_container_width=True):
            if video_concept and video_title:
                data = {
                    "video_concept": video_concept,
                    "video_title": video_title,
                    "target_duration": target_duration,
                    "video_style": video_style,
                    "hook_type": hook_type,
                    "target_emotion": target_emotion
                }
                app.save_to_history("shorts_script", data)
                st.session_state.workflow_step = 1
                st.rerun()
            else:
                st.error("必須項目を入力してください")
                
    elif st.session_state.workflow_step == 1:
        # Step 2: リサーチ
        st.markdown("### Step 2: トレンドリサーチ")
        
        research_keywords = st.text_input(
            "リサーチキーワード",
            value=st.session_state.current_data.get("research_keywords", st.session_state.current_data.get("video_title", ""))
        )
        
        if st.button("リサーチ実行", type="primary"):
            with st.spinner("最新トレンドをリサーチ中..."):
                prompt = f"""
                Shorts企画: {st.session_state.current_data.get('video_concept')}
                タイトル: {st.session_state.current_data.get('video_title')}
                スタイル: {st.session_state.current_data.get('video_style')}
                キーワード: {research_keywords}
                
                以下のリサーチを実施してください：
                
                1. 現在のトレンド分析
                   - 類似コンテンツの人気要素
                   - バズっているフォーマット
                   - 効果的な演出パターン
                   - 人気の音楽・効果音
                
                2. 視聴者心理分析
                   - このジャンルの視聴動機
                   - 期待される感情体験
                   - シェアしたくなる要素
                   - コメントを誘発する要素
                
                3. 成功事例の分析
                   - 冒頭3秒の構成パターン
                   - 中盤の展開テクニック
                   - 締めの演出方法
                   - 視聴維持率を高める工夫
                
                4. 差別化戦略
                   - 新しい切り口の提案
                   - 独自性を出す演出案
                   - 記憶に残る要素
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['trend_research'] = result
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### リサーチ結果")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.workflow_step = 0
                st.rerun()
        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                if 'trend_research' in st.session_state.current_data:
                    st.session_state.workflow_step = 2
                    st.rerun()
                else:
                    st.error("リサーチを実行してください")
                    
    elif st.session_state.workflow_step == 2:
        # Step 3: 台本生成
        st.markdown("### Step 3: 詳細台本生成")
        
        generation_style = st.radio(
            "台本の詳細度",
            ["標準版（基本構成）", "詳細版（セリフ付き）", "完全版（演出指示付き）"],
            index=1
        )
        
        if st.button("台本生成実行", type="primary"):
            with st.spinner("台本を生成中..."):
                prompt = f"""
                企画情報:
                - コンセプト: {st.session_state.current_data.get('video_concept')}
                - タイトル: {st.session_state.current_data.get('video_title')}
                - 尺: {st.session_state.current_data.get('target_duration')}
                - スタイル: {st.session_state.current_data.get('video_style')}
                - フック: {st.session_state.current_data.get('hook_type')}
                - 狙う感情: {st.session_state.current_data.get('target_emotion')}
                
                リサーチ結果: {st.session_state.current_data.get('trend_research')}
                
                {generation_style}の台本を作成してください。
                
                台本構成：
                1. タイムコード付き構成表
                   - 0-3秒: フック部分
                   - 4-{st.session_state.current_data.get('target_duration')[:-1]}秒: メインコンテンツ
                   - ラスト2秒: 締め・CTA
                
                2. 詳細な内容
                   - 各シーンの具体的な内容
                   - {"セリフ・ナレーション" if "詳細版" in generation_style or "完全版" in generation_style else "アクションの説明"}
                   - {"カメラワーク・演出指示" if "完全版" in generation_style else ""}
                   - 使用する音楽・効果音
                   - テロップ・字幕の内容とタイミング
                
                3. 撮影・編集のポイント
                   - 必要な機材・小道具
                   - 撮影時の注意点
                   - 編集時のコツ
                   - 推奨するエフェクト
                
                4. 視聴者エンゲージメント戦略
                   - コメントを誘発する仕掛け
                   - 最後まで見たくなる工夫
                   - シェアしたくなる要素
                   - 次の動画への導線
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['script'] = result
                st.session_state.current_data['script_style'] = generation_style
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### 生成された台本")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.workflow_step = 1
                st.rerun()
        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                if 'script' in st.session_state.current_data:
                    st.session_state.workflow_step = 3
                    st.rerun()
                else:
                    st.error("台本生成を実行してください")
                    
    elif st.session_state.workflow_step == 3:
        # Step 4: 最適化
        st.markdown("### Step 4: 台本の最適化")
        
        optimization_focus = st.multiselect(
            "最適化の焦点",
            ["視聴維持率向上", "バイラル性強化", "エンゲージメント向上", "制作効率化", "ブランディング強化"],
            default=["視聴維持率向上", "バイラル性強化"]
        )
        
        if st.button("最適化実行", type="primary"):
            with st.spinner("台本を最適化中..."):
                prompt = f"""
                生成された台本: {st.session_state.current_data.get('script')}
                最適化の焦点: {optimization_focus}
                
                以下の観点で台本を最適化してください：
                
                1. 構成の最適化
                   - 各パートの時間配分の調整案
                   - より効果的な順序の提案
                   - 不要な部分の削除提案
                   - 追加すべき要素の提案
                
                2. {"視聴維持率向上" if "視聴維持率向上" in optimization_focus else ""}
                   {"- 冒頭3秒の改善案（3パターン）" if "視聴維持率向上" in optimization_focus else ""}
                   {"- 中だるみ防止の工夫" if "視聴維持率向上" in optimization_focus else ""}
                   {"- ラストまで見たくなる仕掛け" if "視聴維持率向上" in optimization_focus else ""}
                
                3. {"バイラル性強化" if "バイラル性強化" in optimization_focus else ""}
                   {"- シェアしたくなる要素の追加" if "バイラル性強化" in optimization_focus else ""}
                   {"- 話題になりやすい演出" if "バイラル性強化" in optimization_focus else ""}
                   {"- ミーム化しやすい要素" if "バイラル性強化" in optimization_focus else ""}
                
                4. 最終チェックリスト
                   - [ ] フックは3秒以内に完了するか
                   - [ ] 尺は目標時間内に収まるか
                   - [ ] CTAは明確か
                   - [ ] 音楽・効果音は適切か
                   - [ ] テロップは読みやすいか
                
                5. 完成版台本
                   - 最適化を反映した最終台本
                   - タイムコード付き
                   - 制作時の具体的な指示
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['optimized_script'] = result
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### 最適化された台本")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.success("✅ Shorts台本生成が完了しました！")
                
                # エクスポート
                if st.button("結果をダウンロード", type="secondary"):
                    result_text = f"""
YouTube Shorts台本
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

【企画情報】
コンセプト: {st.session_state.current_data.get('video_concept')}
タイトル: {st.session_state.current_data.get('video_title')}
尺: {st.session_state.current_data.get('target_duration')}
スタイル: {st.session_state.current_data.get('video_style')}

【トレンドリサーチ】
{st.session_state.current_data.get('trend_research')}

【生成された台本】
{st.session_state.current_data.get('script')}

【最適化された台本】
{st.session_state.current_data.get('optimized_script')}
"""
                    st.download_button(
                        label="テキストファイルをダウンロード",
                        data=result_text,
                        file_name=f"shorts_script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )
        
        if st.button("← 戻る", use_container_width=True):
            st.session_state.workflow_step = 2
            st.rerun()

def handle_content_scoring_workflow(app: YouTubeWorkflowApp):
    """コンテンツスコアリングワークフロー"""
    if st.session_state.workflow_step == 0:
        # Step 1: コンテンツ入力
        st.markdown("### Step 1: 評価対象コンテンツ入力")
        
        content_type = st.radio(
            "評価対象",
            ["新規投稿（予定）", "既存動画"],
            index=0
        )
        
        col1, col2 = st.columns(2)
        with col1:
            video_title = st.text_input("動画タイトル", value=st.session_state.current_data.get("video_title", ""))
            thumbnail_text = st.text_input("サムネイル文言", value=st.session_state.current_data.get("thumbnail_text", ""))
            channel_name = st.text_input("チャンネル名", value=st.session_state.current_data.get("channel_name", ""))
        
        with col2:
            video_category = st.selectbox(
                "動画カテゴリー",
                ["エンターテインメント", "教育", "ゲーム", "音楽", "ハウツー", "ニュース", "スポーツ", "その他"],
                index=0 if not st.session_state.current_data.get("video_category") else 
                      ["エンターテインメント", "教育", "ゲーム", "音楽", "ハウツー", "ニュース", "スポーツ", "その他"].index(st.session_state.current_data.get("video_category"))
            )
            target_keywords = st.text_input("ターゲットキーワード", value=st.session_state.current_data.get("target_keywords", ""))
        
        video_description = st.text_area(
            "動画説明文",
            height=150,
            value=st.session_state.current_data.get("video_description", ""),
            placeholder="動画の説明文を入力してください（最初の125文字が特に重要）"
        )
        
        tags = st.text_area(
            "タグ（カンマ区切り）",
            value=st.session_state.current_data.get("tags", ""),
            placeholder="タグ1, タグ2, タグ3..."
        )
        
        if content_type == "既存動画":
            st.markdown("#### 既存動画の追加情報")
            col3, col4 = st.columns(2)
            with col3:
                video_url = st.text_input("動画URL", value=st.session_state.current_data.get("video_url", ""))
                view_count = st.number_input("現在の視聴回数", min_value=0, value=st.session_state.current_data.get("view_count", 0))
            with col4:
                upload_date = st.date_input("公開日")
                ctr = st.number_input("クリック率（%）", min_value=0.0, max_value=100.0, value=st.session_state.current_data.get("ctr", 0.0))
        
        if st.button("次へ →", type="primary", use_container_width=True):
            if video_title and video_description:
                data = {
                    "content_type": content_type,
                    "video_title": video_title,
                    "thumbnail_text": thumbnail_text,
                    "channel_name": channel_name,
                    "video_category": video_category,
                    "target_keywords": target_keywords,
                    "video_description": video_description,
                    "tags": tags
                }
                if content_type == "既存動画":
                    data.update({
                        "video_url": video_url,
                        "view_count": view_count,
                        "upload_date": str(upload_date),
                        "ctr": ctr
                    })
                app.save_to_history("content_scoring", data)
                st.session_state.workflow_step = 1
                st.rerun()
            else:
                st.error("必須項目を入力してください")
                
    elif st.session_state.workflow_step == 1:
        # Step 2: ペルソナ分析
        st.markdown("### Step 2: ターゲットペルソナ分析")
        
        persona_input = st.text_area(
            "想定視聴者層（任意）",
            value=st.session_state.current_data.get("persona_input", ""),
            placeholder="例：20代男性、ゲーム好き、エンタメ系動画をよく見る"
        )
        
        if st.button("ペルソナ分析実行", type="primary"):
            with st.spinner("ペルソナを分析中..."):
                prompt = f"""
                動画情報:
                - タイトル: {st.session_state.current_data.get('video_title')}
                - カテゴリー: {st.session_state.current_data.get('video_category')}
                - キーワード: {st.session_state.current_data.get('target_keywords')}
                - 説明文: {st.session_state.current_data.get('video_description')}
                - 想定視聴者: {persona_input}
                
                この動画のターゲットペルソナを分析してください：
                
                1. メインペルソナ（最も視聴する可能性が高い層）
                   - 年齢・性別
                   - 興味関心
                   - YouTube利用パターン
                   - この動画を見る動機
                   - 期待する価値
                
                2. サブペルソナ（2番目に重要な層）
                   - 同様の分析
                
                3. ペルソナに響く要素
                   - タイトルの訴求力
                   - サムネイルの効果
                   - 説明文の適切性
                   - タグの最適性
                
                4. ペルソナとのミスマッチ
                   - 現在の要素で響きにくい点
                   - 改善が必要な部分
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['persona_analysis'] = result
                st.session_state.current_data['persona_input'] = persona_input
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### ペルソナ分析結果")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.workflow_step = 0
                st.rerun()
        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                if 'persona_analysis' in st.session_state.current_data:
                    st.session_state.workflow_step = 2
                    st.rerun()
                else:
                    st.error("ペルソナ分析を実行してください")
                    
    elif st.session_state.workflow_step == 2:
        # Step 3: 評価実施
        st.markdown("### Step 3: コンテンツスコアリング実施")
        
        evaluation_criteria = st.multiselect(
            "評価項目（複数選択可）",
            ["SEO最適化", "クリック率予測", "視聴維持率予測", "エンゲージメント予測", "バイラル性", "ブランド適合性"],
            default=["SEO最適化", "クリック率予測", "視聴維持率予測"]
        )
        
        if st.button("スコアリング実行", type="primary"):
            with st.spinner("コンテンツを評価中..."):
                prompt = f"""
                評価対象コンテンツ:
                - タイトル: {st.session_state.current_data.get('video_title')}
                - サムネイル文言: {st.session_state.current_data.get('thumbnail_text')}
                - 説明文: {st.session_state.current_data.get('video_description')}
                - タグ: {st.session_state.current_data.get('tags')}
                - カテゴリー: {st.session_state.current_data.get('video_category')}
                
                ペルソナ分析: {st.session_state.current_data.get('persona_analysis')}
                評価項目: {evaluation_criteria}
                
                以下の観点で詳細なスコアリングを実施してください：
                
                1. 総合評価（100点満点）
                   - 総合スコアと評価
                   - 強みと弱み
                
                2. {"SEO最適化（20点満点）" if "SEO最適化" in evaluation_criteria else ""}
                   {"- キーワード配置の適切性" if "SEO最適化" in evaluation_criteria else ""}
                   {"- タイトルの最適化度" if "SEO最適化" in evaluation_criteria else ""}
                   {"- 説明文の構造" if "SEO最適化" in evaluation_criteria else ""}
                   {"- タグの効果性" if "SEO最適化" in evaluation_criteria else ""}
                
                3. {"クリック率予測（20点満点）" if "クリック率予測" in evaluation_criteria else ""}
                   {"- タイトルの魅力度" if "クリック率予測" in evaluation_criteria else ""}
                   {"- サムネイル文言の効果" if "クリック率予測" in evaluation_criteria else ""}
                   {"- 予想CTR: X.X%" if "クリック率予測" in evaluation_criteria else ""}
                
                4. {"視聴維持率予測（20点満点）" if "視聴維持率予測" in evaluation_criteria else ""}
                   {"- タイトルと内容の一致度" if "視聴維持率予測" in evaluation_criteria else ""}
                   {"- 期待値の管理" if "視聴維持率予測" in evaluation_criteria else ""}
                   {"- 予想視聴維持率: XX%" if "視聴維持率予測" in evaluation_criteria else ""}
                
                5. {"エンゲージメント予測（20点満点）" if "エンゲージメント予測" in evaluation_criteria else ""}
                   {"- コメント誘発度" if "エンゲージメント予測" in evaluation_criteria else ""}
                   {"- いいね率予測" if "エンゲージメント予測" in evaluation_criteria else ""}
                   {"- シェア可能性" if "エンゲージメント予測" in evaluation_criteria else ""}
                
                6. 競合比較分析
                   - 同カテゴリーでの優位性
                   - 差別化ポイント
                   - 不足している要素
                
                7. 視覚的スコアカード
                   各項目を★5段階で評価してください
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['scoring_result'] = result
                st.session_state.current_data['evaluation_criteria'] = evaluation_criteria
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### スコアリング結果")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.workflow_step = 1
                st.rerun()
        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                if 'scoring_result' in st.session_state.current_data:
                    st.session_state.workflow_step = 3
                    st.rerun()
                else:
                    st.error("スコアリングを実行してください")
                    
    elif st.session_state.workflow_step == 3:
        # Step 4: 改善提案
        st.markdown("### Step 4: 改善提案とアクションプラン")
        
        improvement_priority = st.radio(
            "改善の優先度",
            ["即効性重視（簡単な修正）", "効果重視（大幅な改善）", "バランス型"],
            index=2
        )
        
        if st.button("改善提案生成", type="primary"):
            with st.spinner("改善提案を生成中..."):
                prompt = f"""
                現在のコンテンツ:
                - タイトル: {st.session_state.current_data.get('video_title')}
                - サムネイル文言: {st.session_state.current_data.get('thumbnail_text')}
                - 説明文: {st.session_state.current_data.get('video_description')}
                - タグ: {st.session_state.current_data.get('tags')}
                
                スコアリング結果: {st.session_state.current_data.get('scoring_result')}
                改善優先度: {improvement_priority}
                
                以下の改善提案を提供してください：
                
                1. タイトル改善案（5パターン）
                   - 現在: {st.session_state.current_data.get('video_title')}
                   - 改善案1〜5（各案の狙いも説明）
                   - 推奨度ランキング
                
                2. サムネイル文言改善案（5パターン）
                   - 現在: {st.session_state.current_data.get('thumbnail_text')}
                   - 改善案1〜5（インパクト重視）
                   - 各案の予想CTR向上率
                
                3. 説明文最適化案
                   - 最初の125文字の改善案（3パターン）
                   - SEO強化ポイント
                   - CTA配置の提案
                   - 関連動画への誘導文
                
                4. タグ最適化
                   - 追加すべきタグ（10個）
                   - 削除を検討すべきタグ
                   - タグの優先順位
                
                5. 総合的な改善ロードマップ
                   - 即実施すべき改善（24時間以内）
                   - 短期改善（1週間以内）
                   - 中期改善（1ヶ月以内）
                
                6. 期待される改善効果
                   - 各改善による予想スコア向上
                   - CTR向上予測
                   - 視聴回数への影響予測
                
                7. A/Bテスト提案
                   - テストすべき要素
                   - 測定方法
                   - 判断基準
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['improvement_suggestions'] = result
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### 改善提案")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.success("✅ コンテンツスコアリングが完了しました！")
                
                # エクスポート
                if st.button("結果をダウンロード", type="secondary"):
                    result_text = f"""
コンテンツスコアリング結果
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

【評価対象コンテンツ】
タイトル: {st.session_state.current_data.get('video_title')}
サムネイル: {st.session_state.current_data.get('thumbnail_text')}
カテゴリー: {st.session_state.current_data.get('video_category')}
キーワード: {st.session_state.current_data.get('target_keywords')}

【説明文】
{st.session_state.current_data.get('video_description')}

【タグ】
{st.session_state.current_data.get('tags')}

【ペルソナ分析】
{st.session_state.current_data.get('persona_analysis')}

【スコアリング結果】
{st.session_state.current_data.get('scoring_result')}

【改善提案】
{st.session_state.current_data.get('improvement_suggestions')}
"""
                    st.download_button(
                        label="テキストファイルをダウンロード",
                        data=result_text,
                        file_name=f"content_scoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )
        
        if st.button("← 戻る", use_container_width=True):
            st.session_state.workflow_step = 2
            st.rerun()

def handle_keyword_strategy_workflow(app: YouTubeWorkflowApp):
    """キーワード戦略ワークフロー"""
    if st.session_state.workflow_step == 0:
        # Step 1: 初期情報入力
        st.markdown("### Step 1: チャンネル・ビジネス情報入力")
        
        col1, col2 = st.columns(2)
        with col1:
            channel_name = st.text_input("チャンネル名", value=st.session_state.current_data.get("channel_name", ""))
            business_category = st.text_input("ビジネスカテゴリー/業界", value=st.session_state.current_data.get("business_category", ""))
            main_product = st.text_input("主要商品・サービス", value=st.session_state.current_data.get("main_product", ""))
        
        with col2:
            target_audience = st.text_area("ターゲットオーディエンス", value=st.session_state.current_data.get("target_audience", ""))
            competitors = st.text_area("主要競合（カンマ区切り）", value=st.session_state.current_data.get("competitors", ""))
        
        channel_goals = st.multiselect(
            "チャンネル目標",
            ["ブランド認知向上", "リード獲得", "販売促進", "教育・啓蒙", "コミュニティ構築", "収益化"],
            default=st.session_state.current_data.get("channel_goals", ["ブランド認知向上"])
        )
        
        current_status = st.text_area(
            "現在のチャンネル状況（任意）",
            value=st.session_state.current_data.get("current_status", ""),
            placeholder="登録者数、平均視聴回数、主力コンテンツなど"
        )
        
        if st.button("次へ →", type="primary", use_container_width=True):
            if channel_name and business_category and main_product:
                data = {
                    "channel_name": channel_name,
                    "business_category": business_category,
                    "main_product": main_product,
                    "target_audience": target_audience,
                    "competitors": competitors,
                    "channel_goals": channel_goals,
                    "current_status": current_status
                }
                app.save_to_history("keyword_strategy", data)
                st.session_state.workflow_step = 1
                st.rerun()
            else:
                st.error("必須項目を入力してください")
                
    elif st.session_state.workflow_step == 1:
        # Step 2: キーワード収集
        st.markdown("### Step 2: キーワード収集と分析")
        
        seed_keywords = st.text_area(
            "シードキーワード（カンマ区切り）",
            value=st.session_state.current_data.get("seed_keywords", ""),
            placeholder="基本となるキーワードを入力（例：料理レシピ, 簡単料理, 時短料理）"
        )
        
        keyword_sources = st.multiselect(
            "キーワード収集ソース",
            ["YouTube検索", "Google検索", "競合分析", "トレンド分析", "関連キーワード"],
            default=["YouTube検索", "関連キーワード"]
        )
        
        if st.button("キーワード収集実行", type="primary"):
            with st.spinner("キーワードを収集・分析中..."):
                # 各シードキーワードでキーワード収集
                all_keywords = []
                seed_list = [k.strip() for k in seed_keywords.split(",") if k.strip()]
                
                for seed in seed_list[:3]:  # 最初の3つのシードキーワード
                    keywords = app.get_keywords(seed)
                    all_keywords.extend(keywords)
                
                prompt = f"""
                ビジネス情報:
                - カテゴリー: {st.session_state.current_data.get('business_category')}
                - 商品: {st.session_state.current_data.get('main_product')}
                - ターゲット: {st.session_state.current_data.get('target_audience')}
                - 目標: {st.session_state.current_data.get('channel_goals')}
                
                シードキーワード: {seed_keywords}
                収集されたキーワード: {json.dumps(all_keywords[:30], ensure_ascii=False, indent=2)}
                
                以下の分析を実施してください：
                
                1. キーワード分類
                   - カテゴリー別に分類（購買意欲、情報収集、エンタメなど）
                   - 検索意図による分類
                   - コンテンツタイプ別分類
                
                2. キーワード価値評価
                   - 各キーワードのビジネス価値（高/中/低）
                   - 競合性分析
                   - 成長性予測
                   - ROI予測
                
                3. キーワードギャップ分析
                   - 未開拓の有望キーワード
                   - ニッチだが高価値なキーワード
                   - ロングテールキーワードの機会
                
                4. 季節性・トレンド分析
                   - 季節変動のあるキーワード
                   - 急成長キーワード
                   - 将来性のあるキーワード
                
                5. 競合キーワード分析
                   - 競合が狙っているキーワード
                   - 競合が見落としているキーワード
                   - 差別化可能なキーワード
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['keyword_analysis'] = result
                st.session_state.current_data['seed_keywords'] = seed_keywords
                st.session_state.current_data['collected_keywords'] = all_keywords[:30]
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### キーワード分析結果")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # キーワードビジュアライゼーション
                if all_keywords:
                    df = pd.DataFrame(all_keywords[:20])
                    
                    # バブルチャート
                    fig = px.scatter(df, x='search_volume', y='competition', 
                                    size='search_volume', text='keyword',
                                    title='キーワードポートフォリオ（検索ボリューム vs 競合性）',
                                    labels={'search_volume': '月間検索数', 'competition': '競合性'},
                                    color='competition',
                                    color_continuous_scale='RdYlGn_r')
                    fig.update_traces(textposition='top center')
                    st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.workflow_step = 0
                st.rerun()
        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                if 'keyword_analysis' in st.session_state.current_data:
                    st.session_state.workflow_step = 2
                    st.rerun()
                else:
                    st.error("キーワード収集を実行してください")
                    
    elif st.session_state.workflow_step == 2:
        # Step 3: 評価分析
        st.markdown("### Step 3: 戦略評価とシミュレーション")
        
        strategy_focus = st.multiselect(
            "戦略の焦点",
            ["短期的成果重視", "長期的成長重視", "ニッチ市場開拓", "競合差別化", "ブランディング強化"],
            default=["長期的成長重視", "競合差別化"]
        )
        
        content_frequency = st.selectbox(
            "想定投稿頻度",
            ["毎日", "週3-4回", "週2回", "週1回", "月2-3回"],
            index=2
        )
        
        resource_level = st.radio(
            "リソースレベル",
            ["限定的（個人運営）", "中規模（小チーム）", "充実（専門チーム）"],
            index=0
        )
        
        if st.button("戦略シミュレーション実行", type="primary"):
            with st.spinner("戦略をシミュレーション中..."):
                prompt = f"""
                キーワード分析: {st.session_state.current_data.get('keyword_analysis')}
                戦略の焦点: {strategy_focus}
                投稿頻度: {content_frequency}
                リソース: {resource_level}
                
                以下の戦略シミュレーションを実施してください：
                
                1. 推奨キーワード戦略
                   - コアキーワード（5個）: 中心となるキーワード
                   - サポートキーワード（10個）: 補完的なキーワード
                   - ロングテールキーワード（20個）: ニッチ攻略用
                   
                2. フェーズ別実行計画
                   - Phase 1（1-3ヶ月）: 基盤構築期
                     * 狙うキーワード
                     * コンテンツ計画
                     * 期待される成果
                   
                   - Phase 2（4-6ヶ月）: 成長期
                     * 拡張キーワード
                     * スケールアップ戦略
                     * 目標指標
                   
                   - Phase 3（7-12ヶ月）: 確立期
                     * 権威性構築
                     * ブランドキーワード
                     * 収益化戦略
                
                3. コンテンツマトリックス
                   - キーワード×コンテンツタイプのマトリックス
                   - 各組み合わせの優先順位
                   - 制作効率の最適化案
                
                4. KPI予測
                   - 3ヶ月後の予想成果
                   - 6ヶ月後の予想成果
                   - 12ヶ月後の予想成果
                   - 各指標（視聴回数、登録者数、エンゲージメント率）
                
                5. リスクと対策
                   - 想定されるリスク
                   - 対応策
                   - 代替戦略
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['strategy_simulation'] = result
                st.session_state.current_data['strategy_focus'] = strategy_focus
                st.session_state.current_data['content_frequency'] = content_frequency
                st.session_state.current_data['resource_level'] = resource_level
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### 戦略シミュレーション結果")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.workflow_step = 1
                st.rerun()
        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                if 'strategy_simulation' in st.session_state.current_data:
                    st.session_state.workflow_step = 3
                    st.rerun()
                else:
                    st.error("戦略シミュレーションを実行してください")
                    
    elif st.session_state.workflow_step == 3:
        # Step 4: 戦略提案
        st.markdown("### Step 4: 最終戦略提案とアクションプラン")
        
        if st.button("最終戦略提案生成", type="primary"):
            with st.spinner("最終戦略を策定中..."):
                prompt = f"""
                全体情報:
                - ビジネス: {st.session_state.current_data.get('business_category')} - {st.session_state.current_data.get('main_product')}
                - 目標: {st.session_state.current_data.get('channel_goals')}
                - 現状: {st.session_state.current_data.get('current_status')}
                
                分析結果:
                - キーワード分析: {st.session_state.current_data.get('keyword_analysis')}
                - 戦略シミュレーション: {st.session_state.current_data.get('strategy_simulation')}
                
                以下の包括的な戦略提案を作成してください：
                
                1. エグゼクティブサマリー
                   - 戦略の核心（3行以内）
                   - 期待される成果
                   - 必要な投資
                
                2. キーワード戦略マスタープラン
                   - 優先キーワードリスト（TOP30）
                   - 各キーワードの役割と狙い
                   - キーワード間の相乗効果
                
                3. コンテンツカレンダー（最初の3ヶ月）
                   - 月別テーマ設定
                   - 週次コンテンツ計画
                   - キーワード配分
                   - 特別企画・キャンペーン
                
                4. 実行チェックリスト
                   - [ ] 週次タスク
                   - [ ] 月次タスク
                   - [ ] 四半期レビュー項目
                
                5. 成功指標とモニタリング
                   - 追跡すべきKPI
                   - レポートテンプレート
                   - 改善サイクル
                
                6. ツールと自動化
                   - 推奨ツール
                   - 効率化のヒント
                   - テンプレート活用
                
                7. 予算配分案
                   - コンテンツ制作
                   - プロモーション
                   - ツール・サービス
                
                8. 次のステップ（具体的アクション）
                   - 今日やること
                   - 今週やること
                   - 今月やること
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['final_strategy'] = result
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### 最終戦略提案")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.success("✅ キーワード戦略シミュレーションが完了しました！")
                
                # エクスポート
                if st.button("結果をダウンロード", type="secondary"):
                    result_text = f"""
YouTubeキーワード戦略
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

【基本情報】
チャンネル名: {st.session_state.current_data.get('channel_name')}
ビジネスカテゴリー: {st.session_state.current_data.get('business_category')}
主要商品: {st.session_state.current_data.get('main_product')}
ターゲット: {st.session_state.current_data.get('target_audience')}
目標: {st.session_state.current_data.get('channel_goals')}

【キーワード分析】
{st.session_state.current_data.get('keyword_analysis')}

【戦略シミュレーション】
{st.session_state.current_data.get('strategy_simulation')}

【最終戦略提案】
{st.session_state.current_data.get('final_strategy')}
"""
                    st.download_button(
                        label="テキストファイルをダウンロード",
                        data=result_text,
                        file_name=f"keyword_strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )
        
        if st.button("← 戻る", use_container_width=True):
            st.session_state.workflow_step = 2
            st.rerun()

def handle_long_content_workflow(app: YouTubeWorkflowApp):
    """長尺動画台本生成ワークフロー"""
    if st.session_state.workflow_step == 0:
        # Step 1: スタイル選択
        st.markdown("### Step 1: 動画スタイルと基本情報")
        
        content_style = st.selectbox(
            "動画スタイル",
            ["解説・教育系", "エンターテインメント系", "ドキュメンタリー系", "対談・インタビュー系", 
             "レビュー・批評系", "ハウツー・チュートリアル系", "Vlog・日常系", "ストーリーテリング系"],
            index=0 if not st.session_state.current_data.get("content_style") else 
                  ["解説・教育系", "エンターテインメント系", "ドキュメンタリー系", "対談・インタビュー系", 
                   "レビュー・批評系", "ハウツー・チュートリアル系", "Vlog・日常系", "ストーリーテリング系"].index(st.session_state.current_data.get("content_style"))
        )
        
        col1, col2 = st.columns(2)
        with col1:
            video_title = st.text_input("動画タイトル", value=st.session_state.current_data.get("video_title", ""))
            target_duration = st.selectbox(
                "目標尺数",
                ["5-10分", "10-15分", "15-20分", "20-30分", "30分以上"],
                index=1 if not st.session_state.current_data.get("target_duration") else 
                      ["5-10分", "10-15分", "15-20分", "20-30分", "30分以上"].index(st.session_state.current_data.get("target_duration"))
            )
            channel_name = st.text_input("チャンネル名", value=st.session_state.current_data.get("channel_name", ""))
        
        with col2:
            target_audience = st.text_input("ターゲット視聴者", value=st.session_state.current_data.get("target_audience", ""))
            tone_style = st.selectbox(
                "トーン・話し方",
                ["フレンドリー・カジュアル", "プロフェッショナル・フォーマル", "エネルギッシュ・情熱的", 
                 "落ち着いた・知的", "ユーモラス・面白い", "感動的・エモーショナル"],
                index=0 if not st.session_state.current_data.get("tone_style") else 
                      ["フレンドリー・カジュアル", "プロフェッショナル・フォーマル", "エネルギッシュ・情熱的", 
                       "落ち着いた・知的", "ユーモラス・面白い", "感動的・エモーショナル"].index(st.session_state.current_data.get("tone_style"))
            )
        
        special_requirements = st.multiselect(
            "特別な要件",
            ["スポンサー紹介あり", "商品紹介あり", "CTA重視", "教育的価値重視", "エンタメ性重視", "SEO最適化"],
            default=st.session_state.current_data.get("special_requirements", [])
        )
        
        if st.button("次へ →", type="primary", use_container_width=True):
            if video_title and channel_name:
                data = {
                    "content_style": content_style,
                    "video_title": video_title,
                    "target_duration": target_duration,
                    "channel_name": channel_name,
                    "target_audience": target_audience,
                    "tone_style": tone_style,
                    "special_requirements": special_requirements
                }
                app.save_to_history("long_content", data)
                st.session_state.workflow_step = 1
                st.rerun()
            else:
                st.error("必須項目を入力してください")
                
    elif st.session_state.workflow_step == 1:
        # Step 2: 情報入力
        st.markdown("### Step 2: 詳細情報入力")
        
        main_topic = st.text_area(
            "メイントピック・テーマ",
            height=100,
            value=st.session_state.current_data.get("main_topic", ""),
            placeholder="動画で扱うメインのトピックやテーマを詳しく説明してください"
        )
        
        key_points = st.text_area(
            "重要ポイント（箇条書き）",
            height=150,
            value=st.session_state.current_data.get("key_points", ""),
            placeholder="・ポイント1\n・ポイント2\n・ポイント3..."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            reference_materials = st.text_area(
                "参考資料・ソース（任意）",
                value=st.session_state.current_data.get("reference_materials", ""),
                placeholder="参考にする資料やソースがあれば記入"
            )
        
        with col2:
            call_to_action = st.text_area(
                "CTA（行動喚起）内容",
                value=st.session_state.current_data.get("call_to_action", ""),
                placeholder="視聴者に促したい行動（チャンネル登録、商品購入など）"
            )
        
        content_structure = st.radio(
            "希望する構成タイプ",
            ["標準構成（導入→本編→まとめ）", "問題提起型（問題→原因→解決策）", 
             "ストーリー型（起承転結）", "リスト型（TOP10など）", "比較型（A vs B）"],
            index=0
        )
        
        if st.button("次へ →", type="primary", use_container_width=True):
            if main_topic and key_points:
                data = {
                    "main_topic": main_topic,
                    "key_points": key_points,
                    "reference_materials": reference_materials,
                    "call_to_action": call_to_action,
                    "content_structure": content_structure
                }
                st.session_state.current_data.update(data)
                app.save_to_history("long_content", st.session_state.current_data)
                st.session_state.workflow_step = 2
                st.rerun()
            else:
                st.error("必須項目を入力してください")
        
        if st.button("← 戻る", use_container_width=True):
            st.session_state.workflow_step = 0
            st.rerun()
            
    elif st.session_state.workflow_step == 2:
        # Step 3: 台本生成
        st.markdown("### Step 3: 詳細台本生成")
        
        script_detail_level = st.radio(
            "台本の詳細度",
            ["構成案のみ", "基本台本（アウトライン）", "詳細台本（セリフ付き）", "完全台本（演出指示付き）"],
            index=2
        )
        
        include_options = st.multiselect(
            "含める要素",
            ["オープニングフック", "チャプター分け", "ビジュアル指示", "BGM・効果音指示", 
             "テロップ案", "カット割り", "B-roll提案"],
            default=["オープニングフック", "チャプター分け", "テロップ案"]
        )
        
        if st.button("台本生成実行", type="primary"):
            with st.spinner("台本を生成中..."):
                prompt = f"""
                動画情報:
                - スタイル: {st.session_state.current_data.get('content_style')}
                - タイトル: {st.session_state.current_data.get('video_title')}
                - 尺: {st.session_state.current_data.get('target_duration')}
                - トーン: {st.session_state.current_data.get('tone_style')}
                - 構成: {st.session_state.current_data.get('content_structure')}
                
                コンテンツ情報:
                - トピック: {st.session_state.current_data.get('main_topic')}
                - 重要ポイント: {st.session_state.current_data.get('key_points')}
                - 参考資料: {st.session_state.current_data.get('reference_materials')}
                - CTA: {st.session_state.current_data.get('call_to_action')}
                
                要件: {st.session_state.current_data.get('special_requirements')}
                詳細度: {script_detail_level}
                含める要素: {include_options}
                
                以下の形式で{st.session_state.current_data.get('target_duration')}の長尺動画台本を作成してください：
                
                1. 動画概要
                   - 一行サマリー
                   - 視聴者が得られる価値
                   - 差別化ポイント
                
                2. {"オープニング（0:00-0:30）" if "オープニングフック" in include_options else "オープニング"}
                   {"- フックとなる冒頭の一言/シーン" if "オープニングフック" in include_options else ""}
                   - 自己紹介/チャンネル紹介
                   - 今回の内容予告
                   {"- BGM指示" if "BGM・効果音指示" in include_options else ""}
                
                3. {"チャプター構成" if "チャプター分け" in include_options else "本編構成"}
                   {"- 各チャプターのタイムスタンプ" if "チャプター分け" in include_options else ""}
                   - 各セクションの内容
                   {"- セリフ/ナレーション" if "詳細台本" in script_detail_level or "完全台本" in script_detail_level else "- 話すポイント"}
                   {"- ビジュアル指示" if "ビジュアル指示" in include_options else ""}
                   {"- テロップ案" if "テロップ案" in include_options else ""}
                   {"- カメラワーク" if "カット割り" in include_options else ""}
                   {"- B-roll素材" if "B-roll提案" in include_options else ""}
                
                4. クライマックス/重要シーン
                   - 最も伝えたいメッセージ
                   - 感情的なピーク
                   {"- 演出指示" if "完全台本" in script_detail_level else ""}
                
                5. エンディング（ラスト1-2分）
                   - まとめ/要約
                   - CTA（{st.session_state.current_data.get('call_to_action')}）
                   - 次回予告/関連動画紹介
                   - エンドカード配置
                
                6. 制作メモ
                   - 撮影時の注意点
                   - 編集のポイント
                   - 必要な素材リスト
                   {"- 推奨BGM/効果音" if "BGM・効果音指示" in include_options else ""}
                
                7. SEO最適化要素
                   - 説明文の最初の125文字案
                   - 推奨タグ
                   - サムネイル案
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['script'] = result
                st.session_state.current_data['script_detail_level'] = script_detail_level
                st.session_state.current_data['include_options'] = include_options
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### 生成された台本")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.workflow_step = 1
                st.rerun()
        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                if 'script' in st.session_state.current_data:
                    st.session_state.workflow_step = 3
                    st.rerun()
                else:
                    st.error("台本生成を実行してください")
                    
    elif st.session_state.workflow_step == 3:
        # Step 4: 最適化
        st.markdown("### Step 4: 台本の最適化と仕上げ")
        
        optimization_focus = st.multiselect(
            "最適化の重点",
            ["視聴維持率向上", "エンゲージメント向上", "教育効果向上", "エンタメ性向上", 
             "感情的インパクト", "行動変容促進"],
            default=["視聴維持率向上", "エンゲージメント向上"]
        )
        
        revision_requests = st.text_area(
            "特別な修正要望（任意）",
            value="",
            placeholder="特定の部分を修正したい場合は詳細を記入"
        )
        
        if st.button("最適化実行", type="primary"):
            with st.spinner("台本を最適化中..."):
                prompt = f"""
                生成された台本: {st.session_state.current_data.get('script')}
                最適化の重点: {optimization_focus}
                修正要望: {revision_requests}
                
                以下の観点で台本を最適化してください：
                
                1. 構成の最適化
                   - 各セクションの時間配分の見直し
                   - より効果的な順序への組み替え提案
                   - 冗長な部分の削除
                   - 不足している要素の追加
                
                2. {"視聴維持率向上策" if "視聴維持率向上" in optimization_focus else ""}
                   {"- 離脱ポイントの予測と対策" if "視聴維持率向上" in optimization_focus else ""}
                   {"- パターンインタラプト（飽きさせない工夫）" if "視聴維持率向上" in optimization_focus else ""}
                   {"- 次が見たくなる展開" if "視聴維持率向上" in optimization_focus else ""}
                   {"- チャプタースキップ対策" if "視聴維持率向上" in optimization_focus else ""}
                
                3. {"エンゲージメント向上策" if "エンゲージメント向上" in optimization_focus else ""}
                   {"- コメントを誘発する質問・投げかけ" if "エンゲージメント向上" in optimization_focus else ""}
                   {"- 共感を生む要素" if "エンゲージメント向上" in optimization_focus else ""}
                   {"- シェアしたくなる瞬間" if "エンゲージメント向上" in optimization_focus else ""}
                
                4. 台本のブラッシュアップ
                   - より自然な話し方への調整
                   - 専門用語の適切な説明
                   - 例え話やアナロジーの追加
                   - 視覚的要素の強化
                
                5. タイミングとペース
                   - 各セクションの詳細なタイムライン
                   - 話すスピードの指示
                   - 間（ポーズ）の効果的な使い方
                   - BGMとの同期ポイント
                
                6. 最終チェックリスト
                   - [ ] オープニングは10秒以内にフックがあるか
                   - [ ] 各チャプターの冒頭は明確か
                   - [ ] CTAは自然に組み込まれているか
                   - [ ] エンディングは満足感があるか
                   - [ ] 全体の流れは論理的か
                
                7. 完成版台本
                   - 最適化を反映した最終台本
                   - プロンプター用テキスト（読みやすい形式）
                   - 編集者への指示書
                """
                
                result = app.generate_with_gemini(prompt)
                st.session_state.current_data['optimized_script'] = result
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown("#### 最適化された台本")
                st.write(result)
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.success("✅ 長尺動画台本生成が完了しました！")
                
                # エクスポート
                if st.button("結果をダウンロード", type="secondary"):
                    result_text = f"""
長尺動画台本
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

【動画情報】
スタイル: {st.session_state.current_data.get('content_style')}
タイトル: {st.session_state.current_data.get('video_title')}
尺: {st.session_state.current_data.get('target_duration')}
チャンネル: {st.session_state.current_data.get('channel_name')}

【コンテンツ詳細】
トピック: {st.session_state.current_data.get('main_topic')}
重要ポイント:
{st.session_state.current_data.get('key_points')}

CTA: {st.session_state.current_data.get('call_to_action')}

【生成された台本】
{st.session_state.current_data.get('script')}

【最適化された台本】
{st.session_state.current_data.get('optimized_script')}
"""
                    st.download_button(
                        label="テキストファイルをダウンロード",
                        data=result_text,
                        file_name=f"long_content_script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )
        
        if st.button("← 戻る", use_container_width=True):
            st.session_state.workflow_step = 2
            st.rerun()

if __name__ == "__main__":
    main()