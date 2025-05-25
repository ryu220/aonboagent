import streamlit as st
import google.generativeai as genai
from datetime import datetime
import json
import os
import re
from typing import Dict, List, Any, Optional, Tuple
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="YouTube AI Agent",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 近未来的なカスタムCSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Noto+Sans+JP:wght@300;400;700&display=swap');
    
    /* メインコンテナ */
    .main {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
        color: #ffffff;
    }
    
    /* タイトル */
    .main-title {
        font-family: 'Orbitron', monospace;
        font-size: 3.5rem;
        font-weight: 700;
        background: linear-gradient(45deg, #00ff88, #0088ff, #ff0088);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 0 0 30px rgba(0, 255, 136, 0.5);
        animation: glow 2s ease-in-out infinite alternate;
    }
    
    @keyframes glow {
        from { filter: brightness(1); }
        to { filter: brightness(1.2); }
    }
    
    /* サブタイトル */
    .subtitle {
        font-family: 'Noto Sans JP', sans-serif;
        text-align: center;
        color: #88ccff;
        font-size: 1.2rem;
        margin-bottom: 3rem;
        opacity: 0.9;
    }
    
    /* チャットメッセージ */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(136, 204, 255, 0.3);
        border-radius: 15px;
        backdrop-filter: blur(10px);
        margin: 1rem 0;
        padding: 1rem;
        box-shadow: 0 4px 20px rgba(0, 136, 255, 0.1);
    }
    
    /* ユーザーメッセージ */
    .stChatMessage[data-testid="user-message"] {
        background: rgba(0, 136, 255, 0.1);
        border-color: rgba(0, 136, 255, 0.5);
    }
    
    /* AIメッセージ */
    .stChatMessage[data-testid="assistant-message"] {
        background: rgba(0, 255, 136, 0.1);
        border-color: rgba(0, 255, 136, 0.5);
    }
    
    /* 入力フィールド */
    .stChatInput > div {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 2px solid rgba(136, 204, 255, 0.5) !important;
        border-radius: 25px !important;
        color: white !important;
    }
    
    .stChatInput input {
        color: white !important;
        font-family: 'Noto Sans JP', sans-serif;
    }
    
    /* ボタン */
    .stButton > button {
        background: linear-gradient(45deg, #00ff88, #0088ff);
        color: #000;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        font-family: 'Noto Sans JP', sans-serif;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 255, 136, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(0, 255, 136, 0.5);
    }
    
    /* サイドバー */
    .css-1d391kg {
        background: rgba(26, 26, 46, 0.95);
        border-right: 1px solid rgba(136, 204, 255, 0.3);
    }
    
    /* ステータスインジケーター */
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 10px;
        animation: pulse 2s infinite;
    }
    
    .status-active {
        background: #00ff88;
        box-shadow: 0 0 10px #00ff88;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    /* ワークフローカード */
    .workflow-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(136, 204, 255, 0.3);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    
    .workflow-card:hover {
        background: rgba(255, 255, 255, 0.1);
        border-color: rgba(0, 255, 136, 0.5);
        transform: translateX(5px);
    }
    
    /* プログレスバー */
    .progress-bar {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        height: 10px;
        overflow: hidden;
        margin: 1rem 0;
    }
    
    .progress-fill {
        background: linear-gradient(90deg, #00ff88, #0088ff);
        height: 100%;
        animation: progress 2s ease-in-out;
    }
    
    @keyframes progress {
        from { width: 0%; }
        to { width: 100%; }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'context' not in st.session_state:
    st.session_state.context = {}
if 'current_workflow' not in st.session_state:
    st.session_state.current_workflow = None
if 'workflow_step' not in st.session_state:
    st.session_state.workflow_step = 0

# API setup
@st.cache_resource
def setup_gemini():
    api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
    if api_key:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-2.0-flash-exp')
    return None

class YouTubeAIAgent:
    def __init__(self):
        self.model = setup_gemini()
        
        # 全13種類のワークフロー定義
        self.workflows = {
            "channel_concept": {
                "name": "チャンネルコンセプト設計",
                "description": "YouTubeチャンネルのコンセプトを設計し、SEOキーワードとペルソナに基づいた戦略を立案",
                "icon": "🎯",
                "prompts": {
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
            },
            "video_marketing": {
                "name": "動画マーケティング支援",
                "description": "動画の内容からサムネイル文言とタイトルを生成",
                "icon": "🎨",
                "prompts": {
                    "main": """
                    #TASK_EXECUTION[TYPE=動画マーケティング支援]
                    
                    動画内容: {video_content}
                    チャンネル情報: {channel_info}
                    
                    Step1: 動画の内容を分析し、視聴者の興味を引くポイントを抽出
                    Step2: ペルソナ別に響くサムネイル文言を10パターン生成
                    Step3: SEO効果の高いタイトルを10パターン生成
                    Step4: クリック率を最大化する組み合わせTOP3を提案
                    """
                }
            },
            "video_planning": {
                "name": "動画企画生成＆SEO最適化",
                "description": "SEOキーワードに基づいた動画企画とタイトル案を生成",
                "icon": "📋",
                "prompts": {
                    "main": """
                    #TASK_EXECUTION[TYPE=動画企画生成]
                    
                    キーワード: {keywords}
                    チャンネルテーマ: {channel_theme}
                    
                    Step1: キーワードの検索意図を分析
                    Step2: 競合動画の分析（想定）
                    Step3: 差別化できる動画企画を30個生成
                    Step4: 各企画のSEO効果とバイラル性を評価
                    Step5: TOP10企画の詳細な構成案を作成
                    """
                }
            },
            "shorts_planning": {
                "name": "YouTube Shorts企画生成",
                "description": "ショート動画向けの企画案を大量生成し、ランキング評価",
                "icon": "📱",
                "prompts": {
                    "main": """
                    #TASK_EXECUTION[TYPE=Shorts企画生成]
                    
                    テーマ: {theme}
                    ターゲット: {target}
                    
                    Step1: Shortsのトレンドを分析
                    Step2: 60秒以内で完結する企画を50個生成
                    Step3: 各企画のフック力、完視聴率、バイラル性を評価
                    Step4: カテゴリー別にTOP企画をランキング
                    Step5: 制作優先順位と投稿スケジュールを提案
                    """
                }
            },
            "shorts_script": {
                "name": "Shorts台本生成",
                "description": "最新トレンドを踏まえたショート動画台本を作成",
                "icon": "📝",
                "prompts": {
                    "main": """
                    #TASK_EXECUTION[TYPE=Shorts台本生成]
                    
                    企画: {plan}
                    キーワード: {keywords}
                    
                    Step1: 関連キーワードでナレッジを収集
                    Step2: 最初の3秒のフックを5パターン作成
                    Step3: 15秒ごとのシーン構成を設計
                    Step4: オチとCTAを最適化
                    Step5: 撮影・編集指示を含む完全台本を生成
                    """
                }
            },
            "content_scoring": {
                "name": "コンテンツスコアリング",
                "description": "作成したコンテンツの品質を評価し、改善点をフィードバック",
                "icon": "📊",
                "prompts": {
                    "main": """
                    #TASK_EXECUTION[TYPE=コンテンツスコアリング]
                    
                    タイトル: {title}
                    サムネイル: {thumbnail}
                    説明文: {description}
                    
                    評価項目:
                    1. SEO最適化スコア（キーワード配置、密度）
                    2. クリック率予測（タイトル魅力度、サムネイル効果）
                    3. 視聴維持率予測（期待値管理、内容の一致度）
                    4. エンゲージメント予測（コメント誘発度、シェア可能性）
                    5. 総合スコアと改善提案
                    """
                }
            },
            "keyword_strategy": {
                "name": "キーワード戦略シミュレーション",
                "description": "YouTube運用のためのキーワード戦略を多角的に分析・提案",
                "icon": "🔍",
                "prompts": {
                    "main": """
                    #TASK_EXECUTION[TYPE=キーワード戦略]
                    
                    ビジネス: {business}
                    目標: {goals}
                    
                    Step1: シードキーワードから関連キーワードを収集
                    Step2: キーワードの価値評価（検索数、競合性、収益性）
                    Step3: 3ヶ月、6ヶ月、12ヶ月のフェーズ別戦略
                    Step4: コンテンツカレンダーの作成
                    Step5: KPI設定と成功指標の定義
                    """
                }
            },
            "long_script": {
                "name": "長尺動画台本生成",
                "description": "10-30分の詳細な動画台本を生成",
                "icon": "🎬",
                "prompts": {
                    "main": """
                    #TASK_EXECUTION[TYPE=長尺動画台本]
                    
                    トピック: {topic}
                    スタイル: {style}
                    
                    Step1: トピックに関するナレッジを体系的に整理
                    Step2: 視聴者の理解度に応じた構成を設計
                    Step3: チャプター別の詳細台本を作成
                    Step4: ビジュアル指示とB-roll提案
                    Step5: 編集指示を含む完全台本を生成
                    """
                }
            },
            "competitor_analysis": {
                "name": "競合チャンネル分析",
                "description": "競合チャンネルを分析し、差別化戦略を提案",
                "icon": "🔬",
                "prompts": {
                    "main": """
                    #TASK_EXECUTION[TYPE=競合分析]
                    
                    競合チャンネル: {competitors}
                    自チャンネル: {own_channel}
                    
                    Step1: 競合の強み・弱みを分析
                    Step2: コンテンツギャップを特定
                    Step3: 差別化ポイントを抽出
                    Step4: 勝てる領域の特定
                    Step5: 具体的なアクションプランを提案
                    """
                }
            },
            "trend_forecast": {
                "name": "トレンド予測＆早期参入戦略",
                "description": "今後のトレンドを予測し、早期参入戦略を立案",
                "icon": "📈",
                "prompts": {
                    "main": """
                    #TASK_EXECUTION[TYPE=トレンド予測]
                    
                    ジャンル: {genre}
                    現在のトレンド: {current_trends}
                    
                    Step1: 過去のトレンドパターンを分析
                    Step2: 新興トレンドの兆候を特定
                    Step3: 3-6ヶ月後のトレンド予測
                    Step4: 早期参入のためのコンテンツ戦略
                    Step5: リスクヘッジプランの策定
                    """
                }
            },
            "monetization": {
                "name": "収益化戦略立案",
                "description": "チャンネルの収益化戦略を多角的に立案",
                "icon": "💰",
                "prompts": {
                    "main": """
                    #TASK_EXECUTION[TYPE=収益化戦略]
                    
                    チャンネル規模: {channel_size}
                    コンテンツタイプ: {content_type}
                    
                    Step1: 現在の収益化ポテンシャルを分析
                    Step2: 複数の収益源を特定（広告、スポンサー、商品等）
                    Step3: 各収益源の実装計画
                    Step4: 収益予測シミュレーション
                    Step5: 段階的な実行プランを作成
                    """
                }
            },
            "community_building": {
                "name": "コミュニティ構築戦略",
                "description": "熱狂的なファンコミュニティを構築する戦略",
                "icon": "👥",
                "prompts": {
                    "main": """
                    #TASK_EXECUTION[TYPE=コミュニティ構築]
                    
                    チャンネルテーマ: {theme}
                    現在の規模: {current_size}
                    
                    Step1: コアファン層の特定
                    Step2: エンゲージメント施策の設計
                    Step3: コミュニティプラットフォームの選定
                    Step4: ファン参加型コンテンツの企画
                    Step5: 長期的な関係構築プランの策定
                    """
                }
            },
            "collaboration": {
                "name": "コラボレーション戦略",
                "description": "他のクリエイターとの効果的なコラボ戦略",
                "icon": "🤝",
                "prompts": {
                    "main": """
                    #TASK_EXECUTION[TYPE=コラボ戦略]
                    
                    自チャンネル: {own_channel}
                    ターゲット層: {target_audience}
                    
                    Step1: コラボ候補者のリストアップ
                    Step2: 相乗効果の高い組み合わせを特定
                    Step3: アプローチ方法の設計
                    Step4: コラボ企画の立案
                    Step5: 実行スケジュールと期待効果の算出
                    """
                }
            }
        }
    
    def extract_url_content(self, url: str) -> str:
        """URLからコンテンツを抽出"""
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title = soup.find('title').text if soup.find('title') else ''
            meta_desc = soup.find('meta', {'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ''
            
            # 本文の主要部分を抽出
            main_content = []
            for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li']):
                text = tag.get_text().strip()
                if text and len(text) > 20:
                    main_content.append(text)
            
            content_text = '\n'.join(main_content[:50])  # 最初の50要素
            
            return f"""
            ページタイトル: {title}
            メタ説明: {description}
            
            主要コンテンツ:
            {content_text}
            """
        except Exception as e:
            return f"URLの読み取りエラー: {str(e)}"
    
    def analyze_intent(self, user_input: str) -> Tuple[str, Dict[str, Any]]:
        """ユーザーの意図を分析して適切なワークフローを選択"""
        
        # URL検出と抽出
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', user_input)
        url_content = ""
        if urls:
            for url in urls:
                url_content += self.extract_url_content(url)
        
        prompt = f"""
        ユーザー入力: {user_input}
        {"抽出されたURL内容: " + url_content if url_content else ""}
        
        利用可能なワークフロー:
        {json.dumps([{"key": k, "name": v["name"], "description": v["description"]} for k, v in self.workflows.items()], ensure_ascii=False)}
        
        ユーザーの意図を分析し、最も適切なワークフローを選択してください。
        また、ワークフローに必要な情報を抽出してください。
        
        以下のJSON形式で回答:
        {{
            "workflow": "選択されたワークフローのキー",
            "confidence": 0.0-1.0,
            "extracted_info": {{
                "必要な情報のキー": "抽出された値"
            }},
            "missing_info": ["不足している情報"],
            "clarification": "必要な場合の確認質問"
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text)
            
            if url_content:
                result["extracted_info"]["url_content"] = url_content
                
            return result["workflow"], result
        except:
            return None, {"confidence": 0, "clarification": "どのようなお手伝いをしましょうか？"}
    
    def execute_workflow(self, workflow_key: str, context: Dict[str, Any]) -> str:
        """選択されたワークフローを実行"""
        if workflow_key not in self.workflows:
            return "申し訳ございません。適切なワークフローが見つかりませんでした。"
        
        workflow = self.workflows[workflow_key]
        prompts = workflow["prompts"]
        
        # ワークフローに応じて適切なプロンプトを実行
        if workflow_key == "channel_concept":
            return self.execute_channel_concept(prompts, context)
        else:
            # その他のワークフローは単一プロンプト実行
            main_prompt = prompts.get("main", "")
            filled_prompt = self.fill_prompt_template(main_prompt, context)
            
            response = self.model.generate_content(filled_prompt)
            return response.text
    
    def execute_channel_concept(self, prompts: Dict[str, str], context: Dict[str, Any]) -> str:
        """チャンネルコンセプト設計の実行"""
        results = []
        
        # Step 1: 商品情報とキーワード抽出
        step1_prompt = self.fill_prompt_template(prompts["step1"], context)
        step1_result = self.model.generate_content(step1_prompt).text
        results.append("### Step 1: 商品分析とキーワード抽出\n" + step1_result)
        
        # キーワードを抽出してコンテキストに追加
        context["keywords"] = self.extract_keywords_from_text(step1_result)
        
        # Step 2: ペルソナ抽出
        step2_prompt = self.fill_prompt_template(prompts["step2"], context)
        step2_result = self.model.generate_content(step2_prompt).text
        results.append("\n### Step 2: ペルソナ分析\n" + step2_result)
        
        context["personas"] = step2_result
        
        # Step 3: ゴールイメージ作成
        step3_prompt = self.fill_prompt_template(prompts["step3"], context)
        step3_result = self.model.generate_content(step3_prompt).text
        results.append("\n### Step 3: ゴールイメージ設定\n" + step3_result)
        
        context["goals"] = step3_result
        
        # Step 4: コンセプト生成
        step4_prompt = self.fill_prompt_template(prompts["step4"], context)
        step4_result = self.model.generate_content(step4_prompt).text
        results.append("\n### Step 4: チャンネルコンセプト案\n" + step4_result)
        
        return "\n".join(results)
    
    def fill_prompt_template(self, template: str, context: Dict[str, Any]) -> str:
        """プロンプトテンプレートに値を埋め込む"""
        filled = template
        
        # コンテキストから値を埋め込む
        for key, value in context.items():
            placeholder = "{" + key + "}"
            if placeholder in filled:
                filled = filled.replace(placeholder, str(value))
        
        # 残っているプレースホルダーをデフォルト値で埋める
        placeholders = re.findall(r'\{(\w+)\}', filled)
        for placeholder in placeholders:
            filled = filled.replace("{" + placeholder + "}", f"[{placeholder}情報なし]")
        
        return filled
    
    def extract_keywords_from_text(self, text: str) -> str:
        """テキストからキーワードを抽出"""
        # 簡易的な実装。実際にはより高度な抽出が必要
        lines = text.split('\n')
        keywords = []
        for line in lines:
            if 'キーワード' in line or '1.' in line or '2.' in line or '3.' in line:
                keywords.append(line)
        return '\n'.join(keywords[:10])
    
    def process_message(self, message: str, context: Dict[str, Any]) -> str:
        """メッセージを処理してレスポンスを生成"""
        
        # 意図分析
        workflow_key, intent_result = self.analyze_intent(message)
        
        if intent_result["confidence"] > 0.7:
            # 高信頼度でワークフローを実行
            context.update(intent_result["extracted_info"])
            
            # 不足情報があれば確認
            if intent_result.get("missing_info"):
                return f"""
                {self.workflows[workflow_key]['name']}を実行します。
                
                追加で以下の情報を教えてください：
                {chr(10).join(['・' + info for info in intent_result['missing_info']])}
                """
            
            # ワークフロー実行
            result = self.execute_workflow(workflow_key, context)
            
            # コンテキストを保存
            st.session_state.context["last_workflow"] = workflow_key
            st.session_state.context["last_result"] = result
            
            return result
            
        elif intent_result.get("clarification"):
            # 確認が必要
            return intent_result["clarification"]
        else:
            # 一般的な会話として処理
            return self.general_conversation(message, context)
    
    def general_conversation(self, message: str, context: Dict[str, Any]) -> str:
        """一般的な会話処理"""
        prompt = f"""
        あなたはYouTubeコンテンツ制作の専門AIアシスタントです。
        
        ユーザーメッセージ: {message}
        コンテキスト: {json.dumps(context, ensure_ascii=False)}
        
        以下のサポートが可能です：
        {chr(10).join([f"・{v['name']}: {v['description']}" for v in self.workflows.values()])}
        
        ユーザーのニーズに合わせて、適切なワークフローを提案するか、
        YouTubeに関する専門的なアドバイスを提供してください。
        
        フレンドリーで親しみやすいトーンで応答してください。
        """
        
        response = self.model.generate_content(prompt)
        return response.text

# メイン画面
def main():
    # タイトル
    st.markdown('<h1 class="main-title">YouTube AI Agent</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">次世代のYouTubeコンテンツ制作をAIがフルサポート</p>', unsafe_allow_html=True)
    
    # エージェント初期化
    agent = YouTubeAIAgent()
    
    if not agent.model:
        st.error("⚠️ Gemini APIキーが設定されていません")
        return
    
    # ステータスインジケーター
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            '<div style="text-align: center; margin-bottom: 2rem;">'
            '<span class="status-indicator status-active"></span>'
            '<span style="color: #00ff88;">AI Agent Active</span>'
            '</div>',
            unsafe_allow_html=True
        )
    
    # チャット履歴表示
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
                st.markdown(message["content"])
    
    # 入力フィールド
    if prompt := st.chat_input("メッセージを入力してください..."):
        # ユーザーメッセージ追加
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        
        # AI応答生成
        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            
            # タイピングアニメーション
            with st.spinner("思考中..."):
                response = agent.process_message(prompt, st.session_state.context)
            
            # レスポンスを段階的に表示（タイピング効果）
            displayed_text = ""
            for char in response:
                displayed_text += char
                message_placeholder.markdown(displayed_text + "▌")
                time.sleep(0.01)
            
            message_placeholder.markdown(response)
        
        # アシスタントメッセージ追加
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    # サイドバー
    with st.sidebar:
        st.markdown("## 🚀 クイックスタート")
        
        # ワークフローボタン
        st.markdown("### 💡 ワークフローを選択")
        
        for key, workflow in agent.workflows.items():
            if st.button(
                f"{workflow['icon']} {workflow['name']}",
                key=f"workflow_{key}",
                use_container_width=True,
                help=workflow['description']
            ):
                prompt = f"{workflow['name']}を実行してください"
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.rerun()
        
        st.markdown("---")
        
        # サンプルプロンプト
        st.markdown("### 📝 サンプル")
        
        examples = [
            "学習塾のYouTubeチャンネルを始めたいです",
            "https://example.com このサービスでYouTubeを始めたい",
            "料理系YouTuberになりたい。戦略を教えて",
            "Shortsでバズる企画を50個考えて",
            "10分の解説動画の台本を作って",
            "競合チャンネルを分析して差別化戦略を提案して"
        ]
        
        for example in examples:
            if st.button(example, key=f"example_{examples.index(example)}"):
                st.session_state.messages.append({"role": "user", "content": example})
                st.rerun()
        
        st.markdown("---")
        
        # コンテキスト表示
        if st.session_state.context:
            with st.expander("📊 現在のコンテキスト"):
                st.json(st.session_state.context)
        
        # リセットボタン
        if st.button("🔄 会話をリセット", use_container_width=True):
            st.session_state.messages = []
            st.session_state.context = {}
            st.rerun()

if __name__ == "__main__":
    main()