# AI Email Intelligence
Sistema inteligente de gerenciamento e análise de emails usando IA, com classificação automática, busca semântica e agente conversacional.
### **Objetivo**
Automatizar a triagem e organização de emails através de IA, permitindo que você converse naturalmente com seus emails e execute ações como criar eventos no calendário, tudo através de uma interface amigável.
### **Funcionalidades Principais**
#### **Classificação Automática de Emails**

**Categorias:** Reunião/Evento, Boleto, Pessoal, Promoção
**Análise Inteligente:** Extrai informações relevantes como:
- Data de reuniões
- Valores de boletos
- Nível de prioridade (alta/média/baixa)
- Ações sugeridas
- Resumo automático

### **Chat com Agente de IA**

Pergunte sobre seus emails em linguagem natural
Exemplos:
- "Tenho reuniões marcadas esta semana?"
- "Mostre os boletos pendentes"
- "Quais emails importantes chegaram hoje?"
- "Marque uma reunião para amanhã às 14h"

### **Busca Semântica (RAG)**

Busca emails por significado, não apenas palavras-chave
Usa embeddings vetoriais no Pinecone
Contexto completo para respostas mais precisas

### **Integração com Google Calendar**

Crie eventos automaticamente via chat
Sincronização com sua agenda do Google

### **Arquitetura**
```
┌─────────────────┐
│  Streamlit UI   │  ← Interface web do usuário
└────────┬────────┘
         │
┌────────▼────────┐
│    FastAPI      │
│  ├── /emails   │  ← Processamento de emails
│  ├── /chat     │  ← Chat com agente
│  └── /calendar │  ← Criação de eventos
└────────┬────────┘
         │
┌────────┴──────────────────────────┐
│                                   │
▼          ▼          ▼             ▼
┌──────┐ ┌──────┐ ┌──────────┐ ┌──────────┐
│Gmail │ │Groq  │ │Pinecone  │ │Google    │
│ API  │ │ LLM  │ │  (RAG)   │ │Calendar  │
└──────┘ └──────┘ └──────────┘ └──────────┘
```

### **Estrutura**
```
ai-email-intelligence/
│
├── app/
│   ├── api/
│   │   ├── email_routes.py       # Endpoints de emails
│   │   ├── chat_routes.py        # Endpoints de chat
│   │   └── calendar_routes.py    # Endpoints de calendário
│   │
│   ├── services/
│   │   ├── gmail_service.py      # Integração Gmail API
│   │   ├── email_service.py      # Classificação e processamento
│   │   ├── rag_service.py        # Busca vetorial (Pinecone)
│   │   ├── agent_service.py      # Agente IA (LangGraph)
│   │   ├── calendar_service.py   # Integração Google Calendar
│   │   ├── cache_service.py      # Cache de classificações
│   │   ├── reranker_service.py   # Reranking de resultados
│   │   └── query_expansion_service.py  # Expansão de queries
│   │
│   ├── models/
│   │   └── schemas.py            # Modelos Pydantic
│   │
│   ├── config.py                 # Configurações centralizadas
│   └── main.py                   # Aplicação FastAPI
│
├── ui/
│   └── streamlit_app.py          # Interface Streamlit
│
├── data/
│   ├── cache/
│   │   └── classification_cache.json
│   └── emails-processed/
│       └── processed.json
│
├── credentials.json              # Credenciais Google API
├── token.json                    # Token Gmail
├── token_calendar.json           # Token Calendar
├── .env                          # Variáveis de ambiente
├── requirements.txt              # Dependências Python
├── docker-compose.yml            # Orquestração Docker
└── README.md
```

### **Tecnologias Utilizadas Backend**

**FastAPI:** Framework web assíncrono
**LangChain + LangGraph:** Orquestração do agente de IA
**Groq:** API de LLM (Llama 3 70B)
**Sentence Transformers:** Geração de embeddings

### **Armazenamento e Busca**

**Pinecone:** Banco de dados vetorial para RAG
**JSON Local:** Cache de emails processados

### **APIs Externas**

**Gmail API:** Leitura de emails
**Google Calendar API:** Criação de eventos

### **Frontend**

**Streamlit:** Interface web interativa

### **Como Executar**
**Pré-requisitos**

1. Python 3.10+
2. Conta Google com Gmail e Calendar habilitados
3. Chaves de API:

- Groq API Key
- Pinecone API Key

**Configuração**
1. Clone o repositório
clone https://github.com/seu-usuario/ai-email-intelligence.git
cd ai-email-intelligence

2. Instale as dependências
pip install -r requirements.txt

3. Configure as credenciais do Google

Acesse Google Cloud Console
Crie um projeto e habilite as APIs:

- Gmail API
- Google Calendar API

Baixe o arquivo credentials.json e coloque na raiz do projeto

4. Configure as variáveis de ambiente
Crie um arquivo .env na raiz:

# Groq Configuration
GROQ_API_KEY=seu_groq_api_key_aqui
GROQ_MODEL=llama3-70b-8192
GROQ_TEMPERATURE=0.7
GROQ_MAX_TOKENS=2048

# Pinecone Configuration
PINECONE_API_KEY=seu_pinecone_api_key_aqui
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=rag-platform
PINECONE_NAMESPACE=default

# Email Processing
DAYS_TO_KEEP=7
EMAILS_PROCESSED_FILE=data/emails-processed/processed.json

# RAG Settings
CHUNK_SIZE=500
CHUNK_OVERLAP=100
RETRIEVAL_TOP_K=10
SIMILARITY_THRESHOLD=0.7

5. Execute o backend
uvicorn app.main:app --reload --port 8000

6. Execute o frontend (em outro terminal)
streamlit run ui/streamlit_app.py

7. Acesse a aplicação

Frontend: http://localhost:8501
API: http://localhost:8000
Documentação API: http://localhost:8000/docs
