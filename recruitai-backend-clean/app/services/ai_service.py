"""
Multi-Provider AI service with Google AI, DeepSeek, OpenAI, and offline fallbacks
"""

import openai
import httpx
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from ..core.config import settings
from .google_ai_service import google_ai_service

logger = logging.getLogger(__name__)

class MultiProviderAIService:
    """
    Multi-provider AI service with intelligent fallbacks:
    1. Google AI (primary, comprehensive analysis)
    2. DeepSeek (secondary, cost-effective)
    3. OpenAI (tertiary, high quality)
    4. Offline algorithms (always available)
    """
    
    def __init__(self):
        self.google_ai_api_key = settings.GOOGLE_AI_API_KEY
        self.deepseek_api_key = settings.DEEPSEEK_API_KEY
        self.openai_api_key = settings.OPENAI_API_KEY
        self.deepseek_base_url = "https://api.deepseek.com/v1"
        
        # Initialize OpenAI client if key available
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        
        # Initialize TF-IDF vectorizer for offline matching
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=1000,
            ngram_range=(1, 2)
        )
    
    async def analyze_resume(self, resume_text: str, job_requirements: List[str] = None) -> Dict[str, Any]:
        """
        Analyze resume with multi-provider fallback
        """
        try:
            # Try Google AI first (most comprehensive)
            if self.google_ai_api_key:
                result = await google_ai_service.parse_resume_comprehensive(resume_text)
                if result:
                    logger.info("Resume analysis completed with Google AI")
                    return self._format_resume_analysis(result, "google_ai")
            
            # Try DeepSeek second
            if self.deepseek_api_key:
                result = await self._analyze_resume_deepseek(resume_text, job_requirements)
                if result:
                    logger.info("Resume analysis completed with DeepSeek")
                    return result
            
            # Fallback to OpenAI
            if self.openai_api_key:
                result = await self._analyze_resume_openai(resume_text, job_requirements)
                if result:
                    logger.info("Resume analysis completed with OpenAI")
                    return result
            
            # Final fallback to offline analysis
            logger.info("Using offline resume analysis")
            return await self._analyze_resume_offline(resume_text, job_requirements)
            
        except Exception as e:
            logger.error(f"All AI providers failed, using offline analysis: {e}")
            return await self._analyze_resume_offline(resume_text, job_requirements)
    
    async def _analyze_resume_deepseek(self, resume_text: str, job_requirements: List[str] = None) -> Optional[Dict[str, Any]]:
        """Analyze resume using DeepSeek API"""
        try:
            prompt = self._build_resume_analysis_prompt(resume_text, job_requirements)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.deepseek_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.deepseek_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": "You are an expert HR analyst. Analyze resumes and provide structured JSON responses."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1500
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    return self._parse_ai_response(content, "deepseek")
                else:
                    logger.error(f"DeepSeek API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"DeepSeek analysis failed: {e}")
            return None
    
    async def _analyze_resume_openai(self, resume_text: str, job_requirements: List[str] = None) -> Optional[Dict[str, Any]]:
        """Analyze resume using OpenAI API"""
        try:
            prompt = self._build_resume_analysis_prompt(resume_text, job_requirements)
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert HR analyst. Analyze resumes and provide structured JSON responses."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            return self._parse_ai_response(content, "openai")
            
        except Exception as e:
            logger.error(f"OpenAI analysis failed: {e}")
            return None
    
    async def _analyze_resume_offline(self, resume_text: str, job_requirements: List[str] = None) -> Dict[str, Any]:
        """Offline resume analysis using rule-based algorithms"""
        
        # Extract basic information using regex patterns
        skills = self._extract_skills_offline(resume_text)
        experience = self._extract_experience_offline(resume_text)
        education = self._extract_education_offline(resume_text)
        contact_info = self._extract_contact_info_offline(resume_text)
        
        # Calculate match score if job requirements provided
        match_score = 0.0
        if job_requirements:
            match_score = self._calculate_offline_match_score(resume_text, job_requirements)
        
        return {
            "provider": "offline",
            "analysis": {
                "skills": skills,
                "experience_years": experience,
                "education": education,
                "contact_info": contact_info,
                "match_score": match_score,
                "summary": f"Candidate with {experience} years of experience in {', '.join(skills[:3])}",
                "strengths": skills[:5],
                "recommendations": [
                    "Review technical skills alignment",
                    "Verify experience claims",
                    "Check cultural fit"
                ]
            },
            "confidence": 0.7,
            "processing_time": 0.1
        }
    
    def _extract_skills_offline(self, text: str) -> List[str]:
        """Extract skills using keyword matching"""
        common_skills = [
            # Programming languages
            "python", "javascript", "java", "c++", "c#", "php", "ruby", "go", "rust", "swift",
            # Frameworks
            "react", "angular", "vue", "django", "flask", "fastapi", "spring", "express",
            # Databases
            "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
            # Cloud & DevOps
            "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "terraform",
            # Other technical skills
            "machine learning", "ai", "data science", "sql", "git", "linux", "api"
        ]
        
        text_lower = text.lower()
        found_skills = []
        
        for skill in common_skills:
            if skill in text_lower:
                found_skills.append(skill.title())
        
        return found_skills[:10]  # Return top 10 skills
    
    def _extract_experience_offline(self, text: str) -> int:
        """Extract years of experience using regex"""
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'(\d+)\+?\s*years?\s*in',
            r'experience\s*:\s*(\d+)\+?\s*years?',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                return int(matches[0])
        
        # Fallback: count job positions (rough estimate)
        job_indicators = len(re.findall(r'\b(software engineer|developer|analyst|manager|specialist)\b', text.lower()))
        return min(job_indicators * 2, 15)  # Estimate 2 years per position, max 15
    
    def _extract_education_offline(self, text: str) -> List[str]:
        """Extract education information"""
        education_keywords = [
            "bachelor", "master", "phd", "doctorate", "mba", "degree",
            "university", "college", "institute", "school"
        ]
        
        education = []
        text_lower = text.lower()
        
        for keyword in education_keywords:
            if keyword in text_lower:
                # Try to extract the full education line
                lines = text.split('\n')
                for line in lines:
                    if keyword in line.lower():
                        education.append(line.strip())
                        break
        
        return education[:3]  # Return top 3 education entries
    
    def _extract_contact_info_offline(self, text: str) -> Dict[str, str]:
        """Extract contact information"""
        contact = {}
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            contact["email"] = emails[0]
        
        # Phone pattern
        phone_pattern = r'[\+]?[1-9]?[0-9]{7,15}'
        phones = re.findall(phone_pattern, text)
        if phones:
            contact["phone"] = phones[0]
        
        return contact
    
    def _calculate_offline_match_score(self, resume_text: str, job_requirements: List[str]) -> float:
        """Calculate match score using TF-IDF similarity"""
        try:
            # Combine job requirements into single text
            job_text = " ".join(job_requirements)
            
            # Create corpus
            corpus = [resume_text.lower(), job_text.lower()]
            
            # Calculate TF-IDF vectors
            tfidf_matrix = self.vectorizer.fit_transform(corpus)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            
            return float(similarity[0][0])
            
        except Exception as e:
            logger.error(f"Offline match score calculation failed: {e}")
            return 0.5  # Default score
    
    def _build_resume_analysis_prompt(self, resume_text: str, job_requirements: List[str] = None) -> str:
        """Build prompt for AI analysis"""
        prompt = f"""
        Analyze the following resume and provide a structured JSON response:

        RESUME:
        {resume_text}

        """
        
        if job_requirements:
            prompt += f"""
        JOB REQUIREMENTS:
        {', '.join(job_requirements)}
        """
        
        prompt += """
        Please provide analysis in this JSON format:
        {
            "skills": ["skill1", "skill2", ...],
            "experience_years": number,
            "education": ["degree1", "degree2", ...],
            "match_score": 0.0-1.0,
            "summary": "brief summary",
            "strengths": ["strength1", "strength2", ...],
            "recommendations": ["rec1", "rec2", ...]
        }
        """
        
        return prompt
    
    def _parse_ai_response(self, content: str, provider: str) -> Dict[str, Any]:
        """Parse AI response and structure it"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                # Fallback parsing
                analysis = self._fallback_parse_response(content)
            
            return {
                "provider": provider,
                "analysis": analysis,
                "confidence": 0.9,
                "processing_time": 2.0
            }
            
        except Exception as e:
            logger.error(f"Failed to parse {provider} response: {e}")
            # Return basic structure
            return {
                "provider": provider,
                "analysis": {
                    "skills": [],
                    "experience_years": 0,
                    "education": [],
                    "match_score": 0.5,
                    "summary": "Analysis completed",
                    "strengths": [],
                    "recommendations": []
                },
                "confidence": 0.5,
                "processing_time": 2.0
            }
    
    def _fallback_parse_response(self, content: str) -> Dict[str, Any]:
        """Fallback parsing when JSON extraction fails"""
        return {
            "skills": re.findall(r'skill[s]?[:\-\s]*([^\n,]+)', content.lower())[:5],
            "experience_years": 0,
            "education": [],
            "match_score": 0.5,
            "summary": content[:200] + "..." if len(content) > 200 else content,
            "strengths": [],
            "recommendations": ["Review manually", "Verify information"]
        }

    async def match_candidates(self, job_description: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Match candidates to job with multi-provider fallback
        """
        try:
            # Try DeepSeek first
            if self.deepseek_api_key:
                result = await self._match_candidates_deepseek(job_description, candidates)
                if result:
                    logger.info("Candidate matching completed with DeepSeek")
                    return result
            
            # Fallback to OpenAI
            if self.openai_api_key:
                result = await self._match_candidates_openai(job_description, candidates)
                if result:
                    logger.info("Candidate matching completed with OpenAI")
                    return result
            
            # Final fallback to offline matching
            logger.info("Using offline candidate matching")
            return await self._match_candidates_offline(job_description, candidates)
            
        except Exception as e:
            logger.error(f"All AI providers failed for matching, using offline: {e}")
            return await self._match_candidates_offline(job_description, candidates)
    
    async def _match_candidates_offline(self, job_description: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Offline candidate matching using TF-IDF similarity"""
        
        if not candidates:
            return []
        
        try:
            # Prepare texts for comparison
            job_text = job_description.lower()
            candidate_texts = []
            
            for candidate in candidates:
                # Combine candidate information
                candidate_text = ""
                if candidate.get('resume_text'):
                    candidate_text += candidate['resume_text']
                if candidate.get('skills'):
                    candidate_text += " " + " ".join(candidate['skills'])
                candidate_texts.append(candidate_text.lower())
            
            # Calculate similarities
            all_texts = [job_text] + candidate_texts
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # Calculate similarity scores
            job_vector = tfidf_matrix[0:1]
            candidate_vectors = tfidf_matrix[1:]
            
            similarities = cosine_similarity(job_vector, candidate_vectors)[0]
            
            # Add scores to candidates
            for i, candidate in enumerate(candidates):
                candidate['match_score'] = float(similarities[i])
                candidate['match_provider'] = 'offline'
                candidate['match_reasons'] = self._generate_offline_match_reasons(
                    job_description, candidate
                )
            
            # Sort by match score
            candidates.sort(key=lambda x: x.get('match_score', 0), reverse=True)
            
            return candidates
            
        except Exception as e:
            logger.error(f"Offline matching failed: {e}")
            # Return candidates with default scores
            for candidate in candidates:
                candidate['match_score'] = 0.5
                candidate['match_provider'] = 'offline'
                candidate['match_reasons'] = ["Manual review required"]
            
            return candidates
    
    def _generate_offline_match_reasons(self, job_description: str, candidate: Dict[str, Any]) -> List[str]:
        """Generate match reasons for offline matching"""
        reasons = []
        
        job_lower = job_description.lower()
        candidate_skills = candidate.get('skills', [])
        
        # Check skill matches
        matching_skills = []
        for skill in candidate_skills:
            if skill.lower() in job_lower:
                matching_skills.append(skill)
        
        if matching_skills:
            reasons.append(f"Skills match: {', '.join(matching_skills[:3])}")
        
        # Check experience
        if candidate.get('experience_years', 0) > 0:
            reasons.append(f"{candidate['experience_years']} years of experience")
        
        # Check education
        if candidate.get('education'):
            reasons.append("Relevant education background")
        
        if not reasons:
            reasons.append("Basic qualification match")
        
        return reasons

    async def generate_interview_questions(self, job_description: str, candidate_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Generate interview questions with multi-provider fallback
        """
        try:
            # Try DeepSeek first
            if self.deepseek_api_key:
                result = await self._generate_questions_deepseek(job_description, candidate_info)
                if result:
                    logger.info("Interview questions generated with DeepSeek")
                    return result
            
            # Fallback to OpenAI
            if self.openai_api_key:
                result = await self._generate_questions_openai(job_description, candidate_info)
                if result:
                    logger.info("Interview questions generated with OpenAI")
                    return result
            
            # Final fallback to template-based questions
            logger.info("Using template-based interview questions")
            return await self._generate_questions_offline(job_description, candidate_info)
            
        except Exception as e:
            logger.error(f"All AI providers failed for questions, using templates: {e}")
            return await self._generate_questions_offline(job_description, candidate_info)
    
    async def _generate_questions_offline(self, job_description: str, candidate_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Generate template-based interview questions"""
        
        # Extract key information from job description
        job_lower = job_description.lower()
        
        questions = []
        
        # Technical questions based on job description
        if any(tech in job_lower for tech in ['python', 'programming', 'software', 'developer']):
            questions.extend([
                {
                    "question": "Can you walk me through your experience with Python development?",
                    "type": "technical",
                    "category": "experience",
                    "expected_duration": 300
                },
                {
                    "question": "Describe a challenging technical problem you solved recently.",
                    "type": "technical", 
                    "category": "problem_solving",
                    "expected_duration": 300
                }
            ])
        
        # General questions
        questions.extend([
            {
                "question": "Tell me about yourself and your professional background.",
                "type": "general",
                "category": "introduction",
                "expected_duration": 180
            },
            {
                "question": "Why are you interested in this position?",
                "type": "general",
                "category": "motivation",
                "expected_duration": 120
            },
            {
                "question": "What are your greatest strengths?",
                "type": "behavioral",
                "category": "strengths",
                "expected_duration": 120
            },
            {
                "question": "Describe a time when you had to work under pressure.",
                "type": "behavioral",
                "category": "stress_management",
                "expected_duration": 180
            },
            {
                "question": "Where do you see yourself in 5 years?",
                "type": "general",
                "category": "career_goals",
                "expected_duration": 120
            }
        ])
        
        # Add candidate-specific questions if info available
        if candidate_info and candidate_info.get('skills'):
            for skill in candidate_info['skills'][:2]:
                questions.append({
                    "question": f"Can you elaborate on your experience with {skill}?",
                    "type": "technical",
                    "category": "skills",
                    "expected_duration": 180
                })
        
        return questions[:8]  # Return max 8 questions

# Create global instance
ai_service = MultiProviderAIService()

# Convenience functions for backward compatibility
async def analyze_resume_with_ai(resume_text: str, job_requirements: List[str] = None) -> Dict[str, Any]:
    """Analyze resume using multi-provider AI service"""
    return await ai_service.analyze_resume(resume_text, job_requirements)

async def match_candidates_with_ai(job_description: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Match candidates using multi-provider AI service"""
    return await ai_service.match_candidates(job_description, candidates)

async def generate_interview_questions_with_ai(job_description: str, candidate_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Generate interview questions using multi-provider AI service"""
    return await ai_service.generate_interview_questions(job_description, candidate_info)

