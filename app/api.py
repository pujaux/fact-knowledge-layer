import os
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import UPLOAD_DIR
from app.pipeline import process_document, build_relationships

app = FastAPI(title="Fact Knowledge Layer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF, extract facts from it, and re-run cross-document
    relationship discovery across everything ingested so far."""
    dest_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    ingest_result = process_document(dest_path, file.filename)
    relation_result = build_relationships()

    return {"ingested": ingest_result, "relationships": relation_result}


@app.get("/documents")
def list_documents():
    return db.list_documents()


@app.get("/facts")
def list_facts():
    return db.get_all_facts()


@app.get("/relationships")
def list_relationships(relation: str = None):
    return db.get_relationships(relation_filter=relation)


@app.post("/relationships/rebuild")
def rebuild_relationships():
    """Manually re-run relationship discovery without uploading a new file."""
    return build_relationships()
