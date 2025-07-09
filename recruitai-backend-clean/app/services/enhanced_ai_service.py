"""
Enhanced Multi-Provider AI service with Google AI integration
Maintains backward compatibility while adding Google AI Studio features
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from .ai_service import MultiProviderAIService
from .google_ai_service import google_ai_service
from ..core.config import settings

logger = logging.getLogger(__name__)

class EnhancedAIService(MultiProviderAIService):
    """
    Enhanced AI service that extends the existing MultiProviderAIService
    with Google AI Studio integration while maintaining all existing features
    """
    
    def __init__(self):
        super().__init__()
        self.google_ai_available = bool(settings.GOOGLE_AI_API_KEY)
    
    def _format_resume_analysis(self, google_ai_result: Dict, provider: str) -> Dict[str, Any]:
        """Format Google AI result to match existing API structure"""
        if not google_ai_result or 'candidate' not in google_ai_result:
            return {}
        
        candidate = google_ai_result['candidate']
        
        # Convert to existing format while preserving new data
        formatted_result = {
            "provider": provider,
            "timestamp": datetime.now().isoformat(),
            "success": True,
            
            # Existing format fields
            "name": candidate.get('contact_info', {}).get('name', ''),
            "email": candidate.get('contact_info', {}).get('email', ''),
            "phone": candidate.get('contact_info', {}).get('phone', ''),
            "skills": candidate.get('skills_section', []),
            "experience_years": candidate.get('experience_years', 0),
            "summary": candidate.get('summary', ''),
            
            # Enhanced fields from Google AI
            "enhanced_data": {
                "contact_info": candidate.get('contact_info', {}),
                "top_skills": candidate.get('top_skills', []),
                "work_experience": candidate.get('work_experience', []),
                "education": candidate.get('education', []),
                "certifications": candidate.get('certifications', []),
                "linkedin": candidate.get('contact_info', {}).get('linkedin', ''),
                "location": {
                    "city": candidate.get('contact_info', {}).get('city', ''),
                    "state": candidate.get('contact_info', {}).get('state', '')
                }
            },
            
            # Compatibility fields
            "extracted_skills": candidate.get('skills_section', []),
            "work_history": candidate.get('work_experience', []),
            "education_history": candidate.get('education', [])
        }
        
        return formatted_result
    
    def _format_job_analysis(self, google_ai_result: Dict, provider: str) -> Dict[str, Any]:
        """Format Google AI job result to match existing API structure"""
        if not google_ai_result or 'job' not in google_ai_result:
            return {}
        
        job = google_ai_result['job']
        
        formatted_result = {
            "provider": provider,
            "timestamp": datetime.now().isoformat(),
            "success": True,
            
            # Existing format fields
            "title": job.get('title', ''),
            "company": job.get('company', ''),
            "location": job.get('location', ''),
            "description": job.get('summary', ''),
            "requirements": job.get('qualifications', []),
            "skills_required": job.get('required_skills', []),
            
            # Enhanced fields from Google AI
            "enhanced_data": {
                "responsibilities": job.get('responsibilities', []),
                "qualifications": job.get('qualifications', []),
                "required_skills": job.get('required_skills', []),
                "preferred_skills": job.get('preferred_skills', []),
                "experience_level": job.get('experience_level', ''),
                "experience_years": job.get('experience_years', 0),
                "education_requirements": job.get('education_requirements', []),
                "employment_type": job.get('employment_type', ''),
                "salary_range": job.get('salary_range', {})
            },
            
            # Compatibility fields
            "extracted_requirements": job.get('qualifications', []),
            "key_skills": job.get('required_skills', [])
        }
        
        return formatted_result
    
    async def analyze_resume_enhanced(self, resume_text: str, job_requirements: List[str] = None) -> Dict[str, Any]:
        """
        Enhanced resume analysis with Google AI integration
        Falls back to existing multi-provider system
        """
        try:
            # Try Google AI first for comprehensive analysis
            if self.google_ai_available:
                result = await google_ai_service.parse_resume_comprehensive(resume_text)
                if result:
                    logger.info("Enhanced resume analysis completed with Google AI")
                    return self._format_resume_analysis(result, "google_ai")
            
            # Fallback to existing multi-provider analysis
            logger.info("Falling back to existing multi-provider analysis")
            return await super().analyze_resume(resume_text, job_requirements)
            
        except Exception as e:
            logger.error(f"Enhanced resume analysis failed: {e}")
            return await super().analyze_resume(resume_text, job_requirements)
    
    async def analyze_job_enhanced(self, job_description: str) -> Dict[str, Any]:
        """
        Enhanced job analysis with Google AI integration
        """
        try:
            # Try Google AI first for comprehensive analysis
            if self.google_ai_available:
                result = await google_ai_service.parse_job_comprehensive(job_description)
                if result:
                    logger.info("Enhanced job analysis completed with Google AI")
                    return self._format_job_analysis(result, "google_ai")
            
            # Fallback to basic job analysis
            logger.info("Using basic job analysis")
            return {
                "provider": "offline",
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "title": "Job Position",
                "company": "Company",
                "location": "Location",
                "description": job_description[:500],
                "requirements": [],
                "skills_required": [],
                "enhanced_data": {}
            }
            
        except Exception as e:
            logger.error(f"Enhanced job analysis failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def match_candidate_enhanced(self, candidate_data: Dict, job_data: Dict) -> Dict[str, Any]:
        """
        Enhanced candidate matching with Google AI integration
        """
        try:
            # Try Google AI for comprehensive matching
            if self.google_ai_available:
                # Prepare data for Google AI
                google_candidate = candidate_data.get('enhanced_data', candidate_data)
                google_job = job_data.get('enhanced_data', job_data)
                
                result = await google_ai_service.match_candidate_to_job(google_candidate, google_job)
                if result and 'match_analysis' in result:
                    logger.info("Enhanced matching completed with Google AI")
                    return self._format_match_analysis(result['match_analysis'], "google_ai")
            
            # Fallback to existing matching logic
            logger.info("Using existing matching algorithm")
            return await self._match_candidate_offline(candidate_data, job_data)
            
        except Exception as e:
            logger.error(f"Enhanced matching failed: {e}")
            return await self._match_candidate_offline(candidate_data, job_data)
    
    def _format_match_analysis(self, match_analysis: Dict, provider: str) -> Dict[str, Any]:
        """Format Google AI match analysis to existing structure"""
        return {
            "provider": provider,
            "timestamp": datetime.now().isoformat(),
            "success": True,
            
            # Existing format
            "overall_score": match_analysis.get('overall_score', 0),
            "match_percentage": match_analysis.get('overall_score', 0),
            "matched_skills": match_analysis.get('skill_match', {}).get('matched_skills', []),
            "missing_skills": match_analysis.get('skill_match', {}).get('missing_skills', []),
            "recommendation": match_analysis.get('recommendation', 'review'),
            
            # Enhanced analysis
            "enhanced_analysis": {
                "skill_match": match_analysis.get('skill_match', {}),
                "experience_match": match_analysis.get('experience_match', {}),
                "education_match": match_analysis.get('education_match', {}),
                "location_match": match_analysis.get('location_match', {}),
                "strengths": match_analysis.get('strengths', []),
                "concerns": match_analysis.get('concerns', []),
                "confidence": match_analysis.get('confidence', 0.5)
            }
        }
    
    async def _match_candidate_offline(self, candidate_data: Dict, job_data: Dict) -> Dict[str, Any]:
        """Offline matching fallback"""
        candidate_skills = candidate_data.get('skills', [])
        job_requirements = job_data.get('requirements', [])
        
        if not candidate_skills or not job_requirements:
            return {
                "provider": "offline",
                "success": True,
                "overall_score": 50,
                "match_percentage": 50,
                "matched_skills": [],
                "missing_skills": [],
                "recommendation": "review"
            }
        
        # Simple skill matching
        matched_skills = []
        for skill in candidate_skills:
            for req in job_requirements:
                if skill.lower() in req.lower() or req.lower() in skill.lower():
                    matched_skills.append(skill)
                    break
        
        match_score = (len(matched_skills) / len(job_requirements)) * 100 if job_requirements else 0
        
        return {
            "provider": "offline",
            "success": True,
            "overall_score": min(match_score, 100),
            "match_percentage": min(match_score, 100),
            "matched_skills": matched_skills,
            "missing_skills": [req for req in job_requirements if not any(skill.lower() in req.lower() for skill in candidate_skills)],
            "recommendation": "hire" if match_score > 80 else "interview" if match_score > 60 else "review"
        }
    
    async def generate_interview_questions_enhanced(self, job_data: Dict, candidate_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Enhanced interview question generation with Google AI
        """
        try:
            # Try Google AI first
            if self.google_ai_available:
                google_job = job_data.get('enhanced_data', job_data)
                google_candidate = candidate_data.get('enhanced_data') if candidate_data else None
                
                result = await google_ai_service.generate_interview_questions(google_job, google_candidate)
                if result and 'interview_questions' in result:
                    logger.info("Enhanced interview questions generated with Google AI")
                    return self._format_interview_questions(result, "google_ai")
            
            # Fallback to basic question generation
            logger.info("Using basic interview question generation")
            return self._generate_basic_interview_questions(job_data)
            
        except Exception as e:
            logger.error(f"Enhanced interview generation failed: {e}")
            return self._generate_basic_interview_questions(job_data)
    
    def _format_interview_questions(self, google_result: Dict, provider: str) -> Dict[str, Any]:
        """Format Google AI interview questions to existing structure"""
        questions = google_result.get('interview_questions', {})
        
        # Flatten all questions into a single list for backward compatibility
        all_questions = []
        
        for category in ['general', 'technical', 'behavioral', 'situational']:
            category_questions = questions.get(category, [])
            for q in category_questions:
                all_questions.append({
                    "question": q.get('question', ''),
                    "category": category,
                    "type": q.get('type', category),
                    "difficulty": q.get('difficulty', 'medium'),
                    "duration": q.get('expected_duration', 5)
                })
        
        return {
            "provider": provider,
            "success": True,
            "questions": all_questions,
            "total_questions": len(all_questions),
            "estimated_duration": google_result.get('estimated_duration', len(all_questions) * 5),
            "enhanced_structure": questions
        }
    
    def _generate_basic_interview_questions(self, job_data: Dict) -> Dict[str, Any]:
        """Basic interview question generation fallback"""
        basic_questions = [
            {"question": "Tell me about yourself and your experience.", "category": "general", "duration": 5},
            {"question": "Why are you interested in this position?", "category": "general", "duration": 3},
            {"question": "What are your greatest strengths?", "category": "behavioral", "duration": 4},
            {"question": "Describe a challenging project you worked on.", "category": "behavioral", "duration": 6},
            {"question": "Where do you see yourself in 5 years?", "category": "general", "duration": 3}
        ]
        
        return {
            "provider": "offline",
            "success": True,
            "questions": basic_questions,
            "total_questions": len(basic_questions),
            "estimated_duration": sum(q["duration"] for q in basic_questions)
        }

# Global instance
enhanced_ai_service = EnhancedAIService()

# Backward compatibility functions
async def analyze_resume_with_ai(resume_text: str, job_requirements: List[str] = None) -> Dict[str, Any]:
    """Backward compatible resume analysis"""
    return await enhanced_ai_service.analyze_resume_enhanced(resume_text, job_requirements)

async def match_candidates_with_ai(candidate_data: Dict, job_data: Dict) -> Dict[str, Any]:
    """Backward compatible candidate matching"""
    return await enhanced_ai_service.match_candidate_enhanced(candidate_data, job_data)

async def generate_interview_questions_with_ai(job_description: str) -> Dict[str, Any]:
    """Backward compatible interview question generation"""
    job_data = {"description": job_description, "requirements": []}
    return await enhanced_ai_service.generate_interview_questions_enhanced(job_data)

