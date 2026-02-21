import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from pydantic import SecretStr
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from app.config import settings
from app.services.gmail_service import GmailService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

class EmailClassifier:
    """
    Classify and extract relevant information from emails using LLM.
    """

    CLASSIFICATION_PROMPT = """
Você é um assistente que analisa e-mails.

Classifique o e-mail em UMA das categorias:
- reuniao/evento
- boleto
- pessoal
- promocao

Extraia também informações relevantes se existirem:
- data_reuniao (formato YYYY-MM-DD)
- valor_boleto
- acao_sugerida

E-mail:
Remetente: {sender}
Assunto: {subject}
Data: {date}
Corpo: {body}

Responda APENAS com um objeto JSON válido, SEM texto antes ou depois:

{{
  "categoria": "categoria_escolhida",
  "resumo": "resumo breve em 1 frase",
  "prioridade": "alta|media|baixa",
  "data_reuniao": "YYYY-MM-DD ou null",
  "valor_boleto": "valor ou null",
  "acao_sugerida": "ação recomendada ou null"
}}
"""

    def __init__(self):
        self.llm = ChatGroq(
            api_key=SecretStr(settings.GROQ_API_KEY),
            model=settings.GROQ_MODEL,
            temperature=settings.GROQ_TEMPERATURE,
            max_tokens=settings.GROQ_MAX_TOKENS
        )

    def classify_email(self, email: Dict[str, str]) -> Dict[str, Any]:
        prompt = self.CLASSIFICATION_PROMPT.format(
            sender=email.get("sender", "Desconhecido"),
            subject=email.get("subject", "Sem assunto"),
            date=email.get("date", ""),
            body=email.get("body", "")[:800],
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content
            
            logger.info(f"Resposta do LLM: {content[:200]}") 

            if isinstance(content, str):
                content = content.strip()
                
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "").strip()
                elif content.startswith("```"):
                    content = content.replace("```", "").strip()
                
                try:
                    result = json.loads(content)
                except json.JSONDecodeError:
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                    else:
                        raise ValueError("Não foi possível extrair JSON da resposta")
            else:
                result = content

            return {
                **email,
                "categoria": result.get("categoria", "promocao"), # type: ignore
                "resumo": result.get("resumo", "Sem resumo"), # type: ignore
                "prioridade": result.get("prioridade", "media"), # type: ignore
                "data_reuniao": result.get("data_reuniao"), # type: ignore
                "valor_boleto": result.get("valor_boleto"), # type: ignore
                "acao_sugerida": result.get("acao_sugerida"), # type: ignore
                "processed_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Erro ao classificar e-mail '{email.get('subject', 'N/A')}': {e}")

            return {
                **email,
                "categoria": "pessoal",
                "resumo": f"E-mail de {email.get('sender', 'desconhecido')}",
                "prioridade": "baixa",
                "data_reuniao": None,
                "valor_boleto": None,
                "acao_sugerida": None,
                "processed_at": datetime.now().isoformat(),
            }

class EmailService:
    def __init__(self):
        self.classifier = EmailClassifier()
        self.storage = EmailStorage()
        self.gmail = GmailService()
        self.rag = RAGService()

    def fetch_emails(self):
        return self.gmail.fetch_recent_emails(days=settings.days_to_keep)
    
    def process_emails(self):
        logger.info("Iniciando busca de e-mails...")
        raw_emails = self.fetch_emails()
        
        logger.info(f"Total de e-mails recuperados: {len(raw_emails)}")
        
        if len(raw_emails) == 0:
            logger.warning("Nenhum e-mail encontrado para processar")
            return {
                "processed": 0,
                "emails": [],
            }
        
        processed = []

        for idx, email in enumerate(raw_emails, 1):
            logger.info(f"Processando e-mail {idx}/{len(raw_emails)}: {email.get('subject', 'Sem assunto')}")
            result = self.classifier.classify_email(email)
            processed.append(result)

        logger.info(f"Salvando {len(processed)} e-mails processados...")
        self.storage.save_processed(processed)
        
        logger.info("Adicionando e-mails ao RAG (Pinecone)...")
        self.rag.clear_namespace()
        self.rag.add_emails(processed)
        
        logger.info("✅ Processamento concluído!")

        return {
            "processed": len(processed),
            "emails": processed,
        }

    def get_all_emails(self):
        return self.storage.load_processed()
    
    def get_by_category(self):
        emails = self.get_all_emails()

        grouped = {
            "reuniao": [],
            "boleto": [],
            "pessoal": [],
            "promocao": [],
        }

        for email in emails:
            categoria = email.get("categoria", "promocao")
            if categoria in grouped:
                grouped[categoria].append(email)

        return grouped

class EmailStorage:
    def __init__(self):
        self.processed_file = Path(settings.emails_processed_file)
        self.processed_file.parent.mkdir(parents=True, exist_ok=True)

    def load_processed(self) -> List[Dict[str, Any]]:
        if not self.processed_file.exists():
            return []

        with open(self.processed_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("emails", [])

    def save_processed(self, emails: List[Dict[str, Any]]) -> None:
        data = {
            "last_update": datetime.now().isoformat(),
            "total": len(emails),
            "emails": emails,
        }

        with open(self.processed_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

