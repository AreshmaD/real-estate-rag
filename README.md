# Real Estate RAG Assistant

A real estate research assistant that answers questions using uploaded property documents and market reports.

The project uses Retrieval-Augmented Generation (RAG) to retrieve relevant evidence from PostgreSQL with pgvector and generate source-grounded answers through Ollama.

The current version supports property-specific research using synthetic sample properties. It is being developed toward a broader property comparison and decision-support tool for real estate agents and home buyers.

## Features

- PDF and TXT document ingestion
- Page-aware PDF text extraction
- Text chunking with document metadata
- Embeddings generated with sentence-transformers
- Vector storage in PostgreSQL with pgvector
- Semantic retrieval with keyword-based ranking boosts
- Document-diverse retrieval for general questions
- Property-specific document filtering
- Multiple supporting passages from a selected property
- LLM-generated answers with document and page references
- Instructions for distinguishing facts, reported statements, and unknowns
- FastAPI backend
- Streamlit frontend
- Retrieval evaluation notebook

## Example Questions

### Property Research

- What is the asking price and size of SYN-001?
- Do the documents establish whether SYN-001’s basement water issue was permanently fixed?
- What inspection follow-up is recommended for SYN-003?
- What information is missing from the selected property’s documents?

### Conflicting Information

- What monthly HOA fee should be used for SYN-002 as of November 8, 2026?
- Why does the listing show a different HOA fee from the association notice?

### Market Research

- What reporting period does this market report cover?
- What affordability risks are mentioned?
- Which reports discuss rental demand or insurance costs?

Answers depend on the evidence available in the indexed documents.

## How It Works

### Offline Indexing

```text
PDF / TXT Documents
        ↓
Text Extraction
        ↓
Chunking and Metadata
        ↓
Embedding Generation
        ↓
PostgreSQL + pgvector
```

### Online Questions

```text
Question + Optional Property Selection
        ↓
Query Embedding
        ↓
Document Filtering
        ↓
Vector Candidate Retrieval
        ↓
Keyword Boosting and Ranking
        ↓
Relevant Evidence
        ↓
Ollama Answer Generation
        ↓
Answer + Source References
```

## Retrieval Approach

The retriever first selects candidates using vector similarity, then applies keyword-based boosting within that candidate set.

For general questions, document diversity limits how many chunks come from each document.

For property-specific questions, retrieval is restricted to the selected property’s document and can return multiple passages from that document.

This is currently vector retrieval with keyword reranking. Independent keyword candidate retrieval and more advanced ranking are planned.

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python |
| Backend | FastAPI |
| Frontend | Streamlit |
| Database | PostgreSQL 16 |
| Vector extension | pgvector |
| Database access | SQLAlchemy |
| PostgreSQL driver | psycopg |
| Embeddings | sentence-transformers |
| Embedding model | all-MiniLM-L6-v2 |
| Local LLM runtime | Ollama |
| Answer model | gpt-oss:20b |
| PDF extraction | pypdf |
| Evaluation | Jupyter Notebook |

## Project Structure

```text
real-estate-rag/
├── app/
│   ├── api.py
│   ├── chunking.py
│   ├── config.py
│   ├── database.py
│   ├── embed.py
│   ├── generate.py
│   ├── ingest.py
│   ├── load_service.py
│   └── retrieve.py
├── data/
│   └── raw/
├── images/
├── notebooks/
├── scripts/
├── ui/
│   └── streamlit_app.py
├── .gitignore
├── README.md
├── requirements.txt
└── docker-compose.yml
```

## Setup

The commands below target macOS and Linux.

### 1. Clone the Repository

```bash
git clone https://github.com/AreshmaD/real-estate-rag.git
cd real-estate-rag
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt
```

The PostgreSQL driver must match the SQLAlchemy connection configuration. A `postgresql+psycopg` connection requires `psycopg`, available through:

```bash
./venv/bin/python -m pip install "psycopg[binary]"
```

### 4. Configure Database Access

The development setup uses:

| Setting | Value |
|---|---|
| Host | 127.0.0.1 |
| Host port | 55432 |
| Container port | 5432 |
| Database | real_estate_rag |
| User | postgres |

Configure the application’s database connection to match your Docker setup.

The Compose port mapping should be:

```yaml
ports:
  - "127.0.0.1:55432:5432"
```

Keep database passwords in an ignored local configuration file or environment variable. Do not commit credentials to the repository.

Changing `POSTGRES_PASSWORD` in Docker Compose does not reset the password of an already initialized database.

### 5. Start PostgreSQL

Make sure Docker Desktop is running.

```bash
docker compose up -d
docker compose ps
```

Check the published port:

```bash
docker compose port postgres 5432
```

Expected:

```text
127.0.0.1:55432
```

### 6. Enable pgvector

```bash
docker compose exec postgres psql \
  -U postgres \
  -d real_estate_rag \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 7. Prepare Ollama

Install and start Ollama, then download the configured model:

```bash
ollama pull gpt-oss:20b
```

In `app/config.py`, the answer model should be:

```python
LLM_MODEL = "gpt-oss:20b"
```

Model speed and memory usage depend on the hardware, context length, and other running applications.

### 8. Start the API

From the repository root:

```bash
./venv/bin/python -m uvicorn app.api:app --reload
```

Health check:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{"status": "ok"}
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

The health endpoint confirms that the API is running. It does not verify database connectivity or Ollama availability.

### 9. Start Streamlit

In a second terminal:

```bash
cd real-estate-rag
./venv/bin/python -m streamlit run ui/streamlit_app.py
```

Open the local URL shown in the terminal, typically:

```text
http://localhost:8501
```

## Adding Documents

Place supported PDFs and TXT files directly inside:

```text
data/raw/
```

Then click **Ingest Documents** in Streamlit.

The current loader scans that directory directly; it does not recursively scan nested folders.

The first ingestion may download the embedding model. Documents whose filenames already exist in the database are skipped, so changing a file under the same name does not automatically reindex it.

Do not place answer keys or evaluation expectations in the ingestion directory.

## Property Selection

The current sample workflow maps property IDs to document filenames:

| Property | Document |
|---|---|
| SYN-001 | syn-001-property-packet.pdf |
| SYN-002 | syn-002-property-packet.pdf |
| SYN-003 | syn-003-property-packet.pdf |

Selecting a property restricts retrieval to its associated document.

Selecting **All documents** searches the indexed corpus using document-diverse retrieval.

The mapping is currently defined in application code. Database-backed property records and support for multiple documents per property are planned.

## Synthetic Sample Data

The development sample contains three fictional properties and a fictional market report.

It includes:

- Property facts
- Seller disclosures
- Inspection observations
- HOA information
- Conflicting fee information
- Missing insurance inputs
- Current and historical market statistics

A development ingestion successfully processed four sample PDFs into 28 chunks.

All sample properties, addresses, financial inputs, and market statistics are fictional. They must not be used as evidence about actual homes or markets.

Keep synthetic and real research corpora separate.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check API availability |
| POST | `/ingest` | Index documents from the configured directory |
| POST | `/ask` | Ask a question with optional property selection |

### Example Request

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Was the basement water issue permanently fixed?",
    "property_id": "SYN-001"
  }'
```

Omit `property_id`, or set it to `null`, to search all indexed documents.

Responses include the answer and retrieved source metadata such as document name, page number, chunk ID, ranking scores, and text preview.

Returned sources are retrieved evidence; their presence does not automatically prove that every generated claim is supported.

## Evaluation

### Historical Retrieval Benchmark

An earlier small benchmark measured whether expected source documents appeared in the top three results.

| Configuration | Hit@3 |
|---|---:|
| Balanced small corpus | 100% |
| Corpus with a large Zillow PDF, baseline vector retrieval | 25% |
| Document-diverse retrieval | 50% |
| Hybrid ranking | 75% |

These results describe the earlier benchmark. They have not been rerun for the updated property-specific workflow or the current answer model.

The main finding was that a large document could dominate retrieval in a small corpus. Document diversity and keyword-based boosting improved retrieval on that test set.

### Current Manual Validation

The updated workflow was checked using SYN-001’s disclosure and inspection evidence.

The latest observed answer:

- Restricted retrieved sources to SYN-001.
- Used evidence from multiple pages.
- Correctly stated that permanent repair status was not established.
- Distinguished seller statements from inspection observations.
- Referenced the relevant document pages.

This is a single manual case, not evidence of overall system accuracy.

Further evaluation should cover:

- Conflicting dates and figures
- Missing inputs
- Incorrect property attribution
- Citation support
- Unsupported conclusions
- Irrelevant questions
- Repeated-run consistency
- Response time

## Current Limitations

- Property-to-document relationships are hardcoded.
- Documents must be placed in a local folder before ingestion.
- Keyword boosting only reranks vector-selected candidates.
- Fixed character-based chunks can split sentences and qualifications.
- Generated citations and claims are not automatically verified.
- The model can still omit qualifications or include irrelevant information.
- Updating an existing document requires an explicit reindexing workflow.
- Scanned PDFs may require OCR, which is not implemented.
- Ownership cost calculations are not integrated into the application.
- Authentication and multi-user workspace isolation are not implemented.
- The research-agent workflow is planned and has not been implemented.

The application is a local development prototype. Do not expose it publicly or upload sensitive client documents without adding appropriate access controls and data handling.

## Roadmap

### Evidence Foundation

- Upload documents through the UI
- Track ingestion status
- Add database-backed property and document relationships
- Open cited pages in a source viewer
- Support document replacement and deletion

### Property Comparison

- Review and correct extracted facts
- Calculate ownership costs using deterministic formulas
- Display assumptions and missing inputs
- Compare two or three properties side by side

### Research Agent

- Break complex questions into focused searches
- Inspect surrounding source context
- Use bounded tool calls and retrieval rounds
- Identify conflicting evidence and unresolved questions
- Generate structured, cited research briefs

### Reporting and Validation

- Export reviewed comparison reports
- Expand the evaluation dataset
- Measure citation accuracy and preparation time
- Add authentication and workspace isolation
- Pilot with appropriately shared real documents

### Seller Tools

- Import authorized comparable sales
- Support agent-reviewed pricing scenarios
- Estimate seller net proceeds
- Compare offers and concessions

## Data Sources

Real-world research documents should be obtained from their original publishers or supplied with appropriate permission.

Do not redistribute copyrighted reports or private transaction documents without authorization. Keep private uploads out of version control.

Market reports alone are insufficient for property-level valuation. Comparable sales, property condition, and other relevant records are needed for that workflow.

## Troubleshooting

### Database Password Authentication Failed

Confirm that:

- The application uses the correct host port.
- The configured password matches the existing database role.
- Another local PostgreSQL instance is not receiving the connection.

A password change in Compose environment settings does not update an existing database role.

### Database Port Already Allocated

Check the host port mapping in `docker-compose.yml`. This development setup uses host port `55432` to avoid common local PostgreSQL conflicts.

### Python Module Not Found

Use the virtual environment explicitly:

```bash
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python -m uvicorn app.api:app --reload
```

### GET /ingest Returns 405

Ingestion requires a POST request. Use the Streamlit button or the interactive API documentation.

### Streamlit Request Times Out

The model may still be loading or generating. Review the API terminal and adjust the request timeout if appropriate. A frontend timeout does not necessarily stop backend processing.

## Stopping the Application

Press `Control+C` in the API and Streamlit terminals.

Stop PostgreSQL while preserving its data:

```bash
docker compose stop
```

## Project Purpose

This project demonstrates evidence-grounded real estate research using RAG, property-scoped retrieval, and local LLM inference.

It supports research and human review. It does not establish structural safety, legal conclusions, lending eligibility, future investment returns, or definitive property value.
