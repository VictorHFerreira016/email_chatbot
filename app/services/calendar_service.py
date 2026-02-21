import os
import logging
from datetime import datetime
from typing import Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

class CalendarService:
    def __init__(self):
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None

        if os.path.exists("token_calendar.json"):
            creds = Credentials.from_authorized_user_file("token_calendar.json", SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open("token_calendar.json", "w") as token:
                token.write(creds.to_json())

        return build("calendar", "v3", credentials=creds)

    def create_event(
        self,
        summary: str,
        start_datetime: str,
        end_datetime: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> dict:
        """
        Creates an event in Google Calendar.

        Args:
            summary: Event title
            start_datetime: Start date/time (ISO 8601: '2024-03-20T10:00:00')
            end_datetime: End date/time (optional, default: 1 hour later)
            description: Event description
            location: Event location
        """
        try:
            if not end_datetime:
                from datetime import timedelta
                start = datetime.fromisoformat(start_datetime)
                end = start + timedelta(hours=1)
                end_datetime = end.isoformat()

            event = {
                "summary": summary,
                "description": description or "",
                "location": location or "",
                "start": {
                    "dateTime": start_datetime,
                    "timeZone": "America/Sao_Paulo",
                },
                "end": {
                    "dateTime": end_datetime,
                    "timeZone": "America/Sao_Paulo",
                },
            }

            created_event = self.service.events().insert(
                calendarId="primary", body=event
            ).execute()

            logger.info(f"Evento criado: {created_event.get('htmlLink')}")
            return {
                "status": "success",
                "event_id": created_event["id"],
                "link": created_event.get("htmlLink"),
                "summary": summary,
            }

        except Exception as e:
            logger.error(f"Erro ao criar evento: {e}")
            return {"status": "error", "message": str(e)}

    def list_upcoming_events(self, max_results: int = 10) -> list:
        """Lista próximos eventos do calendário"""
        try:
            now = datetime.utcnow().isoformat() + "Z"
            events_result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            return events_result.get("items", [])
        except Exception as e:
            logger.error(f"Erro ao listar eventos: {e}")
            return []