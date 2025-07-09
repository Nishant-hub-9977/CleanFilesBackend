"""
Google AI service for enhanced resume and job analysis
Integrates with Google AI Studio for comprehensive parsing and matching
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
import httpx
from ..core.config import settings

logger = logging.getLogger(__name__)

class GoogleAIService:
    """Google AI service for resume and job analysis"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = "gemini-1.5-flash"
        
    async def _make_request(self, prompt: str, max_retries: int = 3) -> Optional[Dict]:
        """Make request to Google AI API with retries"""
        if not self.api_key:
            logger.warning("Google AI API key not configured")
            return None
            
        url = f"{self.base_url}/models/{self.model}:generateContent"
        
        headers = {
            "Content-Type": "application/json",
        }
        
        params = {
            "key": self.api_key
        }
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048,
            }
        }
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        url, 
                        headers=headers, 
                        params=params,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if 'candidates' in result and result['candidates']:
                            content = result['candidates'][0]['content']['parts'][0]['text']
                            try:
                                # Try to parse as JSON
                                return json.loads(content)
                            except json.JSONDecodeError:
                                # Return as text if not JSON
                                return {"text": content}
                        return None
                    else:
                        logger.error(f"Google AI API error: {response.status_code} - {response.text}")
                        
            except Exception as e:
                logger.error(f"Google AI API request failed (attempt {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
        return None

    async def parse_resume_comprehensive(self, resume_text: str) -> Optional[Dict]:
        """Parse resume using Google AI with comprehensive structure"""
        
        prompt = f"""
        Parse the following resume text and extract information in this exact JSON structure:
        
        {{
          "candidate": {{
            "contact_info": {{
              "name": "string",
              "city": "string",
              "state": "string", 
              "phone": "string",
              "email": "string",
              "linkedin": "string"
            }},
            "summary": "string - professional summary",
            "top_skills": ["array of top 5 most important skills"],
            "work_experience": [
              {{
                "title": "string",
                "company": "string",
                "location": "string", 
                "start_date": "string",
                "end_date": "string",
                "responsibilities": ["array of key responsibilities"]
              }}
            ],
            "education": [
              {{
                "degree": "string",
                "institution": "string",
                "location": "string",
                "year": "string"
              }}
            ],
            "skills_section": ["array of all skills mentioned"],
            "experience_years": "number - total years of experience",
            "certifications": ["array of certifications if any"]
          }}
        }}
        
        Resume text:
        {resume_text}
        
        Return only valid JSON. If information is not available, use empty string or empty array.
        """
        
        try:
            result = await self._make_request(prompt)
            if result and 'candidate' in result:
                return result
            return None
        except Exception as e:
            logger.error(f"Error parsing resume with Google AI: {str(e)}")
            return None

    async def parse_job_comprehensive(self, job_description: str) -> Optional[Dict]:
        """Parse job description using Google AI with comprehensive structure"""
        
        prompt = f"""
        Parse the following job description and extract information in this exact JSON structure:
        
        {{
          "job": {{
            "title": "string",
            "company": "string",
            "location": "string",
            "summary": "string - job summary",
            "responsibilities": ["array of key responsibilities"],
            "qualifications": ["array of required qualifications"],
            "required_skills": ["array of required technical skills"],
            "preferred_skills": ["array of preferred skills"],
            "experience_level": "string - entry/mid/senior/executive",
            "experience_years": "number - minimum years required",
            "education_requirements": ["array of education requirements"],
            "employment_type": "string - full-time/part-time/contract",
            "salary_range": {{
              "min": "number or null",
              "max": "number or null",
              "currency": "string"
            }}
          }}
        }}
        
        Job description:
        {job_description}
        
        Return only valid JSON. If information is not available, use empty string, empty array, or null.
        """
        
        try:
            result = await self._make_request(prompt)
            if result and 'job' in result:
                return result
            return None
        except Exception as e:
            logger.error(f"Error parsing job with Google AI: {str(e)}")
            return None

    async def match_candidate_to_job(self, candidate_data: Dict, job_data: Dict) -> Optional[Dict]:
        """Match candidate to job using Google AI analysis"""
        
        prompt = f"""
        Analyze the match between this candidate and job posting. Provide detailed matching analysis.
        
        Candidate:
        {json.dumps(candidate_data, indent=2)}
        
        Job:
        {json.dumps(job_data, indent=2)}
        
        Return analysis in this exact JSON structure:
        
        {{
          "match_analysis": {{
            "overall_score": "number between 0-100",
            "skill_match": {{
              "score": "number between 0-100",
              "matched_skills": ["array of matching skills"],
              "missing_skills": ["array of skills candidate lacks"],
              "additional_skills": ["array of extra skills candidate has"]
            }},
            "experience_match": {{
              "score": "number between 0-100",
              "candidate_years": "number",
              "required_years": "number", 
              "level_match": "string - under/meets/exceeds"
            }},
            "education_match": {{
              "score": "number between 0-100",
              "meets_requirements": "boolean",
              "details": "string explanation"
            }},
            "location_match": {{
              "score": "number between 0-100",
              "compatible": "boolean",
              "details": "string explanation"
            }},
            "strengths": ["array of candidate strengths for this role"],
            "concerns": ["array of potential concerns or gaps"],
            "recommendation": "string - hire/interview/pass with reasoning",
            "confidence": "number between 0-1"
          }}
        }}
        
        Return only valid JSON.
        """
        
        try:
            result = await self._make_request(prompt)
            if result and 'match_analysis' in result:
                return result
            return None
        except Exception as e:
            logger.error(f"Error matching candidate to job with Google AI: {str(e)}")
            return None

    async def generate_interview_questions(self, job_data: Dict, candidate_data: Optional[Dict] = None) -> Optional[Dict]:
        """Generate interview questions using Google AI"""
        
        context = f"Job: {json.dumps(job_data, indent=2)}"
        if candidate_data:
            context += f"\n\nCandidate: {json.dumps(candidate_data, indent=2)}"
        
        prompt = f"""
        Generate interview questions for this job posting{' and candidate' if candidate_data else ''}.
        
        {context}
        
        Return questions in this exact JSON structure:
        
        {{
          "interview_questions": {{
            "general": [
              {{
                "question": "string",
                "type": "general",
                "purpose": "string - what this question assesses",
                "expected_duration": "number - minutes"
              }}
            ],
            "technical": [
              {{
                "question": "string", 
                "type": "technical",
                "skill_area": "string",
                "difficulty": "string - easy/medium/hard",
                "expected_duration": "number - minutes"
              }}
            ],
            "behavioral": [
              {{
                "question": "string",
                "type": "behavioral", 
                "competency": "string",
                "expected_duration": "number - minutes"
              }}
            ],
            "situational": [
              {{
                "question": "string",
                "type": "situational",
                "scenario": "string",
                "expected_duration": "number - minutes"
              }}
            ]
          }},
          "total_questions": "number",
          "estimated_duration": "number - total minutes"
        }}
        
        Generate 8-12 questions total across all categories. Return only valid JSON.
        """
        
        try:
            result = await self._make_request(prompt)
            if result and 'interview_questions' in result:
                return result
            return None
        except Exception as e:
            logger.error(f"Error generating interview questions with Google AI: {str(e)}")
            return None

# Global instance
google_ai_service = GoogleAIService()

# Convenience functions for backward compatibility
async def parse_resume_with_google_ai(resume_text: str) -> Optional[Dict]:
    """Parse resume using Google AI"""
    return await google_ai_service.parse_resume_comprehensive(resume_text)

async def parse_job_with_google_ai(job_description: str) -> Optional[Dict]:
    """Parse job description using Google AI"""
    return await google_ai_service.parse_job_comprehensive(job_description)

async def match_candidate_with_google_ai(candidate_data: Dict, job_data: Dict) -> Optional[Dict]:
    """Match candidate to job using Google AI"""
    return await google_ai_service.match_candidate_to_job(candidate_data, job_data)

async def generate_interview_questions_with_google_ai(job_data: Dict, candidate_data: Optional[Dict] = None) -> Optional[Dict]:
    """Generate interview questions using Google AI"""
    return await google_ai_service.generate_interview_questions(job_data, candidate_data)

