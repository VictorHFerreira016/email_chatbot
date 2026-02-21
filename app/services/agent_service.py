import json
import logging
from datetime import datetime
from typing import TypedDict, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from pydantic import SecretStr
from app.config import settings
from app.services.rag_service import RAGService
from app.services.calendar_service import CalendarService

logger = logging.getLogger(__name__)

def search_emails_tool(query: str) -> str:
    """Search for relevant emails based on the user's query."""
    try:
        rag = RAGService()
        results = rag.search(query, top_k=5)
        
        if not results:
            return "Nenhum e-mail encontrado na base de dados. Certifique-se de ter processado os e-mails primeiro clicando em 'Processar E-mails'."
        
        formatted = ["📧 E-mails encontrados:\n"]
        for i, email in enumerate(results, 1):
            formatted.append(
                f"{i}. **{email.get('subject', 'Sem assunto')}**\n"
                f"   De: {email.get('sender', 'Desconhecido')}\n"
                f"   Data: {email.get('date', 'N/A')}\n"
                f"   Categoria: {email.get('categoria', 'N/A')}\n"
                f"   Resumo: {email.get('resumo', 'N/A')}\n"
            )
            
            if email.get('data_reuniao'):
                formatted.append(f"   📅 Reunião marcada: {email.get('data_reuniao')}\n")
            if email.get('valor_boleto'):
                formatted.append(f"   💰 Valor: {email.get('valor_boleto')}\n")
            
            formatted.append("\n")
        
        return "".join(formatted)
    
    except Exception as e:
        logger.error(f"Erro ao buscar e-mails: {e}")
        return f"Erro ao buscar e-mails: {str(e)}"


def create_calendar_event_tool(
    summary: str,
    start_datetime: str,
    end_datetime: str = "",
    description: str = ""
) -> str:
    """
    Create an event in Google Calendar.

    Args:
        summary: Event title (e.g., "Meeting with client")
        start_datetime: Start date/time in ISO format (e.g., "2024-03-20T10:00:00")
        end_datetime: End date/time (optional)
        description: Additional description
    """
    calendar = CalendarService()
    result = calendar.create_event(
        summary=summary,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        description=description
    )
    
    if result["status"] == "success":
        return f"✅ Evento criado com sucesso! Link: {result['link']}"
    else:
        return f"❌ Erro ao criar evento: {result['message']}"

class AgentState(TypedDict):
    messages: Sequence[BaseMessage]

class EmailAgent:
    """
    Agente de IA para responder perguntas sobre e-mails e criar eventos.
    """
    
    SYSTEM_PROMPT = """Você é um assistente inteligente de e-mails.

Suas capacidades:
1. Buscar informações em e-mails usando a ferramenta search_emails_tool
2. Criar eventos no Google Calendar usando create_calendar_event_tool

Quando o usuário perguntar sobre:
- Reuniões marcadas → use search_emails_tool com query focada em "reunião"
- Boletos → use search_emails_tool com query "boleto"
- E-mails de alguém → use search_emails_tool com o nome da pessoa
- Criar evento no calendário → use create_calendar_event_tool

IMPORTANTE:
- Se o usuário pedir para marcar reunião, você DEVE extrair:
  * Título da reunião
  * Data e hora (formato: YYYY-MM-DDTHH:MM:SS)
  * Se não tiver data/hora, pergunte ao usuário
  
- Sempre busque nos e-mails ANTES de responder perguntas sobre eles

Seja direto e objetivo nas respostas."""

    def __init__(self):
        self.llm = ChatGroq(
            api_key=SecretStr(settings.groq_api_key),
            model=settings.groq_model,
            temperature=0.3,
        )
        
        self.tools = {
            "search_emails_tool": search_emails_tool,
            "create_calendar_event_tool": create_calendar_event_tool
        }
        
        self.llm_with_tools = self.llm.bind_tools([
            {
                "name": "search_emails_tool",
                "description": "Busca e-mails relevantes baseado na pergunta",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Pergunta ou termo de busca"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "create_calendar_event_tool",
                "description": "Cria evento no Google Calendar",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Título do evento"
                        },
                        "start_datetime": {
                            "type": "string",
                            "description": "Data/hora início ISO format (YYYY-MM-DDTHH:MM:SS)"
                        },
                        "end_datetime": {
                            "type": "string",
                            "description": "Data/hora fim (opcional)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Descrição do evento"
                        }
                    },
                    "required": ["summary", "start_datetime"]
                }
            }
        ])
        
        self.graph = self._build_graph()

    def _build_graph(self):
        """Constrói o grafo do agente"""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", self._execute_tools)
        
        workflow.set_entry_point("agent")
        
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )
        
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()

    def _call_model(self, state: AgentState):
        """Chama o modelo LLM"""
        messages = [SystemMessage(content=self.SYSTEM_PROMPT)] + list(state["messages"])
        response = self.llm_with_tools.invoke(messages)
        return {"messages": state["messages"] + [response]}

    def _should_continue(self, state: AgentState):
        """Decide se continua ou termina"""
        last_message = state["messages"][-1]
        
        # Se tem tool_calls, continua
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        
        return "end"

    def _execute_tools(self, state: AgentState):
        """Executa as ferramentas chamadas"""
        last_message = state["messages"][-1]
        tool_calls = last_message.tool_calls
        
        tool_messages = []
        
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            if tool_name in self.tools:
                try:
                    result = self.tools[tool_name](**tool_args)
                except Exception as e:
                    result = f"Erro ao executar {tool_name}: {str(e)}"
            else:
                result = f"Ferramenta {tool_name} não encontrada"
            
            tool_messages.append(
                ToolMessage(
                    content=result,
                    tool_call_id=tool_call["id"]
                )
            )
        
        return {"messages": state["messages"] + tool_messages}

    def chat(self, message: str, history: list = None) -> str:
        """
        Envia mensagem para o agente e retorna resposta.
        
        Args:
            message: Mensagem do usuário
            history: Histórico de mensagens anterior (opcional)
        """
        try:
            messages = []
            
            if history:
                messages.extend(history)
            
            messages.append(HumanMessage(content=message))
            
            result = self.graph.invoke({"messages": messages})
            
            last_message = result["messages"][-1]
            return last_message.content
        
        except Exception as e:
            logger.error(f"Erro no agente: {e}")
            return f"Desculpe, ocorreu um erro: {str(e)}"