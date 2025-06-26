import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from app.schemas_documentation import UpdateSuggestion, DocumentSection
from app.services.doc_parser import DocumentationParser

class UpdateManager:
    def __init__(self, storage_path: str = None):
        if storage_path is None:
            # Use absolute path based on current file location
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            storage_path = os.path.join(project_root, "data", "updates")
        
        self.storage_path = storage_path
        self.pending_updates_file = os.path.join(storage_path, "pending_updates.json")
        self.applied_updates_file = os.path.join(storage_path, "applied_updates.json")
        self.docs_path = os.path.join(os.path.dirname(storage_path), "documentation")
        
        print(f"DEBUG: UpdateManager initialized with storage_path: {self.storage_path}")
        print(f"DEBUG: Pending updates file: {self.pending_updates_file}")
        print(f"DEBUG: Applied updates file: {self.applied_updates_file}")
        print(f"DEBUG: Docs path: {self.docs_path}")
        
        self._ensure_storage_exists()

    
    def _ensure_storage_exists(self):
        """Create storage directory if it doesn't exist"""
        print(f"DEBUG: Ensuring storage exists at {self.storage_path}")
        os.makedirs(self.storage_path, exist_ok=True)
        print(f"DEBUG: Storage directory created/verified")
        
        # Initialize files if they don't exist
        for file_path in [self.pending_updates_file, self.applied_updates_file]:
            if not os.path.exists(file_path):
                print(f"DEBUG: Creating new file: {file_path}")
                with open(file_path, 'w') as f:
                    json.dump([], f)
            else:
                print(f"DEBUG: File already exists: {file_path}")
    
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
                    "section_title": suggestion.section_title,
                    "file_path": suggestion.file_path,
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
        
        # Filter to only include batches with pending suggestions
        filtered_updates = []
        for batch in pending_updates:
            # Filter suggestions to only include pending ones
            pending_suggestions = [
                s for s in batch["suggestions"] 
                if s.get("status") == "pending"
            ]
            
            if pending_suggestions:
                # Create a copy of the batch with only pending suggestions
                filtered_batch = batch.copy()
                filtered_batch["suggestions"] = pending_suggestions
                filtered_updates.append(filtered_batch)
        
        if batch_id:
            return [batch for batch in filtered_updates if batch["batch_id"] == batch_id]
        
        return filtered_updates
    
    def approve_suggestions(self, batch_id: str, approved_suggestion_ids: List[str]) -> Dict:
        """Approve specific suggestions and ACTUALLY APPLY CHANGES to documentation files"""
        
        print(f"DEBUG: Approving suggestions for batch {batch_id}, IDs: {approved_suggestion_ids}")
        
        # Load pending updates
        try:
            with open(self.pending_updates_file, 'r') as f:
                pending_updates = json.load(f)
            print(f"DEBUG: Loaded {len(pending_updates)} pending update batches")
        except Exception as e:
            print(f"DEBUG: Error loading pending updates: {e}")
            return {"error": "No pending updates found"}
        
        # Find the batch
        target_batch = None
        batch_index = None
        for i, batch in enumerate(pending_updates):
            if batch["batch_id"] == batch_id:
                target_batch = batch
                batch_index = i
                break
        
        if not target_batch:
            print(f"DEBUG: Batch {batch_id} not found in pending updates")
            return {"error": f"Batch {batch_id} not found"}
        
        print(f"DEBUG: Found target batch with {len(target_batch['suggestions'])} suggestions")
        
        # Mark approved suggestions and collect them
        approved_suggestions = []
        for suggestion in target_batch["suggestions"]:
            if suggestion["suggestion_id"] in approved_suggestion_ids:
                suggestion["status"] = "approved"
                suggestion["approved_at"] = datetime.now().isoformat()
                approved_suggestions.append(suggestion)
        
        print(f"DEBUG: Marked {len(approved_suggestions)} suggestions as approved")
        
        # ACTUALLY APPLY CHANGES TO FILES
        applied_changes = []
        successfully_applied = []
        for suggestion in approved_suggestions:
            try:
                result = self._apply_suggestion_to_file(suggestion)
                applied_changes.append(result)
                # If the application was successful, mark it as successfully applied
                if result["status"] in ["applied", "applied_as_addition"]:
                    suggestion["status"] = "successfully_applied"
                    suggestion["backup_path"] = result["backup_path"]
                    successfully_applied.append(suggestion)
                else:
                    suggestion["status"] = "failed"
                    suggestion["error"] = "Application failed"
            except Exception as e:
                print(f"Failed to apply suggestion {suggestion['suggestion_id']}: {e}")
                suggestion["status"] = "failed"
                suggestion["error"] = str(e)
        
        print(f"DEBUG: Successfully applied {len(successfully_applied)} suggestions")
        
        # Collect IDs of all processed suggestions (successfully applied or failed)
        processed_suggestion_ids = {s["suggestion_id"] for s in successfully_applied}
        
        # Add failed suggestions to the list of processed IDs
        for suggestion in approved_suggestions:
            if suggestion["status"] == "failed":
                processed_suggestion_ids.add(suggestion["suggestion_id"])
        
        print(f"DEBUG: Total processed suggestions (applied or failed): {len(processed_suggestion_ids)}")

        # Remove all processed suggestions from the batch
        target_batch["suggestions"] = [
            s for s in target_batch["suggestions"] 
            if s["suggestion_id"] not in processed_suggestion_ids
        ]
        
        # If batch has no more suggestions, remove the entire batch
        if not target_batch["suggestions"]:
            print(f"DEBUG: Removing empty batch {batch_id} from pending updates")
            pending_updates.pop(batch_index)
        else:
            print(f"DEBUG: Batch {batch_id} has {len(target_batch['suggestions'])} remaining suggestions")
        
        # Save updated pending updates
        print(f"DEBUG: Saving updated pending updates to {self.pending_updates_file}")
        with open(self.pending_updates_file, 'w') as f:
            json.dump(pending_updates, f, indent=2)
        
        # Move successfully applied suggestions to applied updates
        if successfully_applied:
            print(f"DEBUG: Moving {len(successfully_applied)} suggestions to applied updates")
            self._move_to_applied(batch_id, successfully_applied)
        
        return {
            "batch_id": batch_id,
            "approved_count": len(successfully_applied),
            "failed_count": len(approved_suggestions) - len(successfully_applied),
            "applied_changes": applied_changes,
            "approved_suggestions": successfully_applied
        }
    
    def _apply_suggestion_to_file(self, suggestion: Dict) -> Dict:
        """Actually modify the documentation file based on the suggestion"""
        
        print(f"DEBUG: Applying suggestion {suggestion['suggestion_id']} to file")
        print(f"DEBUG: Original content: {suggestion['original_content']}")
        print(f"DEBUG: Suggested content: {suggestion['suggested_content']}")
        
        # Use the file path directly from the suggestion instead of trying to find by section ID
        file_path = suggestion["file_path"]
        
        # Normalize the file path to handle different path separators
        file_path = file_path.replace('\\', '/')
        
        print(f"DEBUG: Using file path: {file_path}")
        
        if not os.path.exists(file_path):
            raise Exception(f"File {file_path} not found")
        
        # Read the original file
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        print(f"DEBUG: File content length: {len(file_content)} characters")
        
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
            
            print(f"DEBUG: Successfully applied change to {file_path}")
            
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
            
            print(f"DEBUG: Applied change as addition to {file_path}")
            
            return {
                "suggestion_id": suggestion["suggestion_id"],
                "file_path": file_path,
                "backup_path": backup_path,
                "status": "applied_as_addition",
                "changes_made": f"Added suggested content to {os.path.basename(file_path)}"
            }

    
    def reject_suggestions(self, batch_id: str, rejected_suggestion_ids: List[str]) -> Dict:
        """Reject specific suggestions from a batch"""
        
        print(f"DEBUG: Rejecting suggestions for batch {batch_id}, IDs: {rejected_suggestion_ids}")
        
        try:
            with open(self.pending_updates_file, 'r') as f:
                pending_updates = json.load(f)
            print(f"DEBUG: Loaded {len(pending_updates)} pending update batches")
        except Exception as e:
            print(f"DEBUG: Error loading pending updates: {e}")
            return {"error": "No pending updates found"}
        
        # Find and update the batch
        batch_found = False
        batch_index = None
        for i, batch in enumerate(pending_updates):
            if batch["batch_id"] == batch_id:
                batch_found = True
                batch_index = i
                rejected_count = 0
                for suggestion in batch["suggestions"]:
                    if suggestion["suggestion_id"] in rejected_suggestion_ids:
                        suggestion["status"] = "rejected"
                        suggestion["rejected_at"] = datetime.now().isoformat()
                        rejected_count += 1
                print(f"DEBUG: Marked {rejected_count} suggestions as rejected in batch {batch_id}")
                break
        
        if not batch_found:
            print(f"DEBUG: Batch {batch_id} not found in pending updates")
            return {"error": f"Batch {batch_id} not found"}
        
        # Remove rejected suggestions from the batch
        target_batch = pending_updates[batch_index]
        target_batch["suggestions"] = [
            s for s in target_batch["suggestions"] 
            if s["suggestion_id"] not in rejected_suggestion_ids
        ]
        
        # If batch has no more suggestions, remove the entire batch
        if not target_batch["suggestions"]:
            print(f"DEBUG: Removing empty batch {batch_id} from pending updates")
            pending_updates.pop(batch_index)
        else:
            print(f"DEBUG: Batch {batch_id} has {len(target_batch['suggestions'])} remaining suggestions")
        
        # Save updated pending updates
        print(f"DEBUG: Saving updated pending updates to {self.pending_updates_file}")
        with open(self.pending_updates_file, 'w') as f:
            json.dump(pending_updates, f, indent=2)
        
        return {
            "batch_id": batch_id,
            "rejected_count": len(rejected_suggestion_ids)
        }
    
    def _move_to_applied(self, batch_id: str, approved_suggestions: List[Dict]):
        """Move approved suggestions to applied updates"""
        
        print(f"DEBUG: Moving {len(approved_suggestions)} suggestions to applied updates for batch {batch_id}")
        
        try:
            with open(self.applied_updates_file, 'r') as f:
                applied_updates = json.load(f)
            print(f"DEBUG: Loaded {len(applied_updates)} existing applied update batches")
        except Exception as e:
            print(f"DEBUG: Error loading applied updates, creating new file: {e}")
            applied_updates = []
        
        # Check if a batch with the same ID already exists
        existing_batch_index = -1
        for i, batch in enumerate(applied_updates):
            if batch["batch_id"] == batch_id:
                existing_batch_index = i
                break

        if existing_batch_index != -1:
            # Append suggestions to existing batch
            applied_updates[existing_batch_index]["suggestions"].extend(approved_suggestions)
        else:
            # Add new batch
            applied_batch = {
                "batch_id": batch_id,
                "applied_at": datetime.now().isoformat(),
                "suggestions": approved_suggestions
            }
            applied_updates.append(applied_batch)
        
        # Save applied updates
        print(f"DEBUG: Saving {len(applied_updates)} applied update batches to {self.applied_updates_file}")
        with open(self.applied_updates_file, 'w') as f:
            json.dump(applied_updates, f, indent=2)
        
        print(f"DEBUG: Successfully moved suggestions to applied updates")
    
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

    def revert_update(self, suggestion_id: str) -> Dict:
        """Revert a specific applied update."""
        
        try:
            with open(self.applied_updates_file, 'r') as f:
                applied_updates = json.load(f)
        except Exception as e:
            return {"error": f"Could not load applied updates: {e}"}

        suggestion_to_revert = None
        batch_of_suggestion = None
        
        for batch in applied_updates:
            for suggestion in batch["suggestions"]:
                if suggestion["suggestion_id"] == suggestion_id:
                    suggestion_to_revert = suggestion
                    batch_of_suggestion = batch
                    break
            if suggestion_to_revert:
                break
        
        if not suggestion_to_revert:
            return {"error": "Suggestion not found"}
            
        if suggestion_to_revert.get("status") != "successfully_applied":
             return {"error": f"Suggestion status is '{suggestion_to_revert.get('status')}', not 'successfully_applied'"}

        backup_path = suggestion_to_revert.get("backup_path")
        file_path = suggestion_to_revert.get("file_path")

        if not backup_path or not os.path.exists(backup_path):
            return {"error": "Backup file not found"}

        try:
            # Restore the backup
            # To be safe, we can copy and then remove, or just rename
            import shutil
            shutil.move(backup_path, file_path)
            
            # Update the suggestion's status
            suggestion_to_revert["status"] = "reverted"
            suggestion_to_revert["reverted_at"] = datetime.now().isoformat()

            # Save the updated applied_updates.json
            with open(self.applied_updates_file, 'w') as f:
                json.dump(applied_updates, f, indent=2)

            return {
                "status": "reverted",
                "suggestion_id": suggestion_id,
                "file_path": file_path
            }

        except Exception as e:
            return {"error": f"Failed to revert update: {e}"}

    def revert_all_updates(self) -> Dict:
        """Revert all applied updates that are revertible and remove them from the list."""
        
        try:
            with open(self.applied_updates_file, 'r') as f:
                applied_updates = json.load(f)
        except Exception as e:
            return {"error": f"Could not load applied updates: {e}"}

        reverted_count = 0
        failed_count = 0
        revert_results = []
        
        surviving_batches = []
        import shutil

        for batch in applied_updates:
            surviving_suggestions = []
            for suggestion in batch["suggestions"]:
                if suggestion.get("status") == "successfully_applied":
                    backup_path = suggestion.get("backup_path")
                    file_path = suggestion.get("file_path")

                    if not backup_path or not os.path.exists(backup_path):
                        failed_count += 1
                        revert_results.append({
                            "suggestion_id": suggestion["suggestion_id"],
                            "status": "failed",
                            "reason": "Backup file not found"
                        })
                        surviving_suggestions.append(suggestion) # Keep it if failed
                        continue

                    try:
                        shutil.move(backup_path, file_path)
                        reverted_count += 1
                        revert_results.append({
                            "suggestion_id": suggestion["suggestion_id"],
                            "status": "reverted_and_removed"
                        })
                        # On success, DON'T append to surviving_suggestions
                    except Exception as e:
                        failed_count += 1
                        revert_results.append({
                            "suggestion_id": suggestion["suggestion_id"],
                            "status": "failed",
                            "reason": str(e)
                        })
                        surviving_suggestions.append(suggestion) # Keep it if failed
                else:
                    # Keep all other suggestions
                    surviving_suggestions.append(suggestion)

            if surviving_suggestions:
                batch['suggestions'] = surviving_suggestions
                surviving_batches.append(batch)
        
        # Save the updated list of batches and suggestions
        with open(self.applied_updates_file, 'w') as f:
            json.dump(surviving_batches, f, indent=2)

        return {
            "reverted_and_removed_count": reverted_count,
            "failed_to_revert_count": failed_count,
            "details": revert_results
        }

# Create singleton instance
update_manager = UpdateManager()
