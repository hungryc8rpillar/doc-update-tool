from fastapi import APIRouter, Query
from typing import List
from app.schemas_documentation import DocumentSection, ChangeQuery, UpdateSuggestion, ApproveRequest, RejectRequest
from app.services.doc_parser import DocumentationParser
from app.services.ai_analyzer import ai_analyzer
from app.services.enhanced_search import enhanced_search
from app.services.update_manager import update_manager
import os

router = APIRouter(prefix="/api/documentation", tags=["documentation"])

# Initialize parser
docs_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "documentation")
docs_path = os.path.abspath(docs_path)
doc_parser = DocumentationParser(docs_path)

# Load documentation on startup
sections_loaded = False

@router.get("/health")
async def documentation_health():
    global sections_loaded
    if not sections_loaded:
        if os.path.exists(docs_path):
            sections = doc_parser.parse_markdown_files()
            sections_loaded = True
            print(f"Loaded {len(sections)} documentation sections")
    
    return {
        "status": "healthy",
        "sections_loaded": len(doc_parser.get_sections()),
        "docs_path": docs_path,
        "path_exists": os.path.exists(docs_path),
        "ai_enabled": bool(os.getenv("OPENAI_API_KEY"))
    }

@router.get("/sections", response_model=List[DocumentSection])
async def get_all_sections():
    """Get all documentation sections"""
    global sections_loaded
    if not sections_loaded:
        doc_parser.parse_markdown_files()
        sections_loaded = True
    return doc_parser.get_sections()

@router.get("/search/{keyword}")
async def search_documentation(keyword: str, enhanced: bool = True):
    """Search documentation for specific keywords"""
    global sections_loaded
    if not sections_loaded:
        doc_parser.parse_markdown_files()
        sections_loaded = True
    
    all_sections = doc_parser.get_sections()
    
    if enhanced:
        # Use enhanced semantic search
        results = enhanced_search.semantic_search(keyword, all_sections, max_results=10)
    else:
        # Use simple keyword search
        results = doc_parser.find_sections_by_keyword(keyword)[:10]
    
    return {
        "keyword": keyword,
        "enhanced": enhanced,
        "found": len(results),
        "sections": results
    }

@router.get("/categories")
async def get_documentation_categories():
    """Get documentation sections organized by categories"""
    global sections_loaded
    if not sections_loaded:
        doc_parser.parse_markdown_files()
        sections_loaded = True
    
    all_sections = doc_parser.get_sections()
    categories = enhanced_search.categorize_sections(all_sections)
    
    # Return summary with counts
    category_summary = {}
    for category, sections in categories.items():
        category_summary[category] = {
            "count": len(sections),
            "sections": sections[:5]  # Return first 5 sections of each category
        }
    
    return category_summary

@router.get("/sections/{section_id}/related")
async def get_related_sections(section_id: str, max_results: int = 5):
    """Get sections related to a specific section"""
    global sections_loaded
    if not sections_loaded:
        doc_parser.parse_markdown_files()
        sections_loaded = True
    
    all_sections = doc_parser.get_sections()
    
    # Find the target section
    target_section = None
    for section in all_sections:
        if section.id == section_id:
            target_section = section
            break
    
    if not target_section:
        return {"error": "Section not found", "section_id": section_id}
    
    related = enhanced_search.find_related_sections(target_section, all_sections, max_results)
    
    return {
        "target_section": target_section.title,
        "related_count": len(related),
        "related_sections": related
    }

@router.post("/analyze", response_model=List[UpdateSuggestion])
async def analyze_change(query: ChangeQuery):
    """Analyze a change query and suggest documentation updates using AI"""
    global sections_loaded
    if not sections_loaded:
        doc_parser.parse_markdown_files()
        sections_loaded = True
    
    # Use enhanced search to find relevant sections
    all_sections = doc_parser.get_sections()
    relevant_sections = enhanced_search.semantic_search(query.query, all_sections, max_results=5)
    
    if not relevant_sections:
        return []
    
    # Use AI to analyze and generate suggestions
    suggestions = await ai_analyzer.analyze_change_request(query, relevant_sections)
    
    return suggestions

@router.post("/analyze-and-save")
async def analyze_and_save_changes(query: ChangeQuery):
    """Analyze changes and save suggestions for review"""
    global sections_loaded
    if not sections_loaded:
        doc_parser.parse_markdown_files()
        sections_loaded = True
    # Get relevant sections and AI suggestions
    all_sections = doc_parser.get_sections()
    relevant_sections = enhanced_search.semantic_search(query.query, all_sections, max_results=20)
    if not relevant_sections:
        return {"error": "No relevant sections found", "query": query.query, "status": "error"}
    suggestions = await ai_analyzer.analyze_change_request(query, relevant_sections)
    if not suggestions:
        return {"error": "No suggestions generated", "query": query.query, "status": "error"}
    # Save suggestions as pending updates
    batch_id = update_manager.save_pending_updates(suggestions, query.query)
    return {
        "batch_id": batch_id,
        "query": query.query,
        "suggestions_count": len(suggestions),
        "suggestions": suggestions,
        "status": "saved_for_review"
    }

@router.get("/pending-updates")
async def get_pending_updates(batch_id: str = None):
    """Get pending updates for review"""
    updates = update_manager.get_pending_updates(batch_id)
    return {
        "pending_updates": updates,
        "count": len(updates)
    }

@router.post("/approve-suggestions")
async def approve_suggestions(batch_id: str = Query(...), request: ApproveRequest = None):
    """Approve specific suggestions"""
    if request is None:
        request = ApproveRequest(approved_ids=[])
    result = update_manager.approve_suggestions(batch_id, request.approved_ids)
    return result

@router.post("/reject-suggestions") 
async def reject_suggestions(batch_id: str = Query(...), request: RejectRequest = None):
    """Reject specific suggestions"""
    if request is None:
        request = RejectRequest(rejected_ids=[])
    result = update_manager.reject_suggestions(batch_id, request.rejected_ids)
    return result

@router.get("/applied-updates")
async def get_applied_updates():
    """Get all applied updates"""
    updates = update_manager.get_applied_updates()
    return {
        "applied_updates": updates,
        "count": len(updates)
    }

@router.get("/update-statistics")
async def get_update_statistics():
    """Get statistics about documentation updates"""
    return update_manager.get_update_statistics()

@router.post("/revert-all-updates")
async def revert_all_updates():
    """Revert all successfully applied updates."""
    result = update_manager.revert_all_updates()
    return result
