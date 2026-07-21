# pop_gmail

Gmailの「他のアカウントのメールを取得(POP3)」機能が使えなくなった代替として、
GitHub Actions を手動実行してPOPサーバーの新着メールをGmailに取り込む。

> **注意**: POPアカウントの情報やGmailのOAuth情報を扱うため、フォークして使う場合は
> **プライベートリポジトリでの運用を推奨する**。

## 仕組み

1. `scripts/fetch_pop_to_gmail.py` がPOP3(SSL)でサーバーに接続し、`UIDL` で新着メールのみ判定
2. 新着メールを生のRFC822形式のまま Gmail API の `messages.import` でGmailに取り込む
   (`insert` と違い、Gmailのフィルタ・スパム判定を通した上で受信トレイに入る。実際にPOPで受信した場合と同じ挙動)
3. 取り込み済みメールのUIDLは `state/processed_uids.json` に保存し、`actions/cache` でジョブ間に引き継いで重複取り込みを防ぐ

トリガーは `workflow_dispatch` のみ(手動実行)。GitHubリポジトリの Actions タブ、または
`gh workflow run fetch-pop-mail.yml` で好きなタイミングに受信できる。

## セットアップ

### 1. Google Cloud側の準備 (初回のみ、ローカルで実施)

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成し、Gmail API を有効化
2. OAuth同意画面を設定 (公開状況「テスト」のままでよい。テストユーザーに自分のGmailアドレスを追加)
3. 認証情報 > OAuthクライアントID を作成 (アプリケーションの種類: **デスクトップアプリ**)
4. ダウンロードしたJSONを `client_secret.json` としてこのリポジトリのルートに保存 (`.gitignore` 済み・コミットしないこと)

### 2. refresh_token の取得 (初回のみ、ローカルで実施)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/get_gmail_refresh_token.py
```

ブラウザが開くので対象のGmailアカウントで認可する。表示された
`GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN` を控える。

### 3. GitHub Secrets の登録

リポジトリの Settings > Secrets and variables > Actions で以下を登録する。

| Secret名 | 内容 |
|---|---|
| `POP_HOST` | POPサーバーのホスト名 |
| `POP_PORT` | POPサーバーのポート番号 (通常995、省略時は995) |
| `POP_USER` | POPアカウントのユーザー名 |
| `POP_PASSWORD` | POPアカウントのパスワード |
| `GMAIL_CLIENT_ID` | 手順2で取得 |
| `GMAIL_CLIENT_SECRET` | 手順2で取得 |
| `GMAIL_REFRESH_TOKEN` | 手順2で取得 |

- Secretsはリポジトリごとに個別管理されるため、フォークしても元リポジトリのSecretsは引き継がれない。フォーク先で上記をすべて登録し直す必要がある。

### 4. 実行

GitHubリポジトリの Actions タブ > "Fetch POP mail into Gmail" > Run workflow。
または `gh workflow run fetch-pop-mail.yml`。

## 補足

- POPサーバー上のメールは削除しない (デフォルトのGmail POP設定と同様、サーバーにコピーを残す)。
  容量が気になる場合はスクリプトに `DELE` を追加すること。
- `state/processed_uids.json` は `actions/cache` にのみ保存され、リポジトリにはコミットされない。
  キャッシュが失効した場合は同じメールが再取り込みされる可能性がある。

## License

Apache License 2.0 ([LICENSE](LICENSE)を参照)。
依存ライブラリの `google-api-python-client` / `google-auth` / `google-auth-oauthlib` に合わせている。
