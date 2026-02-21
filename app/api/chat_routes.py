from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.agent_service import EmailAgent

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)

agent = EmailAgent()

class ChatMessage(BaseModel):
    message: str
    history: Optional[List[dict]] = None


class ChatResponse(BaseModel):
    response: str


@router.post("/", response_model=ChatResponse)
def chat(chat_input: ChatMessage):
    """
    Endpoint para conversar com o agente de e-mails.
    """
    try:
        # Converte histórico se existir
        history = []
        if chat_input.history:
            from langchain_core.messages import HumanMessage, AIMessage
            for msg in chat_input.history:
                if msg["role"] == "user":
                    history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    history.append(AIMessage(content=msg["content"]))
        
        response = agent.chat(chat_input.message, history)
        
        return ChatResponse(response=response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))