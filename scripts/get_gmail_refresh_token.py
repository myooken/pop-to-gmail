#!/usr/bin/env python3
"""初回セットアップ専用: ローカルPCで1回だけ実行し、Gmailのrefresh_tokenを取得する。

ブラウザでのログイン確認が必要なため、GitHub Actions上では実行しない。

事前準備:
  1. Google Cloud Console でプロジェクトを作成し、Gmail API を有効化
  2. OAuth同意画面を設定 (公開状況「テスト」のまま、テストユーザーに自分のGmailアドレスを追加)
  3. 認証情報 > OAuthクライアントID を作成 (アプリケーションの種類: デスクトップアプリ)
  4. ダウンロードしたJSONを client_secret.json という名前でこのファイルと同じディレクトリに置く

実行方法:
  pip install -r requirements.txt
  python scripts/get_gmail_refresh_token.py
"""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.insert"]


def main() -> None:
    flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
    creds = flow.run_local_server(port=0)
    print("\n=== 以下をリポジトリの GitHub Secrets に登録してください ===")
    print(f"GMAIL_CLIENT_ID={creds.client_id}")
    print(f"GMAIL_CLIENT_SECRET={creds.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")


if __name__ == "__main__":
    main()
