import os
import base64
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

class GmailService:
    def __init__(self):
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None

        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        if not creds or not creds.token_state:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open("token.json", "w") as token:
                token.write(creds.to_json())

        return build("gmail", "v1", credentials=creds)

    def fetch_recent_emails(self, days: int = 7) -> List[Dict]:
        query_date = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")

        results = (
            self.service
            .users()
            .messages()
            .list(userId="me", q=f"after:{query_date}")
            .execute()
        )

        messages = results.get("messages", [])

        emails = []

        for msg in messages:
            msg_data = (
                self.service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="full")
                .execute()
            )

            payload = msg_data.get("payload", {})
            headers = payload.get("headers", [])

            email_data = {
                "id": msg["id"],
                "sender": "",
                "subject": "",
                "date": "",
                "body": "",
            }

            for header in headers:
                name = header["name"]
                if name == "From":
                    email_data["sender"] = header["value"]
                elif name == "Subject":
                    email_data["subject"] = header["value"]
                elif name == "Date":
                    email_data["date"] = header["value"]

            parts = payload.get("parts")
            if parts:
                for part in parts:
                    if part["mimeType"] == "text/plain":
                        data = part["body"].get("data")
                        if data:
                            decoded = base64.urlsafe_b64decode(data).decode("utf-8")
                            email_data["body"] = decoded
                            break

            emails.append(email_data)

        logger.info(f"{len(emails)} e-mails recuperados do Gmail.")
        return emails
