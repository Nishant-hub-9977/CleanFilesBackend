"""
Offline matching service for resume analysis and candidate matching
Works without any AI API keys - provides robust fallback functionality
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

class OfflineMatchingService:
    """
    Offline matching service that provides full functionality without AI APIs
    """
    
    def __init__(self):
        # Initialize TF-IDF vectorizer for text similarity
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=1000,
            ngram_range=(1, 2),
            lowercase=True
        )
        
        # Common skills database for extraction
        self.skill_database = self._build_skill_database()
        
        # Job title patterns for experience extraction
        self.job_title_patterns = [
            r'software engineer', r'developer', r'programmer', r'architect',
            r'analyst', r'manager', r'director', r'lead', r'senior', r'junior',
            r'specialist', r'consultant', r'coordinator', r'administrator'
        ]
    
    def _build_skill_database(self) -> Dict[str, List[str]]:
        """Build comprehensive skill database for extraction"""
        return {
            "programming_languages": [
                "python", "javascript", "java", "c++", "c#", "php", "ruby", 
                "go", "rust", "swift", "kotlin", "scala", "r", "matlab",
                "typescript", "dart", "perl", "shell", "bash"
            ],
            "web_frameworks": [
                "react", "angular", "vue", "django", "flask", "fastapi",
                "spring", "express", "laravel", "rails", "asp.net", "nextjs"
            ],
            "databases": [
                "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
                "oracle", "sqlite", "cassandra", "dynamodb", "neo4j"
            ],
            "cloud_platforms": [
                "aws", "azure", "gcp", "google cloud", "digital ocean",
                "heroku", "vercel", "netlify", "firebase"
            ],
            "devops_tools": [
                "docker", "kubernetes", "jenkins", "terraform", "ansible",
                "gitlab", "github actions", "circleci", "travis ci"
            ],
            "data_science": [
                "machine learning", "deep learning", "ai", "data science",
                "pandas", "numpy", "tensorflow", "pytorch", "scikit-learn",
                "jupyter", "tableau", "power bi"
            ],
            "mobile_development": [
                "android", "ios", "react native", "flutter", "xamarin",
                "cordova", "ionic"
            ],
            "other_technical": [
                "git", "linux", "api", "rest", "graphql", "microservices",
                "agile", "scrum", "ci/cd", "testing", "unit testing"
            ]
        }
    
    def analyze_resume_offline(self, resume_text: str, job_requirements: List[str] = None) -> Dict[str, Any]:
        """
        Comprehensive offline resume analysis
        """
        try:
            # Extract all information
            skills = self.extract_skills(resume_text)
            experience_years = self.extract_experience_years(resume_text)
            education = self.extract_education(resume_text)
            contact_info = self.extract_contact_info(resume_text)
            certifications = self.extract_certifications(resume_text)
            
            # Calculate match score if job requirements provided
            match_score = 0.0
            match_details = {}
            
            if job_requirements:
                match_score, match_details = self.calculate_detailed_match_score(
                    resume_text, job_requirements, skills
                )
            
            # Generate summary
            summary = self.generate_candidate_summary(
                skills, experience_years, education
            )
            
            # Identify strengths
            strengths = self.identify_strengths(skills, experience_years, education)
            
            # Generate recommendations
            recommendations = self.generate_recommendations(
                skills, experience_years, match_score
            )
            
            return {
                "provider": "offline",
                "analysis": {
                    "skills": skills,
                    "experience_years": experience_years,
                    "education": education,
                    "contact_info": contact_info,
                    "certifications": certifications,
                    "match_score": match_score,
                    "match_details": match_details,
                    "summary": summary,
                    "strengths": strengths,
                    "recommendations": recommendations
                },
                "confidence": 0.8,  # High confidence for rule-based analysis
                "processing_time": 0.1,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Offline resume analysis failed: {e}")
            return self._get_fallback_analysis()
    
    def extract_skills(self, text: str) -> List[str]:
        """Extract skills using comprehensive pattern matching"""
        text_lower = text.lower()
        found_skills = []
        
        # Check each skill category
        for category, skills in self.skill_database.items():
            for skill in skills:
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(skill.lower()) + r'\b'
                if re.search(pattern, text_lower):
                    # Capitalize properly
                    found_skills.append(skill.title())
        
        # Remove duplicates while preserving order
        unique_skills = []
        seen = set()
        for skill in found_skills:
            if skill.lower() not in seen:
                unique_skills.append(skill)
                seen.add(skill.lower())
        
        return unique_skills[:15]  # Return top 15 skills
    
    def extract_experience_years(self, text: str) -> int:
        """Extract years of experience using multiple patterns"""
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'(\d+)\+?\s*years?\s*in\s+',
            r'experience\s*[:\-]\s*(\d+)\+?\s*years?',
            r'(\d+)\+?\s*year\s+experience',
            r'over\s+(\d+)\s+years?',
            r'more\s+than\s+(\d+)\s+years?'
        ]
        
        text_lower = text.lower()
        
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                try:
                    return int(matches[0])
                except ValueError:
                    continue
        
        # Fallback: estimate from job positions and dates
        return self._estimate_experience_from_positions(text)
    
    def _estimate_experience_from_positions(self, text: str) -> int:
        """Estimate experience from job positions and dates"""
        # Look for date patterns (years)
        year_pattern = r'\b(19|20)\d{2}\b'
        years = re.findall(year_pattern, text)
        
        if len(years) >= 2:
            try:
                years_int = [int(y + '00') for y in years]  # Convert to full years
                years_int = [y for y in years_int if 1990 <= y <= 2024]  # Filter valid years
                
                if years_int:
                    min_year = min(years_int)
                    current_year = datetime.now().year
                    estimated_experience = current_year - min_year
                    return min(estimated_experience, 25)  # Cap at 25 years
            except:
                pass
        
        # Fallback: count job positions
        job_count = 0
        for pattern in self.job_title_patterns:
            job_count += len(re.findall(pattern, text.lower()))
        
        return min(job_count * 2, 15)  # Estimate 2 years per position, max 15
    
    def extract_education(self, text: str) -> List[str]:
        """Extract education information with detailed parsing"""
        education = []
        
        # Education degree patterns
        degree_patterns = [
            r'(bachelor[\'s]?\s+(?:of\s+)?(?:science|arts|engineering|business)?[^\n]*)',
            r'(master[\'s]?\s+(?:of\s+)?(?:science|arts|engineering|business)?[^\n]*)',
            r'(phd|doctorate|doctoral[^\n]*)',
            r'(mba[^\n]*)',
            r'(associate[\'s]?\s+degree[^\n]*)',
            r'(diploma[^\n]*)',
            r'(certificate[^\n]*)'
        ]
        
        text_lower = text.lower()
        
        for pattern in degree_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                education.append(match.strip().title())
        
        # Also look for university/college names
        institution_patterns = [
            r'(university\s+of\s+[^\n,]+)',
            r'([^\n,]+\s+university)',
            r'([^\n,]+\s+college)',
            r'([^\n,]+\s+institute)'
        ]
        
        for pattern in institution_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches[:3]:  # Limit to 3 institutions
                education.append(match.strip().title())
        
        return education[:5]  # Return top 5 education entries
    
    def extract_contact_info(self, text: str) -> Dict[str, str]:
        """Extract contact information with improved patterns"""
        contact = {}
        
        # Email pattern (more comprehensive)
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            contact["email"] = emails[0]
        
        # Phone patterns (various formats)
        phone_patterns = [
            r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            r'\+?([0-9]{1,3})[-.\s]?([0-9]{3,4})[-.\s]?([0-9]{3,4})[-.\s]?([0-9]{3,4})'
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Format the first match
                if len(matches[0]) == 3:  # US format
                    contact["phone"] = f"({matches[0][0]}) {matches[0][1]}-{matches[0][2]}"
                break
        
        # LinkedIn profile
        linkedin_pattern = r'linkedin\.com/in/([A-Za-z0-9-]+)'
        linkedin_matches = re.findall(linkedin_pattern, text.lower())
        if linkedin_matches:
            contact["linkedin"] = f"linkedin.com/in/{linkedin_matches[0]}"
        
        # GitHub profile
        github_pattern = r'github\.com/([A-Za-z0-9-]+)'
        github_matches = re.findall(github_pattern, text.lower())
        if github_matches:
            contact["github"] = f"github.com/{github_matches[0]}"
        
        return contact
    
    def extract_certifications(self, text: str) -> List[str]:
        """Extract certifications and licenses"""
        cert_patterns = [
            r'certified\s+[^\n,]+',
            r'certification\s+in\s+[^\n,]+',
            r'license\s+in\s+[^\n,]+',
            r'aws\s+certified\s+[^\n,]+',
            r'microsoft\s+certified\s+[^\n,]+',
            r'google\s+certified\s+[^\n,]+',
            r'cisco\s+certified\s+[^\n,]+',
            r'pmp\s+certified',
            r'scrum\s+master\s+certified'
        ]
        
        certifications = []
        text_lower = text.lower()
        
        for pattern in cert_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                certifications.append(match.strip().title())
        
        return certifications[:5]  # Return top 5 certifications
    
    def calculate_detailed_match_score(self, resume_text: str, job_requirements: List[str], 
                                     extracted_skills: List[str]) -> Tuple[float, Dict[str, Any]]:
        """Calculate detailed match score with breakdown"""
        try:
            # Combine job requirements
            job_text = " ".join(job_requirements).lower()
            resume_lower = resume_text.lower()
            
            # 1. TF-IDF similarity (40% weight)
            corpus = [resume_lower, job_text]
            tfidf_matrix = self.vectorizer.fit_transform(corpus)
            tfidf_similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # 2. Skills match (35% weight)
            job_skills = []
            for category, skills in self.skill_database.items():
                for skill in skills:
                    if skill.lower() in job_text:
                        job_skills.append(skill.lower())
            
            extracted_skills_lower = [s.lower() for s in extracted_skills]
            matching_skills = set(job_skills) & set(extracted_skills_lower)
            skills_score = len(matching_skills) / max(len(job_skills), 1) if job_skills else 0.5
            
            # 3. Keyword match (25% weight)
            job_keywords = set(job_text.split())
            resume_keywords = set(resume_lower.split())
            keyword_overlap = len(job_keywords & resume_keywords) / len(job_keywords)
            
            # Calculate weighted score
            final_score = (
                tfidf_similarity * 0.4 +
                skills_score * 0.35 +
                keyword_overlap * 0.25
            )
            
            # Ensure score is between 0 and 1
            final_score = max(0.0, min(1.0, final_score))
            
            match_details = {
                "tfidf_similarity": float(tfidf_similarity),
                "skills_match_score": float(skills_score),
                "keyword_overlap_score": float(keyword_overlap),
                "matching_skills": list(matching_skills),
                "required_skills": job_skills,
                "candidate_skills": extracted_skills_lower
            }
            
            return final_score, match_details
            
        except Exception as e:
            logger.error(f"Match score calculation failed: {e}")
            return 0.5, {"error": str(e)}
    
    def generate_candidate_summary(self, skills: List[str], experience_years: int, 
                                 education: List[str]) -> str:
        """Generate a comprehensive candidate summary"""
        
        # Determine primary skill area
        primary_area = "Technology"
        if any("data" in skill.lower() or "machine learning" in skill.lower() 
               for skill in skills):
            primary_area = "Data Science"
        elif any("web" in skill.lower() or "react" in skill.lower() or "javascript" in skill.lower() 
                 for skill in skills):
            primary_area = "Web Development"
        elif any("mobile" in skill.lower() or "android" in skill.lower() or "ios" in skill.lower() 
                 for skill in skills):
            primary_area = "Mobile Development"
        
        # Build summary
        summary_parts = []
        
        if experience_years > 0:
            summary_parts.append(f"{experience_years} years of experience")
        
        if skills:
            top_skills = skills[:3]
            summary_parts.append(f"skilled in {', '.join(top_skills)}")
        
        if education:
            summary_parts.append("with relevant educational background")
        
        if summary_parts:
            summary = f"Candidate with {' '.join(summary_parts)} in {primary_area}."
        else:
            summary = f"Candidate in {primary_area} field."
        
        return summary
    
    def identify_strengths(self, skills: List[str], experience_years: int, 
                          education: List[str]) -> List[str]:
        """Identify candidate strengths"""
        strengths = []
        
        # Experience-based strengths
        if experience_years >= 5:
            strengths.append("Experienced professional")
        elif experience_years >= 2:
            strengths.append("Mid-level experience")
        
        # Skill-based strengths
        if len(skills) >= 10:
            strengths.append("Diverse technical skill set")
        elif len(skills) >= 5:
            strengths.append("Good technical foundation")
        
        # Check for leadership skills
        leadership_indicators = ["lead", "manager", "director", "senior", "architect"]
        if any(indicator in " ".join(skills).lower() for indicator in leadership_indicators):
            strengths.append("Leadership experience")
        
        # Check for modern technologies
        modern_tech = ["react", "python", "aws", "docker", "kubernetes", "machine learning"]
        if any(tech in " ".join(skills).lower() for tech in modern_tech):
            strengths.append("Modern technology expertise")
        
        # Education strengths
        if education:
            if any("master" in edu.lower() or "phd" in edu.lower() for edu in education):
                strengths.append("Advanced education")
            elif any("bachelor" in edu.lower() for edu in education):
                strengths.append("Strong educational foundation")
        
        return strengths[:5]  # Return top 5 strengths
    
    def generate_recommendations(self, skills: List[str], experience_years: int, 
                               match_score: float) -> List[str]:
        """Generate hiring recommendations"""
        recommendations = []
        
        if match_score >= 0.8:
            recommendations.append("Strong candidate - recommend for interview")
        elif match_score >= 0.6:
            recommendations.append("Good candidate - consider for interview")
        elif match_score >= 0.4:
            recommendations.append("Potential candidate - review skills alignment")
        else:
            recommendations.append("Limited match - consider for different roles")
        
        # Experience-based recommendations
        if experience_years < 2:
            recommendations.append("Junior level - may need mentoring")
        elif experience_years > 10:
            recommendations.append("Senior level - good for leadership roles")
        
        # Skill-based recommendations
        if len(skills) < 5:
            recommendations.append("Limited technical skills listed - verify in interview")
        
        # General recommendations
        recommendations.extend([
            "Verify technical skills through practical assessment",
            "Check cultural fit and communication skills",
            "Validate experience claims with references"
        ])
        
        return recommendations[:5]  # Return top 5 recommendations
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """Fallback analysis when everything fails"""
        return {
            "provider": "offline",
            "analysis": {
                "skills": [],
                "experience_years": 0,
                "education": [],
                "contact_info": {},
                "certifications": [],
                "match_score": 0.5,
                "match_details": {},
                "summary": "Resume analysis completed - manual review recommended",
                "strengths": ["Manual review required"],
                "recommendations": ["Review resume manually", "Conduct detailed interview"]
            },
            "confidence": 0.3,
            "processing_time": 0.1,
            "timestamp": datetime.utcnow().isoformat(),
            "error": "Analysis failed - using fallback"
        }

# Create global instance
offline_matching_service = OfflineMatchingService()

# Convenience function
def analyze_resume_offline(resume_text: str, job_requirements: List[str] = None) -> Dict[str, Any]:
    """Analyze resume using offline matching service"""
    return offline_matching_service.analyze_resume_offline(resume_text, job_requirements)

