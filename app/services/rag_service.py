import logging
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from app.config import settings

logger = logging.getLogger(__name__)

class RAGService:
    """
    Serviço para armazenar e buscar e-mails usando embeddings no Pinecone.
    """

    def __init__(self):
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self._setup_index()
        self.index = self.pc.Index(settings.pinecone_index_name)

    def _setup_index(self):
        try:
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if settings.pinecone_index_name not in existing_indexes:
                logger.info(f"Criando index {settings.pinecone_index_name}...")
                
                self.pc.create_index(
                    name=settings.pinecone_index_name,
                    dimension=settings.embedding_dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=settings.PINECONE_ENVIRONMENT
                    )
                )
                logger.info("Index criado com sucesso!")
            else:
                logger.info(f"Index {settings.pinecone_index_name} já existe.")
        
        except Exception as e:
            logger.error(f"Erro ao configurar index: {e}")
            raise

    def add_emails(self, emails: List[Dict[str, Any]]) -> None:
        try:
            vectors = []
            
            for email in emails:
                text = f"""
                Assunto: {email.get('subject', '')}
                Remetente: {email.get('sender', '')}
                Data: {email.get('date', '')}
                Categoria: {email.get('categoria', '')}
                Resumo: {email.get('resumo', '')}
                Corpo: {email.get('body', '')[:500]}
                """
                
                embedding = self.embedding_model.encode(text).tolist()
                
                metadata = {
                    "sender": str(email.get("sender", "")),
                    "subject": str(email.get("subject", "")),
                    "date": str(email.get("date", "")),
                    "categoria": str(email.get("categoria", "")),
                    "prioridade": str(email.get("prioridade", "")),
                    "resumo": str(email.get("resumo", ""))[:1000], 
                    "data_reuniao": str(email.get("data_reuniao") or ""),
                    "valor_boleto": str(email.get("valor_boleto") or ""),
                }
                
                vectors.append({
                    "id": email["id"],
                    "values": embedding,
                    "metadata": metadata
                })
            
            if vectors:
                self.index.upsert(
                    vectors=vectors,
                    namespace=settings.pinecone_namespace
                )
                
                logger.info(f"{len(vectors)} e-mails adicionados ao Pinecone")
        
        except Exception as e:
            logger.error(f"Erro ao adicionar e-mails ao Pinecone: {e}")
            raise

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Busca e-mails similares à query no Pinecone"""
        try:
            query_embedding = self.embedding_model.encode(query).tolist()
            
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=settings.pinecone_namespace,
                include_metadata=True
                
            )
            
            emails = []
            for match in results.matches:
                if match.score >= settings.similarity_threshold:
                    email_data = {
                        "id": match.id,
                        "score": match.score,
                        **match.metadata
                    }
                    emails.append(email_data)
            
            logger.info(f"Encontrados {len(emails)} e-mails relevantes")
            return emails
        
        except Exception as e:
            logger.error(f"Erro na busca Pinecone: {e}")
            return []

    def clear_namespace(self) -> None:
        """Limpa todos os vetores do namespace"""
        try:
            stats = self.index.describe_index_stats()
            
            namespaces = stats.get('namespaces', {})
            
            if settings.pinecone_namespace in namespaces:
                vector_count = namespaces[settings.pinecone_namespace].get('vector_count', 0)
                
                if vector_count > 0:
                    self.index.delete(delete_all=True, namespace=settings.pinecone_namespace)
                    logger.info(f"Namespace {settings.pinecone_namespace} limpo ({vector_count} vetores deletados)")
                else:
                    logger.info(f"Namespace {settings.pinecone_namespace} já está vazio")
            else:
                logger.info(f"Namespace {settings.pinecone_namespace} não existe ainda, será criado no primeiro upsert")
                
        except Exception as e:
            logger.warning(f"Aviso ao limpar namespace: {e}")

    def get_index_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do index"""
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "namespaces": stats.namespaces
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}