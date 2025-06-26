import openai
import json
import re
import difflib
from typing import List, Dict, Any
from app.schemas_documentation import UpdateSuggestion, DocumentSection, ChangeQuery
from app.config import settings
from app.services.enhanced_search import EnhancedDocumentSearch

class AIAnalyzer:
    def __init__(self):
        if settings.OPENAI_API_KEY:
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.client = None
        self.enhanced_search = EnhancedDocumentSearch()
    
    async def analyze_change_request(self, query: ChangeQuery, relevant_sections: List[DocumentSection]) -> List[UpdateSuggestion]:
        """Use OpenAI to analyze change request and generate intelligent suggestions"""
        
        if not relevant_sections:
            return []
        
        if not self.client or not settings.OPENAI_API_KEY:
            print("⚠️ OpenAI API key not configured, using fallback suggestions")
            return self._create_fallback_suggestions(query.query, relevant_sections)
        
        # Limit sections based on config
        limited_sections = relevant_sections[:min(20, settings.DOC_PROCESSING_MAX_SECTIONS)]
        
        try:
            # Prepare context for OpenAI
            context = self._prepare_context(query.query, limited_sections)
            print(f"🤖 Calling OpenAI with {len(limited_sections)} sections...")
            
            response = await self._call_openai_api(context)
            print(f"📝 OpenAI response received: {len(response)} characters")
            print(f"🔍 Response preview: {response[:200]}...")
            
            suggestions = self._parse_ai_response(response, limited_sections)
            # Do not filter by high confidence; include all suggestions (even low confidence)
            print(f"✅ Generated {len(suggestions)} AI suggestions (no confidence filtering)")
            return suggestions
            
        except Exception as e:
            print(f"❌ AI Analysis error: {e}")
            return self._create_fallback_suggestions(query.query, limited_sections)
    
    def _normalize_text(self, text: str) -> str:
        # Remove markdown formatting, lowercase, and strip extra spaces
        text = re.sub(r'\*\*', '', text)  # Remove bold
        text = re.sub(r'`', '', text)      # Remove code formatting
        text = re.sub(r'\s+', ' ', text)  # Collapse whitespace
        return text.strip().lower()

    def _find_matching_section(self, title: str, sections: List[DocumentSection]) -> DocumentSection:
        if not title:
            return None
        title_norm = self._normalize_text(title)
        candidates = []
        for section in sections:
            section_title_norm = self._normalize_text(section.title)
            if title_norm == section_title_norm:
                print(f"[MATCH] Exact title match: '{section.title}' (file: {section.file_path})")
                return section
            if title_norm in section_title_norm or section_title_norm in title_norm:
                candidates.append(section)
        if candidates:
            # Prefer candidate whose file path contains the normalized title
            for section in candidates:
                if title_norm in self._normalize_text(section.file_path):
                    print(f"[MATCH] Fuzzy title match with file path: '{section.title}' (file: {section.file_path})")
                    return section
            print(f"[MATCH] Fuzzy title match: '{candidates[0].title}' (file: {candidates[0].file_path})")
            return candidates[0]
        print(f"[NO MATCH] No section matched title '{title}'")
        return None

    def _find_section_by_content(self, content: str, sections: List[DocumentSection], ai_section_title: str = None) -> DocumentSection:
        if not content:
            return None
        norm_content = self._normalize_text(content)
        matches = []
        for section in sections:
            norm_section = self._normalize_text(section.content)
            if norm_content and norm_content in norm_section:
                matches.append(section)
        if not matches:
            print(f"[NO MATCH] No section matched content '{content[:40]}...'")
            return None
        if len(matches) == 1:
            print(f"[MATCH] Single content match: '{matches[0].title}' (file: {matches[0].file_path})")
            return matches[0]
        # Prefer match whose file path or title contains the AI section title
        if ai_section_title:
            ai_title_norm = self._normalize_text(ai_section_title)
            for section in matches:
                if ai_title_norm in self._normalize_text(section.file_path) or ai_title_norm in self._normalize_text(section.title):
                    print(f"[MATCH] Content match with AI section title: '{section.title}' (file: {section.file_path})")
                    return section
        print(f"[MATCH] Multiple content matches, returning first: '{matches[0].title}' (file: {matches[0].file_path})")
        return matches[0]

    def _prepare_context(self, query: str, sections: List[DocumentSection]) -> str:
        """Prepare context for OpenAI API call"""
        
        sections_text = ""
        for i, section in enumerate(sections):
            sections_text += f"""
    SECTION {i+1}: {section.title}
    FILE: {section.file_path}
    CURRENT CONTENT:
    {section.content[:800]}
    {'...' if len(section.content) > 800 else ''}

    ---
    """
        
        prompt = f"""You are a technical documentation expert. A user wants to make this change:

    CHANGE REQUEST: {query}

    Here are the relevant documentation sections that may need updating:

    {sections_text}

    For each section that needs updating, provide SPECIFIC, ACTIONABLE changes. Respond in this EXACT JSON format:
    {{
    "suggestions": [
        {{
        "section_title": "exact section title from above",
        "change_type": "update",
        "original_content": "EXACT text from the documentation that needs changing (must be copy-pasted, unmodified)",
        "suggested_content": "EXACT replacement text for that specific content",
        "confidence_score": 0.8,
        "reasoning": "Specific explanation of what needs to change and why"
        }}
    ]
    }}
    
    IMPORTANT: For 'original_content', you MUST copy-paste the exact, unmodified text from the documentation above. Do NOT rephrase, summarize, or change any characters, punctuation, or formatting. If you do, your suggestion will be ignored.

    For each section, if you see any text that might be outdated, ambiguous, or potentially affected by the change request, include it as a suggestion—even if you are not 100% certain. If you are unsure, it is better to include a suggestion with a lower confidence score and explain your reasoning.

    Consider not only direct contradictions, but also related statements, edge cases, or examples that might be indirectly affected by the change request.

    For each suggestion, set the confidence score to reflect your certainty (e.g., 0.5 for possible but uncertain, 0.9 for very certain).

    Example:
    If the documentation says:
    - Agents as tools: this allows you to use an agent as a tool, allowing Agents to call other agents without handing off to them.
    
    Then your 'original_content' must be EXACTLY:
    "- Agents as tools: this allows you to use an agent as a tool, allowing Agents to call other agents without handing off to them."
    
    NOT:
    "Agents as tools: this feature allows agents to call other agents." (This will be ignored)
    
    Focus on finding actual documentation text that contradicts the change request. If no changes are needed, return empty suggestions array."""
        
        return prompt

    async def _call_openai_api(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a technical documentation expert. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=settings.AI_MAX_TOKENS,
            temperature=settings.AI_TEMPERATURE
        )
        return response.choices[0].message.content.strip()

    def _parse_ai_response(self, ai_response: str, sections: List[DocumentSection]) -> List[UpdateSuggestion]:
        try:
            cleaned_response = ai_response.strip()
            if cleaned_response.startswith("```"):
                cleaned_response = re.sub(r'^```\w*\n', '', cleaned_response)
                cleaned_response = re.sub(r'\n```$', '', cleaned_response)
            parsed = json.loads(cleaned_response)
            suggestions = []
            suggestion_list = parsed.get("suggestions", [])
            print(f"🔄 Processing {len(suggestion_list)} AI suggestions...")
            for idx, suggestion_data in enumerate(suggestion_list):
                section_title = suggestion_data.get("section_title", "")
                section = self._find_matching_section(section_title, sections)
                if not section:
                    original_content = suggestion_data.get("original_content", "")
                    section = self._find_section_by_content(original_content, sections, ai_section_title=section_title)
                if not section:
                    section = sections[0] if sections else None
                    print(f"⚠️ No matching section found for '{section_title}', using first section")
                if section:
                    orig_content = suggestion_data.get("original_content", section.content[:300])
                    # 1. Check for exact match
                    if orig_content in section.content:
                        print(f"✅ [EXACT] 'original_content' is an exact match in section: {section.title} (file: {section.file_path})")
                        suggestions.append(UpdateSuggestion(
                            section_id=section.id,
                            section_title=section.title,
                            file_path=section.file_path,
                            original_content=orig_content,
                            suggested_content=suggestion_data.get("suggested_content", ""),
                            change_type=suggestion_data.get("change_type", "update"),
                            confidence_score=float(suggestion_data.get("confidence_score", 0.7)),
                            reasoning=suggestion_data.get("reasoning", "AI-generated suggestion")
                        ))
                    else:
                        # 2. Check for normalized match
                        norm_orig = self._normalize_text(orig_content)
                        norm_section = self._normalize_text(section.content)
                        if norm_orig and norm_orig in norm_section:
                            print(f"⚠️ [LENIENT] 'original_content' is not exact but normalized match in section: {section.title} (file: {section.file_path})")
                            suggestions.append(UpdateSuggestion(
                                section_id=section.id,
                                section_title=section.title,
                                file_path=section.file_path,
                                original_content=orig_content,
                                suggested_content=suggestion_data.get("suggested_content", ""),
                                change_type=suggestion_data.get("change_type", "update"),
                                confidence_score=float(suggestion_data.get("confidence_score", 0.7)),
                                reasoning=suggestion_data.get("reasoning", "AI-generated suggestion (lenient match)")
                            ))
                        else:
                            # 3. Fuzzy match as a last resort
                            seq = difflib.SequenceMatcher(None, orig_content, section.content, autojunk=False)
                            match = seq.find_longest_match(0, len(orig_content), 0, len(section.content))
                            if match.size > 0 and (match.size / len(orig_content)) > 0.8:
                                matched_content_from_doc = section.content[match.b:match.b + match.size]
                                print(f"⚠️ [FUZZY] Found fuzzy match. Correcting 'original_content' to be exact.")
                                suggestions.append(UpdateSuggestion(
                                    section_id=section.id,
                                    section_title=section.title,
                                    file_path=section.file_path,
                                    original_content=matched_content_from_doc, # Use the corrected content
                                    suggested_content=suggestion_data.get("suggested_content", ""),
                                    change_type=suggestion_data.get("change_type", "update"),
                                    confidence_score=0.6, # Lower confidence for fuzzy match
                                    reasoning=suggestion_data.get("reasoning", "") + " (Note: Original content was fuzzy-matched and corrected for accuracy.)"
                                ))
                            else:
                                print(f"❌ [SKIPPING] 'original_content' is NOT a match (exact, normalized, or fuzzy).")
                                continue
                else:
                    print(f"❌ No section available for suggestion {idx}")
            return suggestions
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print(f"Raw response: {ai_response[:500]}...")
            return self._create_fallback_suggestions("AI response parsing failed", sections)
        except Exception as e:
            print(f"❌ Error processing AI response: {e}")
            return self._create_fallback_suggestions("AI processing error", sections)

    def _create_fallback_suggestions(self, query: str, sections: List[DocumentSection]) -> List[UpdateSuggestion]:
        suggestions = []
        # Use dynamic query terms for more context-aware fallback
        query_terms = self.enhanced_search.extract_query_terms(query)
        for i, section in enumerate(sections[:3]):
            # Try to find a sentence in the section that contains any query term
            found = None
            for sentence in section.content.split('.'):
                if any(term in sentence.lower() for term in query_terms):
                    found = sentence.strip()
                    break
            if not found:
                found = section.content[:200] + "..."
            suggestion = UpdateSuggestion(
                section_id=section.id,
                section_title=section.title,
                file_path=section.file_path,
                original_content=found,
                suggested_content=f"[UPDATE NEEDED] Based on query: '{query}'\n\nSuggested change: Review and update this section about {section.title} to reflect the requested changes.",
                change_type="update",
                confidence_score=0.6,
                reasoning=f"Section about '{section.title}' likely needs updates based on query: '{query}'"
            )
            suggestions.append(suggestion)
        return suggestions

# Create singleton instance
ai_analyzer = AIAnalyzer()