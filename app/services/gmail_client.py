import os, base64
from typing import Optional, Dict, List
from email.message import EmailMessage

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

def _service():
    # Usa el token generado por InstalledAppFlow (quickstart oficial)
    creds = Credentials.from_authorized_user_file("utils/token.json", SCOPES)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

def send_email(to: str, subject: str, body: str,
               thread_id: Optional[str] = None,
               in_reply_to_rfc_message_id: Optional[str] = None) -> Dict:
    svc = _service()
    msg = EmailMessage()
    msg["To"] = to
    msg["From"] = "enzo.ip.98@gmail.com"
    msg["Subject"] = subject
    msg.set_content(body)

    # Para RESPONDER en el mismo hilo de forma más robusta:
    if in_reply_to_rfc_message_id:
        msg["In-Reply-To"] = in_reply_to_rfc_message_id
        msg["References"] = in_reply_to_rfc_message_id

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id

    return svc.users().messages().send(userId="me", body=payload).execute()

def list_messages(query: str, max_results: int = 50) -> List[Dict]:
    svc = _service()
    resp = svc.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    return resp.get("messages", [])

def get_message(msg_id: str) -> Dict:
    svc = _service()
    return svc.users().messages().get(userId="me", id=msg_id, format="full").execute()