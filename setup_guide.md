# Streamlit Cloud セットアップガイド

## 誰でもブラウザからアクセスできるアプリにする方法

### 1. Streamlit Cloudでのデプロイ手順

1. **Streamlit Cloudにアクセス**
   - https://streamlit.io/cloud にアクセス
   - GitHubアカウントでログイン

2. **新しいアプリを作成**
   - 「New app」をクリック
   - GitHubリポジトリを選択
   - Branch: main
   - Main file path: app.py

3. **Secretsの設定（重要！）**
   - アプリの設定画面で「Settings」タブ
   - 「Secrets」セクションに以下を追加：

```toml
GEMINI_API_KEY = "your-gemini-api-key-here"
KEYWORD_TOOL_API_KEY = "your-keyword-tool-api-key-here"  # オプション
```

### 2. 必要なファイル構成

```
youtube-workflow-app/
├── app.py              # メインアプリケーション
├── requirements.txt    # Python依存関係
├── .gitignore         # Git除外設定
└── README.md          # プロジェクト説明
```

### 3. 共有方法

デプロイが完了すると、以下のようなURLが発行されます：
`https://[あなたのアプリ名].streamlit.app`

このURLを共有するだけで、誰でも：
- 環境構築不要でアクセス可能
- スマートフォンからも利用可能
- 24時間365日利用可能

### 4. 利用制限について

**無料プランの制限**:
- 月間1000時間のアプリ実行時間
- 1GBのリソース制限
- 同時接続数に制限あり

**APIの制限**:
- Gemini API: 無料枠あり（要確認）
- Keyword Tool API: 有料（オプション）

### 5. トラブルシューティング

**「ModuleNotFoundError」が出る場合**:
- requirements.txtを確認
- アプリを再起動（Manage app → Reboot）

**APIキーエラーが出る場合**:
- Secretsが正しく設定されているか確認
- APIキーの有効性を確認

### 6. セキュリティ注意事項

- APIキーは絶対にコードに直接書かない
- .envファイルはGitHubにアップロードしない
- Secretsは暗号化されて保存される