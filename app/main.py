from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import email_routes
from app.config import settings
from app.api import email_routes, chat_routes

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(email_routes.router, tags=['emails'])
app.include_router(chat_routes.router, tags=['chats']) 

@app.get("/")
def root():
    return {
        "status": "API's working!"
    }