import openai
import json
import re
from typing import List, Dict, Any
from app.schemas_documentation import UpdateSuggestion, DocumentSection, ChangeQuery
from app.config import settings

class AIAnalyzer:
    def __init__(self):
        if settings.OPENAI_API_KEY:
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.client = None
    
    async def analyze_change_request(self, query: ChangeQuery, relevant_sections: List[DocumentSection]) -> List[UpdateSuggestion]:
        """Use OpenAI to analyze change request and generate intelligent suggestions"""
        
        if not relevant_sections:
            return []
        
        if not self.client or not settings.OPENAI_API_KEY:
            print("⚠️ OpenAI API key not configured, using fallback suggestions")
            return self._create_fallback_suggestions(query.query, relevant_sections)
        
        # Limit sections based on config
        limited_sections = relevant_sections[:min(3, settings.DOC_PROCESSING_MAX_SECTIONS)]
        
        try:
            # Prepare context for OpenAI
            context = self._prepare_context(query.query, limited_sections)
            print(f"🤖 Calling OpenAI with {len(limited_sections)} sections...")
            
            response = await self._call_openai_api(context)
            print(f"📝 OpenAI response received: {len(response)} characters")
            print(f"🔍 Response preview: {response[:200]}...")
            
            suggestions = self._parse_ai_response(response, limited_sections)
            print(f"✅ Generated {len(suggestions)} AI suggestions")
            return suggestions
            
        except Exception as e:
            print(f"❌ AI Analysis error: {e}")
            return self._create_fallback_suggestions(query.query, limited_sections)
    
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

    For each section that needs updating, provide SPECIFIC, ACTIONABLE changes:

    1. Quote the EXACT text that needs to be changed
    2. Provide the EXACT replacement text  
    3. Be specific about what documentation needs updating

    Respond in this EXACT JSON format:
    {{
    "suggestions": [
        {{
        "section_title": "exact section title from above",
        "change_type": "update",
        "original_content": "EXACT text from the documentation that needs changing",
        "suggested_content": "EXACT replacement text for that specific content",
        "confidence_score": 0.8,
        "reasoning": "Specific explanation of what needs to change and why"
        }}
    ]
    }}

    Focus on finding actual documentation text that contradicts the change request. If no changes are needed, return empty suggestions array."""
        
        return prompt


    
    async def _call_openai_api(self, prompt: str) -> str:
        """Make API call to OpenAI using config settings"""
        
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
        """Parse OpenAI response into UpdateSuggestion objects"""
        
        try:
            # Clean the response (remove any markdown formatting)
            cleaned_response = ai_response.strip()
            if cleaned_response.startswith("```"):
                # Remove markdown code blocks
                cleaned_response = re.sub(r'^```\w*\n', '', cleaned_response)
                cleaned_response = re.sub(r'\n```$', '', cleaned_response)
            
            # Try to parse JSON response
            parsed = json.loads(cleaned_response)
            suggestions = []
            
            suggestion_list = parsed.get("suggestions", [])
            print(f"🔄 Processing {len(suggestion_list)} AI suggestions...")
            
            for idx, suggestion_data in enumerate(suggestion_list):
                # Find matching section or use index
                section = sections[idx] if idx < len(sections) else sections[0]
                
                suggestion = UpdateSuggestion(
                    section_id=section.id,
                    original_content=suggestion_data.get("original_content", section.content[:300]),
                    suggested_content=suggestion_data.get("suggested_content", ""),
                    change_type=suggestion_data.get("change_type", "update"),
                    confidence_score=float(suggestion_data.get("confidence_score", 0.7)),
                    reasoning=suggestion_data.get("reasoning", "AI-generated suggestion")
                )
                suggestions.append(suggestion)
            
            return suggestions
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print(f"Raw response: {ai_response[:500]}...")
            return self._create_fallback_suggestions("AI response parsing failed", sections)
        except Exception as e:
            print(f"❌ Error processing AI response: {e}")
            return self._create_fallback_suggestions("AI processing error", sections)
    
    def _find_matching_section(self, title: str, sections: List[DocumentSection]) -> DocumentSection:
        """Find section that best matches the title"""
        if not title:
            return None
        title_lower = title.lower()
        for section in sections:
            if title_lower in section.title.lower() or section.title.lower() in title_lower:
                return section
        return None
    
    def _create_fallback_suggestions(self, query: str, sections: List[DocumentSection]) -> List[UpdateSuggestion]:
        """Create simple fallback suggestions when AI fails"""
        suggestions = []
        
        for i, section in enumerate(sections[:3]):
            suggestion = UpdateSuggestion(
                section_id=section.id,
                original_content=section.content[:200] + "...",
                suggested_content=f"[UPDATE NEEDED] Based on query: '{query}'\n\nSuggested change: Review and update this section about {section.title} to reflect the requested changes.",
                change_type="update",
                confidence_score=0.6,
                reasoning=f"Section about '{section.title}' likely needs updates based on query: '{query}'"
            )
            suggestions.append(suggestion)
        
        return suggestions

# Create singleton instance
ai_analyzer = AIAnalyzer()