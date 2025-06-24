import os
import json
import uuid
from typing import List, Dict, Any
from app.schemas_documentation import DocumentSection

class DocumentationParser:
    def __init__(self, docs_path: str):
        self.docs_path = docs_path
        self.sections: List[DocumentSection] = []
    
    def parse_markdown_files(self) -> List[DocumentSection]:
        """Parse JSON files from scraped documentation"""
        sections = []
        
        print(f"🔍 Searching for JSON files in: {self.docs_path}")
        
        if not os.path.exists(self.docs_path):
            print(f"❌ Documentation path does not exist: {self.docs_path}")
            return sections
        
        # Look for JSON files instead of markdown
        json_files = []
        for root, dirs, files in os.walk(self.docs_path):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    json_files.append(file_path)
        
        print(f"📄 Found {len(json_files)} JSON files")
        
        # Parse each JSON file
        for file_path in json_files:
            try:
                sections.extend(self._parse_json_file(file_path))
            except Exception as e:
                print(f"❌ Error parsing {file_path}: {e}")
                continue
        
        print(f"✅ Successfully parsed {len(sections)} sections from {len(json_files)} files")
        
        self.sections = sections
        return sections
    
    def _parse_json_file(self, file_path: str) -> List[DocumentSection]:
        """Parse a single JSON file containing scraped documentation"""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ Error reading JSON {file_path}: {e}")
            return []
        
        sections = []
        
        # Extract the page name from filename
        filename = os.path.basename(file_path).replace('.json', '')
        page_name = filename.replace('openai.github.io_openai-agents-python_', '').replace('_', '/')
        
        # Handle different JSON structures
        if isinstance(data, dict):
            content = self._extract_content_from_json(data)
            if content:
                section = DocumentSection(
                    id=str(uuid.uuid4()),
                    title=page_name,
                    content=content,
                    file_path=file_path.replace('\\', '/'),
                    section_type="json_page"
                )
                sections.append(section)
        elif isinstance(data, list):
            # Handle JSON arrays
            for i, item in enumerate(data):
                content = self._extract_content_from_json(item)
                if content:
                    section = DocumentSection(
                        id=str(uuid.uuid4()),
                        title=f"{page_name} (part {i+1})",
                        content=content,
                        file_path=file_path.replace('\\', '/'),
                        section_type="json_page"
                    )
                    sections.append(section)
        
        return sections
    
    def _extract_content_from_json(self, data: Any) -> str:
        """Extract readable content from JSON data"""
        content_parts = []
        
        if isinstance(data, dict):
            # Look for common content fields
            for key in ['content', 'text', 'body', 'description', 'title', 'name']:
                if key in data and isinstance(data[key], str):
                    content_parts.append(f"{key.title()}: {data[key]}")
            
            # If no specific content fields, extract all string values
            if not content_parts:
                for key, value in data.items():
                    if isinstance(value, str) and len(value) > 10:  # Only meaningful strings
                        content_parts.append(f"{key}: {value}")
                    elif isinstance(value, dict):
                        nested_content = self._extract_content_from_json(value)
                        if nested_content:
                            content_parts.append(f"{key}: {nested_content}")
        
        elif isinstance(data, str):
            content_parts.append(data)
        
        return "\n".join(content_parts[:10])  # Limit to first 10 content pieces
    
    def get_sections(self) -> List[DocumentSection]:
        return self.sections
    
    def find_sections_by_keyword(self, keyword: str) -> List[DocumentSection]:
        return [
            section for section in self.sections 
            if keyword.lower() in section.content.lower() or 
               keyword.lower() in section.title.lower()
        ]