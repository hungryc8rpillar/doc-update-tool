from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class DocumentSection(BaseModel):
    id: str
    title: str
    content: str
    file_path: str
    section_type: str
    parent_section: Optional[str] = None

class UpdateSuggestion(BaseModel):
    section_id: str
    section_title: str
    file_path: str
    original_content: str
    suggested_content: str
    change_type: str
    confidence_score: float
    reasoning: str

class ChangeQuery(BaseModel):
    query: str
    ai_model: Optional[str] = None
    context: Optional[Dict] = None

class UpdateRequest(BaseModel):
    suggestions: List[UpdateSuggestion]
    approved_changes: List[str]

class ApproveRequest(BaseModel):
    approved_ids: List[str]

class RejectRequest(BaseModel):
    rejected_ids: List[str]
