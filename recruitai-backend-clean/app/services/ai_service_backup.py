"""
AI service for OpenAI integration and AI-powered features
"""

import openai
import json
from typing import List, Dict, Any, Optional
from ..core.config import settings
from ..models.job import Job
from ..models.resume import Resume
from ..models.interview import Interview

# Set OpenAI API key
openai.api_key = settings.OPENAI_API_KEY

async def generate_interview_questions(job: Job) -> List[Dict[str, Any]]:
    """Generate AI-powered interview questions for a job"""
    
    if not settings.OPENAI_API_KEY:
        return []
    
    try:
        prompt = f"""
        Generate 10 comprehensive interview questions for the following job position:
        
        Job Title: {job.title}
        Company: {job.company}
        Experience Level: {job.experience_level}
        Job Type: {job.job_type}
        Required Skills: {', '.join(job.required_skills or [])}
        Job Description: {job.description[:500]}...
        
        Please generate questions that assess:
        1. Technical skills relevant to the position
        2. Communication and interpersonal skills
        3. Problem-solving abilities
        4. Experience and background
        5. Cultural fit and motivation
        
        Return the response as a JSON array where each question has:
        - id: sequential number
        - question: the interview question
        - type: "behavioral", "technical", or "situational"
        - skills_assessed: array of skills this question evaluates
        - expected_duration: estimated time in seconds for response
        """
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert HR professional and technical interviewer. Generate comprehensive, relevant interview questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        questions_text = response.choices[0].message.content
        
        # Try to parse as JSON
        try:
            questions = json.loads(questions_text)
            return questions
        except json.JSONDecodeError:
            # If JSON parsing fails, create structured questions from text
            lines = questions_text.strip().split('\n')
            questions = []
            for i, line in enumerate(lines[:10], 1):
                if line.strip():
                    questions.append({
                        "id": i,
                        "question": line.strip(),
                        "type": "general",
                        "skills_assessed": job.required_skills[:3] if job.required_skills else [],
                        "expected_duration": 120
                    })
            return questions
            
    except Exception as e:
        print(f"Error generating interview questions: {e}")
        return []

async def generate_job_summary(job: Job) -> str:
    """Generate AI-powered job summary"""
    
    if not settings.OPENAI_API_KEY:
        return ""
    
    try:
        prompt = f"""
        Create a concise, engaging job summary for the following position:
        
        Job Title: {job.title}
        Company: {job.company}
        Experience Level: {job.experience_level}
        Job Type: {job.job_type}
        Location: {job.location or 'Remote'}
        Required Skills: {', '.join(job.required_skills or [])}
        Job Description: {job.description}
        
        Generate a 2-3 sentence summary that highlights the key aspects of the role and would attract qualified candidates.
        """
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert recruiter. Create compelling job summaries that attract top talent."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating job summary: {e}")
        return ""

async def extract_resume_information(resume_text: str) -> Dict[str, Any]:
    """Extract structured information from resume text using AI"""
    
    if not settings.OPENAI_API_KEY:
        return {}
    
    try:
        prompt = f"""
        Extract structured information from the following resume text:
        
        {resume_text[:3000]}...
        
        Please extract and return a JSON object with the following structure:
        {{
            "candidate_name": "Full name",
            "candidate_email": "email@example.com",
            "candidate_phone": "phone number",
            "skills": ["skill1", "skill2", "skill3"],
            "experience": [
                {{
                    "company": "Company Name",
                    "position": "Job Title",
                    "duration": "Start - End dates",
                    "description": "Brief description"
                }}
            ],
            "education": [
                {{
                    "institution": "School/University",
                    "degree": "Degree type",
                    "field": "Field of study",
                    "year": "Graduation year"
                }}
            ],
            "certifications": ["cert1", "cert2"],
            "summary": "Brief professional summary"
        }}
        
        Extract only information that is clearly present in the resume.
        """
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert resume parser. Extract structured information accurately from resume text."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content
        
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            return {}
            
    except Exception as e:
        print(f"Error extracting resume information: {e}")
        return {}

async def calculate_resume_match_score(resume: Resume, job: Job) -> Dict[str, Any]:
    """Calculate match score between resume and job using AI"""
    
    if not settings.OPENAI_API_KEY:
        return {"match_score": 0.0, "is_qualified": False, "match_details": {}}
    
    try:
        prompt = f"""
        Analyze the match between this resume and job posting:
        
        JOB POSTING:
        Title: {job.title}
        Experience Level: {job.experience_level}
        Required Skills: {', '.join(job.required_skills or [])}
        Preferred Skills: {', '.join(job.preferred_skills or [])}
        Description: {job.description[:500]}...
        
        RESUME:
        Candidate: {resume.candidate_name or 'Unknown'}
        Skills: {', '.join(resume.skills or [])}
        Experience: {json.dumps(resume.experience or [])}
        Education: {json.dumps(resume.education or [])}
        Summary: {resume.ai_summary or ''}
        
        Provide a detailed match analysis as JSON:
        {{
            "match_score": 0.85,
            "is_qualified": true,
            "match_details": {{
                "skills_match": {{
                    "score": 0.8,
                    "matched_skills": ["skill1", "skill2"],
                    "missing_skills": ["skill3"]
                }},
                "experience_match": {{
                    "score": 0.9,
                    "relevant_experience": "Details about relevant experience",
                    "experience_level_fit": true
                }},
                "education_match": {{
                    "score": 0.7,
                    "education_fit": "Assessment of education fit"
                }},
                "overall_assessment": "Detailed assessment of candidate fit",
                "strengths": ["strength1", "strength2"],
                "concerns": ["concern1", "concern2"]
            }}
        }}
        
        Score should be 0.0-1.0. Candidate is qualified if score >= {settings.RESUME_MATCH_THRESHOLD}.
        """
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert recruiter. Analyze resume-job matches accurately and provide detailed assessments."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content
        
        try:
            result = json.loads(result_text)
            # Ensure required fields exist
            if "match_score" not in result:
                result["match_score"] = 0.0
            if "is_qualified" not in result:
                result["is_qualified"] = result["match_score"] >= settings.RESUME_MATCH_THRESHOLD
            if "match_details" not in result:
                result["match_details"] = {}
            
            return result
        except json.JSONDecodeError:
            return {"match_score": 0.0, "is_qualified": False, "match_details": {}}
            
    except Exception as e:
        print(f"Error calculating match score: {e}")
        return {"match_score": 0.0, "is_qualified": False, "match_details": {}}

async def analyze_interview_responses(interview: Interview) -> Dict[str, Any]:
    """Analyze interview responses using AI"""
    
    if not settings.OPENAI_API_KEY or not interview.responses:
        return {}
    
    try:
        # Prepare interview data for analysis
        questions_and_responses = []
        for i, response in enumerate(interview.responses):
            if i < len(interview.questions):
                questions_and_responses.append({
                    "question": interview.questions[i].get("question", ""),
                    "response": response.get("response_text", ""),
                    "duration": response.get("duration", 0)
                })
        
        prompt = f"""
        Analyze this interview performance:
        
        Job Title: {interview.job.title if hasattr(interview, 'job') else 'Unknown'}
        Interview Duration: {interview.duration_minutes} minutes
        
        Questions and Responses:
        {json.dumps(questions_and_responses, indent=2)}
        
        Provide a comprehensive analysis as JSON:
        {{
            "overall_score": 0.85,
            "communication_score": 0.8,
            "technical_score": 0.9,
            "problem_solving_score": 0.8,
            "detailed_analysis": {{
                "communication_assessment": "Assessment of communication skills",
                "technical_assessment": "Assessment of technical knowledge",
                "problem_solving_assessment": "Assessment of problem-solving abilities",
                "response_quality": "Overall quality of responses",
                "areas_of_strength": ["strength1", "strength2"],
                "areas_for_improvement": ["improvement1", "improvement2"]
            }},
            "recommendation": "hire",
            "confidence": 0.85,
            "feedback": "Detailed feedback for the candidate"
        }}
        
        Scores should be 0.0-1.0. Recommendation should be "hire", "consider", or "reject".
        """
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert interviewer and talent assessor. Provide fair, detailed, and constructive interview analysis."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content
        
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            return {}
            
    except Exception as e:
        print(f"Error analyzing interview responses: {e}")
        return {}

