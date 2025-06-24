from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Add the app directory to Python path for imports
sys.path.append(os.path.dirname(__file__))

from app.services.doc_parser import DocumentationParser

app = FastAPI(title="Documentation Update Tool")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global documentation parser instance - handle Windows paths
docs_path = os.path.join(os.path.dirname(__file__), "..", "data", "documentation")
docs_path = os.path.abspath(docs_path)  # Convert to absolute path
doc_parser = DocumentationParser(docs_path)

@app.on_event("startup")
async def startup_event():
    """Initialize documentation parsing on startup"""
    print(f"Looking for documentation in: {docs_path}")
    if os.path.exists(docs_path):
        print("Parsing documentation...")
        sections = doc_parser.parse_markdown_files()
        print(f"Parsed {len(sections)} documentation sections")
    else:
        print(f"Documentation path not found: {docs_path}")

@app.get("/")
async def root():
    return {"message": "Documentation Update Tool API"}

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy", 
        "sections_loaded": len(doc_parser.get_sections()),
        "docs_path": docs_path,
        "path_exists": os.path.exists(docs_path)
    }
