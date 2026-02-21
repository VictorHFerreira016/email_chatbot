from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from app.models.schemas import EmailResponse
from app.services.email_service import EmailService

router = APIRouter(
    prefix="/emails",
    tags=["Emails"]
)

email_service = EmailService()

@router.post("/process/")
def process_emails() -> Dict[str, Any]:
    """
    Processa e classifica os e-mails dos últimos dias.
    """
    try:
        result = email_service.process_emails()
        return {
            "status": "success",
            "processed": result["processed"],
            "emails": result["emails"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[EmailResponse])
def get_all_emails():
    """
    Retorna todos os e-mails processados.
    """
    return email_service.get_all_emails()

@router.get("/category/{categoria}")
def get_by_category(categoria: str):
    """
    Retorna e-mails por categoria.
    Categorias válidas:
    - reuniao
    - boleto
    - pessoal
    - promocao
    """

    grouped = email_service.get_by_category()

    if categoria not in grouped:
        raise HTTPException(
            status_code=404,
            detail=f"Categoria '{categoria}' não encontrada"
        )

    return {
        "categoria": categoria,
        "total": len(grouped[categoria]),
        "emails": grouped[categoria]
    }

@router.get("/stats")
def get_stats():
    """
    Retorna estatísticas gerais.
    """
    emails = email_service.get_all_emails()
    grouped = email_service.get_by_category()

    return {
        "total_emails": len(emails),
        "reunioes": len(grouped.get("reuniao", [])),
        "boletos": len(grouped.get("boleto", [])),
        "pessoais": len(grouped.get("pessoal", [])),
        "promocoes": len(grouped.get("promocao", [])),
    }

@router.get("/debug/count")
def debug_email_count():
    """
    Endpoint de debug para ver quantos e-mails estão armazenados.
    """
    emails = email_service.get_all_emails()
    
    from app.services.rag_service import RAGService
    rag = RAGService()
    rag_stats = rag.get_index_stats()
    
    return {
        "emails_no_storage": len(emails),
        "emails_no_rag": rag_stats.get("total_vectors", 0),
        "rag_stats": rag_stats,
        "primeiro_email": emails[0] if emails else None
    }
