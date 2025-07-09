# 🧪 RecruitAI Backend Testing Guide

## Multi-Provider AI System Testing

This guide helps you test all features of your RecruitAI backend with the new multi-provider AI system.

---

## 🚀 **Quick Start Testing**

### **1. Health Check**
```bash
curl https://your-app.onrender.com/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "message": "RecruitAI API is running",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### **2. API Documentation**
Visit: `https://your-app.onrender.com/docs`

You should see:
- ✅ Complete API documentation
- ✅ All endpoints listed
- ✅ Interactive testing interface

---

## 🔐 **Authentication Testing**

### **1. User Registration**
```bash
curl -X POST "https://your-app.onrender.com/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpassword123",
    "full_name": "Test User",
    "role": "recruiter"
  }'
```

**Expected Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "full_name": "Test User",
    "role": "recruiter",
    "credits": 10
  }
}
```

### **2. User Login**
```bash
curl -X POST "https://your-app.onrender.com/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword123"
```

**Save the access_token for subsequent requests!**

---

## 🤖 **AI Provider Testing**

### **1. Check AI Status**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-app.onrender.com/api/status"
```

**Expected Response:**
```json
{
  "api_status": "operational",
  "ai_providers": {
    "deepseek": "available",
    "openai": "unavailable",
    "offline": "available"
  },
  "features": {
    "ai_matching": true,
    "interview_analysis": true,
    "resume_processing": true
  },
  "provider_priority": ["deepseek", "openai", "offline"]
}
```

### **2. Test Resume Analysis (Multi-Provider)**
```bash
curl -X POST "https://your-app.onrender.com/api/resumes/analyze" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "John Doe\nSoftware Engineer\n5 years experience with Python, FastAPI, PostgreSQL\nBachelor of Computer Science\nEmail: john@example.com",
    "job_requirements": ["Python", "FastAPI", "PostgreSQL", "5+ years experience"]
  }'
```

**Expected Response (DeepSeek):**
```json
{
  "provider": "deepseek",
  "analysis": {
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "experience_years": 5,
    "education": ["Bachelor of Computer Science"],
    "contact_info": {"email": "john@example.com"},
    "match_score": 0.85,
    "summary": "Experienced software engineer with 5 years in Python development",
    "strengths": ["Strong technical skills", "Relevant experience"],
    "recommendations": ["Strong candidate - recommend for interview"]
  },
  "confidence": 0.9,
  "processing_time": 2.1
}
```

**Expected Response (Offline Fallback):**
```json
{
  "provider": "offline",
  "analysis": {
    "skills": ["Python", "Fastapi", "Postgresql"],
    "experience_years": 5,
    "education": ["Bachelor of Computer Science"],
    "contact_info": {"email": "john@example.com"},
    "match_score": 0.78,
    "summary": "Candidate with 5 years of experience in Python, Fastapi, Postgresql",
    "strengths": ["Python", "Fastapi", "Postgresql", "Strong technical foundation"],
    "recommendations": ["Review technical skills alignment", "Verify experience claims"]
  },
  "confidence": 0.7,
  "processing_time": 0.1
}
```

---

## 💼 **Job Management Testing**

### **1. Create Job**
```bash
curl -X POST "https://your-app.onrender.com/api/jobs/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior Python Developer",
    "company": "Tech Corp",
    "description": "We are looking for a senior Python developer with FastAPI experience",
    "requirements": ["Python", "FastAPI", "PostgreSQL", "5+ years experience"],
    "location": "Remote",
    "job_type": "full-time",
    "experience_level": "senior",
    "salary_min": 80000,
    "salary_max": 120000
  }'
```

### **2. List Jobs**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-app.onrender.com/api/jobs/?limit=10&skip=0"
```

### **3. Get Job Details**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-app.onrender.com/api/jobs/1"
```

---

## 📄 **Resume Upload Testing**

### **1. Upload Resume (PDF)**
```bash
curl -X POST "https://your-app.onrender.com/api/resumes/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@sample_resume.pdf" \
  -F "job_id=1"
```

**Expected Response:**
```json
{
  "id": 1,
  "filename": "sample_resume.pdf",
  "file_size": 245760,
  "file_type": "application/pdf",
  "is_processed": true,
  "extracted_text": "John Doe\nSoftware Engineer...",
  "ai_analysis": {
    "provider": "deepseek",
    "skills": ["Python", "FastAPI"],
    "match_score": 0.85
  },
  "upload_date": "2024-01-15T10:30:00Z"
}
```

### **2. List Resumes**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-app.onrender.com/api/resumes/?limit=10"
```

---

## 👥 **Candidate Management Testing**

### **1. Create Candidate**
```bash
curl -X POST "https://your-app.onrender.com/api/candidates/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": 1,
    "resume_id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "(555) 123-4567",
    "status": "applied"
  }'
```

### **2. Match Candidates to Job**
```bash
curl -X POST "https://your-app.onrender.com/api/candidates/match" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": 1,
    "candidate_ids": [1, 2, 3]
  }'
```

**Expected Response:**
```json
{
  "job_id": 1,
  "matches": [
    {
      "candidate_id": 1,
      "match_score": 0.85,
      "match_provider": "deepseek",
      "match_reasons": ["Skills match: Python, FastAPI", "5 years of experience"],
      "ranking": 1
    },
    {
      "candidate_id": 2,
      "match_score": 0.72,
      "match_provider": "offline",
      "match_reasons": ["Skills match: Python", "3 years of experience"],
      "ranking": 2
    }
  ],
  "provider_used": "deepseek",
  "processing_time": 2.3
}
```

---

## 🎤 **Interview System Testing**

### **1. Generate Interview Questions**
```bash
curl -X POST "https://your-app.onrender.com/api/interviews/generate-questions" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Senior Python Developer with FastAPI experience",
    "candidate_info": {
      "skills": ["Python", "FastAPI", "PostgreSQL"],
      "experience_years": 5
    }
  }'
```

**Expected Response (DeepSeek):**
```json
{
  "questions": [
    {
      "question": "Can you walk me through your experience with Python development?",
      "type": "technical",
      "category": "experience",
      "expected_duration": 300
    },
    {
      "question": "How would you design a scalable FastAPI application?",
      "type": "technical",
      "category": "architecture",
      "expected_duration": 240
    }
  ],
  "provider": "deepseek",
  "total_questions": 8
}
```

**Expected Response (Offline):**
```json
{
  "questions": [
    {
      "question": "Tell me about yourself and your professional background.",
      "type": "general",
      "category": "introduction",
      "expected_duration": 180
    },
    {
      "question": "Can you elaborate on your experience with Python?",
      "type": "technical",
      "category": "skills",
      "expected_duration": 180
    }
  ],
  "provider": "offline",
  "total_questions": 6
}
```

### **2. Create Interview**
```bash
curl -X POST "https://your-app.onrender.com/api/interviews/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": 1,
    "candidate_id": 1,
    "interview_type": "video",
    "scheduled_at": "2024-01-20T14:00:00Z"
  }'
```

---

## 💳 **Credit System Testing**

### **1. Check Credits**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-app.onrender.com/api/credits/balance"
```

**Expected Response:**
```json
{
  "user_id": 1,
  "current_balance": 7,
  "total_earned": 10,
  "total_spent": 3,
  "last_transaction": "2024-01-15T10:30:00Z"
}
```

### **2. Credit Transaction History**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-app.onrender.com/api/credits/transactions?limit=10"
```

---

## 📊 **Analytics Testing**

### **1. Dashboard Analytics**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-app.onrender.com/api/analytics/dashboard"
```

**Expected Response:**
```json
{
  "total_jobs": 5,
  "active_jobs": 3,
  "total_candidates": 15,
  "qualified_candidates": 8,
  "total_interviews": 6,
  "completed_interviews": 4,
  "ai_usage": {
    "deepseek_requests": 45,
    "openai_requests": 2,
    "offline_requests": 8,
    "total_cost": "$0.23"
  },
  "recent_activity": [...]
}
```

---

## 🔄 **Fallback Testing**

### **1. Test DeepSeek Failure Simulation**
To test fallbacks, temporarily remove the DeepSeek API key:

```bash
# In Render dashboard, remove DEEPSEEK_API_KEY
# Then test resume analysis - should fall back to offline
curl -X POST "https://your-app.onrender.com/api/resumes/analyze" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "Test resume content...",
    "job_requirements": ["Python", "FastAPI"]
  }'
```

**Should return `"provider": "offline"` in response**

### **2. Test Complete Offline Mode**
Remove all AI API keys and verify all features still work:

```bash
# Remove both DEEPSEEK_API_KEY and OPENAI_API_KEY
# All endpoints should still function with offline algorithms
```

---

## 🚨 **Error Testing**

### **1. Invalid Authentication**
```bash
curl -H "Authorization: Bearer invalid_token" \
  "https://your-app.onrender.com/api/jobs/"
```

**Expected Response:**
```json
{
  "detail": "Could not validate credentials"
}
```

### **2. Invalid File Upload**
```bash
curl -X POST "https://your-app.onrender.com/api/resumes/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@large_file.exe"
```

**Expected Response:**
```json
{
  "detail": "File type not allowed. Allowed types: .pdf, .doc, .docx, .txt"
}
```

---

## 📈 **Performance Testing**

### **1. Response Time Testing**
```bash
# Test response times for different providers
time curl -X POST "https://your-app.onrender.com/api/resumes/analyze" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"resume_text": "test", "job_requirements": ["Python"]}'
```

**Expected Times:**
- **DeepSeek**: 2-3 seconds
- **OpenAI**: 2-4 seconds
- **Offline**: 0.1-0.2 seconds

### **2. Concurrent Request Testing**
```bash
# Test multiple simultaneous requests
for i in {1..5}; do
  curl -X POST "https://your-app.onrender.com/api/resumes/analyze" \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"resume_text": "test '$i'", "job_requirements": ["Python"]}' &
done
wait
```

---

## ✅ **Test Checklist**

### **Basic Functionality:**
- [ ] Health check responds correctly
- [ ] API documentation loads
- [ ] User registration works
- [ ] User login works
- [ ] JWT tokens are valid

### **AI Features:**
- [ ] Resume analysis works with DeepSeek
- [ ] Resume analysis falls back to offline
- [ ] Candidate matching works
- [ ] Interview questions generate
- [ ] All providers show correct status

### **Core Features:**
- [ ] Job creation and management
- [ ] Resume upload and processing
- [ ] Candidate management
- [ ] Interview scheduling
- [ ] Credit system tracking

### **Error Handling:**
- [ ] Invalid authentication rejected
- [ ] Invalid file types rejected
- [ ] API rate limits respected
- [ ] Graceful error messages

### **Performance:**
- [ ] Response times acceptable
- [ ] Concurrent requests handled
- [ ] Memory usage stable
- [ ] No memory leaks

---

## 🎯 **Success Criteria**

Your RecruitAI backend is working correctly if:

✅ **All endpoints respond without errors**  
✅ **AI features work with available providers**  
✅ **Fallbacks activate when needed**  
✅ **File uploads process correctly**  
✅ **Authentication and authorization work**  
✅ **Credit system tracks usage**  
✅ **Analytics provide meaningful data**  

## 🔧 **Troubleshooting**

### **Common Issues:**

**1. "AI service unavailable"**
- Check API keys in environment variables
- Verify network connectivity
- Confirm offline fallback is working

**2. "Database connection error"**
- Check DATABASE_URL environment variable
- Verify PostgreSQL service is running
- Check database permissions

**3. "File upload fails"**
- Check file size limits
- Verify file type is allowed
- Check upload directory permissions

**4. "High response times"**
- Monitor AI provider response times
- Check server resource usage
- Consider caching frequently used data

---

## 📞 **Support**

If tests fail:
1. Check the application logs in Render dashboard
2. Verify all environment variables are set
3. Test locally with the same configuration
4. Review the error messages for specific issues

**Your RecruitAI backend is now fully tested and production-ready!** 🚀

