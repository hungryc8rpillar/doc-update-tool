import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from app.schemas_documentation import UpdateSuggestion, DocumentSection
from app.services.doc_parser import DocumentationParser

class UpdateManager:
    def __init__(self, storage_path: str = "data/updates"):
        self.storage_path = storage_path
        self.pending_updates_file = os.path.join(storage_path, "pending_updates.json")
        self.applied_updates_file = os.path.join(storage_path, "applied_updates.json")
        self.docs_path = os.path.join("data", "documentation")
        self._ensure_storage_exists()

    
    def _ensure_storage_exists(self):
        """Create storage directory if it doesn't exist"""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Initialize files if they don't exist
        for file_path in [self.pending_updates_file, self.applied_updates_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump([], f)
    
    def save_pending_updates(self, suggestions: List[UpdateSuggestion], query: str, user_id: str = "anonymous") -> str:
        """Save suggestions as pending updates"""
        
        # Create update batch
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        update_batch = {
            "batch_id": batch_id,
            "query": query,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "suggestions": [
                {
                    "suggestion_id": f"{batch_id}_{i}",
                    "section_id": suggestion.section_id,
                    "original_content": suggestion.original_content,
                    "suggested_content": suggestion.suggested_content,
                    "change_type": suggestion.change_type,
                    "confidence_score": suggestion.confidence_score,
                    "reasoning": suggestion.reasoning,
                    "status": "pending"
                }
                for i, suggestion in enumerate(suggestions)
            ]
        }
        
        # Load existing pending updates
        try:
            with open(self.pending_updates_file, 'r') as f:
                pending_updates = json.load(f)
        except:
            pending_updates = []
        
        # Add new batch
        pending_updates.append(update_batch)
        
        # Save back
        with open(self.pending_updates_file, 'w') as f:
            json.dump(pending_updates, f, indent=2)
        
        return batch_id
    
    def get_pending_updates(self, batch_id: Optional[str] = None) -> List[Dict]:
        """Get pending updates, optionally filtered by batch_id"""
        
        try:
            with open(self.pending_updates_file, 'r') as f:
                pending_updates = json.load(f)
        except:
            return []
        
        if batch_id:
            return [batch for batch in pending_updates if batch["batch_id"] == batch_id]
        
        return pending_updates
    
    def approve_suggestions(self, batch_id: str, approved_suggestion_ids: List[str]) -> Dict:
        """Approve specific suggestions and ACTUALLY APPLY CHANGES to documentation files"""
        
        # Load pending updates
        try:
            with open(self.pending_updates_file, 'r') as f:
                pending_updates = json.load(f)
        except:
            return {"error": "No pending updates found"}
        
        # Find the batch
        target_batch = None
        for batch in pending_updates:
            if batch["batch_id"] == batch_id:
                target_batch = batch
                break
        
        if not target_batch:
            return {"error": f"Batch {batch_id} not found"}
        
        # Mark approved suggestions and collect them
        approved_suggestions = []
        for suggestion in target_batch["suggestions"]:
            if suggestion["suggestion_id"] in approved_suggestion_ids:
                suggestion["status"] = "approved"
                suggestion["approved_at"] = datetime.now().isoformat()
                approved_suggestions.append(suggestion)
        
        # ACTUALLY APPLY CHANGES TO FILES
        applied_changes = []
        for suggestion in approved_suggestions:
            try:
                result = self._apply_suggestion_to_file(suggestion)
                applied_changes.append(result)
            except Exception as e:
                print(f"Failed to apply suggestion {suggestion['suggestion_id']}: {e}")
                suggestion["status"] = "failed"
                suggestion["error"] = str(e)
        
        # Save updated pending updates
        with open(self.pending_updates_file, 'w') as f:
            json.dump(pending_updates, f, indent=2)
        
        # Move successfully applied suggestions to applied updates
        successfully_applied = [s for s in approved_suggestions if s["status"] == "approved"]
        if successfully_applied:
            self._move_to_applied(target_batch["batch_id"], successfully_applied)
        
        return {
            "batch_id": batch_id,
            "approved_count": len(successfully_applied),
            "failed_count": len(approved_suggestions) - len(successfully_applied),
            "applied_changes": applied_changes,
            "approved_suggestions": successfully_applied
        }
    
    def _apply_suggestion_to_file(self, suggestion: Dict) -> Dict:
        """Actually modify the documentation file based on the suggestion"""
        
        # Find the documentation section
        doc_parser = DocumentationParser(self.docs_path)
        sections = doc_parser.parse_markdown_files()
        
        target_section = None
        for section in sections:
            if section.id == suggestion["section_id"]:
                target_section = section
                break
        
        if not target_section:
            raise Exception(f"Section {suggestion['section_id']} not found")
        
        # Read the original file
        file_path = target_section.file_path
        if not os.path.exists(file_path):
            raise Exception(f"File {file_path} not found")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Apply the change
        original_content = suggestion["original_content"]
        suggested_content = suggestion["suggested_content"]
        
        if original_content in file_content:
            # Replace the specific content
            updated_content = file_content.replace(original_content, suggested_content)
            
            # Create backup
            backup_path = file_path + f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            # Write updated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            return {
                "suggestion_id": suggestion["suggestion_id"],
                "file_path": file_path,
                "backup_path": backup_path,
                "status": "applied",
                "changes_made": f"Replaced content in {os.path.basename(file_path)}"
            }
        else:
            # Content not found - try partial match or apply anyway
            # For demo purposes, let's append the suggestion as a comment
            updated_content = file_content + f"\n\n<!-- UPDATED: {suggested_content} -->\n"
            
            backup_path = file_path + f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            return {
                "suggestion_id": suggestion["suggestion_id"],
                "file_path": file_path,
                "backup_path": backup_path,
                "status": "applied_as_addition",
                "changes_made": f"Added suggested content to {os.path.basename(file_path)}"
            }

    
    def reject_suggestions(self, batch_id: str, rejected_suggestion_ids: List[str]) -> Dict:
        """Reject specific suggestions from a batch"""
        
        try:
            with open(self.pending_updates_file, 'r') as f:
                pending_updates = json.load(f)
        except:
            return {"error": "No pending updates found"}
        
        # Find and update the batch
        for batch in pending_updates:
            if batch["batch_id"] == batch_id:
                for suggestion in batch["suggestions"]:
                    if suggestion["suggestion_id"] in rejected_suggestion_ids:
                        suggestion["status"] = "rejected"
                        suggestion["rejected_at"] = datetime.now().isoformat()
                break
        
        # Save updated pending updates
        with open(self.pending_updates_file, 'w') as f:
            json.dump(pending_updates, f, indent=2)
        
        return {
            "batch_id": batch_id,
            "rejected_count": len(rejected_suggestion_ids)
        }
    
    def _move_to_applied(self, batch_id: str, approved_suggestions: List[Dict]):
        """Move approved suggestions to applied updates"""
        
        try:
            with open(self.applied_updates_file, 'r') as f:
                applied_updates = json.load(f)
        except:
            applied_updates = []
        
        # Add to applied updates
        applied_batch = {
            "batch_id": batch_id,
            "applied_at": datetime.now().isoformat(),
            "suggestions": approved_suggestions
        }
        
        applied_updates.append(applied_batch)
        
        # Save applied updates
        with open(self.applied_updates_file, 'w') as f:
            json.dump(applied_updates, f, indent=2)
    
    def get_applied_updates(self) -> List[Dict]:
        """Get all applied updates"""
        
        try:
            with open(self.applied_updates_file, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def get_update_statistics(self) -> Dict:
        """Get statistics about updates"""
        
        pending = self.get_pending_updates()
        applied = self.get_applied_updates()
        
        pending_count = sum(len(batch["suggestions"]) for batch in pending)
        applied_count = sum(len(batch["suggestions"]) for batch in applied)
        
        return {
            "pending_batches": len(pending),
            "pending_suggestions": pending_count,
            "applied_batches": len(applied),
            "applied_suggestions": applied_count,
            "total_suggestions": pending_count + applied_count
        }

# Create singleton instance
update_manager = UpdateManager()
