import openai
import re
from typing import List, Dict, Set
from app.schemas_documentation import DocumentSection
from collections import Counter
from app.config import settings
import numpy as np

class EnhancedDocumentSearch:
    def __init__(self):
        self.stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        if settings.OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.openai_client = None
    
    def extract_query_terms(self, query: str, top_n: int = 5) -> List[str]:
        """Extract key terms/phrases from the query using simple NLP heuristics."""
        # Lowercase and tokenize
        tokens = self._tokenize(query.lower())
        # Remove stop words and short words
        filtered = [t for t in tokens if t not in self.stop_words and len(t) > 2]
        # Use frequency to get most important terms
        freq = Counter(filtered)
        most_common = [w for w, _ in freq.most_common(top_n)]
        return most_common
    
    def _get_embedding(self, text: str) -> List[float]:
        if not self.openai_client:
            raise Exception("OpenAI API key not configured for embeddings.")
        response = self.openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        a = np.array(a)
        b = np.array(b)
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            return 0.0
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def semantic_search(self, query: str, sections: List[DocumentSection], max_results: int = 10) -> List[DocumentSection]:
        """Semantic search using OpenAI embeddings. Fallback to keyword search if embedding fails. Filters out Japanese docs."""
        # Filter out Japanese docs (title starts with 'ja/')
        english_sections = [s for s in sections if not s.title.startswith('ja/')]
        try:
            query_embedding = self._get_embedding(query)
            section_embeddings = []
            for section in english_sections:
                # Use both title and content for embedding
                section_text = section.title + "\n" + section.content[:1000]
                emb = self._get_embedding(section_text)
                section_embeddings.append((section, emb))
            # Compute similarity
            scored_sections = []
            for section, emb in section_embeddings:
                sim = self._cosine_similarity(query_embedding, emb)
                scored_sections.append((section, sim))
            scored_sections.sort(key=lambda x: x[1], reverse=True)
            print(f"🔍 [EMBEDDING] Top semantic results for query '{query}':")
            for i, (section, score) in enumerate(scored_sections[:5]):
                print(f"  {i+1}. {section.title} (cosine: {score:.3f})")
            return [section for section, score in scored_sections[:max_results]]
        except Exception as e:
            print(f"❌ Embedding search failed: {e}. Falling back to keyword search.")
            # Fallback: keyword search
            query_terms = self.extract_query_terms(query)
            scored_sections = []
            for section in english_sections:
                score = self._calculate_relevance_score(query_terms, section)
                if score > 0:
                    scored_sections.append((section, score))
            scored_sections.sort(key=lambda x: x[1], reverse=True)
            return [section for section, score in scored_sections[:max_results]]
    
    def find_related_sections(self, target_section: DocumentSection, all_sections: List[DocumentSection], max_results: int = 5) -> List[DocumentSection]:
        """Find sections related to a target section using key term overlap."""
        target_terms = self._extract_key_terms(target_section)
        related = []
        for section in all_sections:
            if section.id == target_section.id:
                continue
            similarity = self._calculate_similarity(target_terms, section)
            if similarity > 0.3:
                related.append((section, similarity))
        related.sort(key=lambda x: x[1], reverse=True)
        return [section for section, similarity in related[:max_results]]
    
    def _tokenize(self, text: str) -> List[str]:
        text = re.sub(r'[^\w\s]', ' ', text)
        return [word.strip() for word in text.split() if word.strip()]
    
    def _calculate_relevance_score(self, query_terms: List[str], section: DocumentSection) -> float:
        section_text = (section.title + " " + section.content).lower()
        section_tokens = self._tokenize(section_text)
        score = 0.0
        title_tokens = self._tokenize(section.title.lower())
        for term in query_terms:
            if term in title_tokens:
                score += 3.0
            elif term in section_tokens:
                score += 1.0
        query_phrase = " ".join(query_terms)
        if query_phrase in section_text:
            score += 5.0
        if len(section_tokens) > 0:
            score = score / (len(section_tokens) / 100)
        return score
    
    def _extract_key_terms(self, section: DocumentSection) -> Set[str]:
        text = (section.title + " " + section.content).lower()
        tokens = self._tokenize(text)
        key_terms = set()
        for token in tokens:
            if len(token) > 3 and token not in self.stop_words:
                key_terms.add(token)
        return key_terms
    
    def _calculate_similarity(self, target_terms: Set[str], section: DocumentSection) -> float:
        section_terms = self._extract_key_terms(section)
        if not target_terms or not section_terms:
            return 0.0
        intersection = len(target_terms & section_terms)
        union = len(target_terms | section_terms)
        return intersection / union if union > 0 else 0.0

# Create singleton instance
enhanced_search = EnhancedDocumentSearch()
