#!/usr/bin/env python3
"""POPサーバーの新着メールをGmail APIでGmailに取り込む。

GitHub Actions の workflow_dispatch から手動実行される想定。
POP3 の UIDL を使って取得済みメッセージを識別し、
処理済み UID のリストを state/processed_uids.json に保存して重複取り込みを防ぐ
(このディレクトリは actions/cache でジョブ間に引き継がれる)。
"""
import base64
import json
import os
import poplib
import sys
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

STATE_PATH = Path(os.environ.get("STATE_PATH", "state/processed_uids.json"))


def load_state() -> set[str]:
    if STATE_PATH.exists():
        return set(json.loads(STATE_PATH.read_text()))
    return set()


def save_state(uids: set[str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(sorted(uids), ensure_ascii=False, indent=2))


def fetch_new_messages(host: str, port: int, user: str, password: str, seen: set[str]):
    """POPサーバーに接続し、未処理メッセージの (uid, raw_bytes) 一覧を返す。"""
    conn = poplib.POP3_SSL(host, port)
    try:
        conn.user(user)
        conn.pass_(password)
        uidl_lines = conn.uidl()[1]  # [b"1 uid1", b"2 uid2", ...]
        new_messages = []
        for line in uidl_lines:
            num_str, uid = line.decode().split(" ", 1)
            if uid in seen:
                continue
            _, lines, _ = conn.retr(int(num_str))
            raw = b"\r\n".join(lines)
            new_messages.append((uid, raw))
        return new_messages
    finally:
        conn.quit()


def import_to_gmail(service, raw_message: bytes) -> None:
    encoded = base64.urlsafe_b64encode(raw_message).decode()
    service.users().messages().import_(
        userId="me",
        body={"raw": encoded, "labelIds": ["INBOX", "UNREAD"]},
        internalDateSource="dateHeader",
        neverMarkSpam=False,
        processForCalendar=False,
    ).execute()


def build_gmail_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/gmail.insert"],
    )
    return build("gmail", "v1", credentials=creds)


def main() -> None:
    host = os.environ["POP_HOST"]
    port = int(os.environ.get("POP_PORT", "995"))
    user = os.environ["POP_USER"]
    password = os.environ["POP_PASSWORD"]

    seen = load_state()
    messages = fetch_new_messages(host, port, user, password, seen)

    if not messages:
        print("新着メールはありませんでした。")
        return

    service = build_gmail_service()
    imported = 0
    for uid, raw in messages:
        try:
            import_to_gmail(service, raw)
            seen.add(uid)
            imported += 1
        except Exception as exc:  # noqa: BLE001
            print(f"取り込み失敗 (uid={uid}): {exc}", file=sys.stderr)
        finally:
            # 途中で失敗しても、成功した分の進捗は必ず残す
            save_state(seen)

    print(f"{imported}/{len(messages)} 件のメールをGmailに取り込みました。")


if __name__ == "__main__":
    main()
