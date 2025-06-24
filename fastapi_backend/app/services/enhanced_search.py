import re
from typing import List, Dict, Set
from app.schemas_documentation import DocumentSection

class EnhancedDocumentSearch:
    def __init__(self):
        self.stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    
    def semantic_search(self, query: str, sections: List[DocumentSection], max_results: int = 10) -> List[DocumentSection]:
        """Enhanced search with ranking and relevance scoring"""
        
        # Filter to English content only (skip Japanese docs)
        english_sections = [s for s in sections if not s.title.startswith('ja/')]
        
        # For agent/tool queries, prioritize sections with actual tool content
        query_lower = query.lower()
        if any(term in query_lower for term in ['agent', 'tool', 'as_tool', 'handoff']):
            # Find sections with actual tool/agent code examples
            priority_sections = []
            for section in english_sections:
                content_lower = section.content.lower()
                # Prioritize sections with real tool patterns
                if any(term in content_lower for term in ['@function_tool', 'function_tool', 'tools=', 'agent.', 'def ', 'class ']):
                    priority_sections.append(section)
            
            if priority_sections:
                print(f"🎯 Found {len(priority_sections)} priority sections with tool patterns")
                english_sections = priority_sections
        
        # Tokenize and clean query
        query_terms = self._tokenize(query_lower)
        query_terms = [term for term in query_terms if term not in self.stop_words]
        
        # Score each section
        scored_sections = []
        for section in english_sections:
            score = self._calculate_relevance_score(query_terms, section)
            if score > 0:
                scored_sections.append((section, score))
        
        # Sort by score (highest first) and return top results
        scored_sections.sort(key=lambda x: x[1], reverse=True)
        
        # Debug: print top results
        print(f"🔍 Top search results for '{' '.join(query_terms)}':")
        for i, (section, score) in enumerate(scored_sections[:5]):
            print(f"  {i+1}. {section.title} (score: {score:.2f})")
            # Show snippet of content to verify it's good
            content_snippet = section.content[:100].replace('\n', ' ')
            print(f"     Content: {content_snippet}...")
        
        return [section for section, score in scored_sections[:max_results]]
    
    def find_related_sections(self, target_section: DocumentSection, all_sections: List[DocumentSection], max_results: int = 5) -> List[DocumentSection]:
        """Find sections related to a target section"""
        
        # Extract key terms from target section
        target_terms = self._extract_key_terms(target_section)
        
        # Find sections with similar terms
        related = []
        for section in all_sections:
            if section.id == target_section.id:
                continue
                
            similarity = self._calculate_similarity(target_terms, section)
            if similarity > 0.3:  # Threshold for similarity
                related.append((section, similarity))
        
        # Sort by similarity and return top results
        related.sort(key=lambda x: x[1], reverse=True)
        return [section for section, similarity in related[:max_results]]
    
    def categorize_sections(self, sections: List[DocumentSection]) -> Dict[str, List[DocumentSection]]:
        """Categorize sections by topic"""
        
        categories = {
            "agents": [],
            "tools": [],
            "handoffs": [],
            "configuration": [],
            "examples": [],
            "api_reference": [],
            "other": []
        }
        
        for section in sections:
            category = self._determine_category(section)
            categories[category].append(section)
        
        return categories
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words"""
        # Remove special characters and split
        text = re.sub(r'[^\w\s]', ' ', text)
        return [word.strip() for word in text.split() if word.strip()]
    
    def _calculate_relevance_score(self, query_terms: List[str], section: DocumentSection) -> float:
        """Calculate relevance score between query and section"""
        
        section_text = (section.title + " " + section.content).lower()
        section_tokens = self._tokenize(section_text)
        
        score = 0.0
        
        # Title matches get higher weight
        title_tokens = self._tokenize(section.title.lower())
        for term in query_terms:
            if term in title_tokens:
                score += 3.0  # High weight for title matches
            elif term in section_tokens:
                score += 1.0  # Normal weight for content matches
        
        # Boost score for exact phrase matches
        query_phrase = " ".join(query_terms)
        if query_phrase in section_text:
            score += 5.0
        
        # Normalize by section length (prefer more focused content)
        if len(section_tokens) > 0:
            score = score / (len(section_tokens) / 100)  # Normalize per 100 words
        
        return score
    
    def _extract_key_terms(self, section: DocumentSection) -> Set[str]:
        """Extract key terms from a section"""
        
        text = (section.title + " " + section.content).lower()
        tokens = self._tokenize(text)
        
        # Filter out stop words and short words
        key_terms = set()
        for token in tokens:
            if len(token) > 3 and token not in self.stop_words:
                key_terms.add(token)
        
        return key_terms
    
    def _calculate_similarity(self, target_terms: Set[str], section: DocumentSection) -> float:
        """Calculate similarity between target terms and section"""
        
        section_terms = self._extract_key_terms(section)
        
        if not target_terms or not section_terms:
            return 0.0
        
        # Calculate Jaccard similarity (intersection / union)
        intersection = len(target_terms & section_terms)
        union = len(target_terms | section_terms)
        
        return intersection / union if union > 0 else 0.0
    
    def _determine_category(self, section: DocumentSection) -> str:
        """Determine the category of a section based on its content"""
        
        title_lower = section.title.lower()
        content_preview = section.content[:500].lower()  # Only check first 500 chars
        
        # Check title first (more specific)
        if any(term in title_lower for term in ['handoff', 'transfer', 'delegate']):
            return "handoffs"
        elif any(term in title_lower for term in ['tool', 'function', 'as_tool']):
            return "tools"
        elif any(term in title_lower for term in ['config', 'setting', 'configuration']):
            return "configuration"
        elif any(term in title_lower for term in ['example', 'tutorial', 'quickstart']):
            return "examples"
        elif any(term in title_lower for term in ['api', 'reference', 'ref/', 'class', 'method']):
            return "api_reference"
        elif 'agent' in title_lower and not any(term in title_lower for term in ['tool', 'handoff', 'config']):
            return "agents"
        
        # Check content if title doesn't match
        elif any(term in content_preview for term in ['handoff', 'transfer control', 'delegate to']):
            return "handoffs"
        elif any(term in content_preview for term in ['as_tool', 'function calling', 'tool use']):
            return "tools"
        elif any(term in content_preview for term in ['configuration', 'settings', 'config']):
            return "configuration"
        elif any(term in content_preview for term in ['example:', 'tutorial', 'getting started']):
            return "examples"
        elif any(term in content_preview for term in ['class ', 'method ', 'function ', 'parameter']):
            return "api_reference"
        elif 'agent' in content_preview:
            return "agents"
        else:
            return "other"

# Create singleton instance
enhanced_search = EnhancedDocumentSearch()
