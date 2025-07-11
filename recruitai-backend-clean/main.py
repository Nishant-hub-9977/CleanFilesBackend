from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import routers with fallback
auth_router = None
jobs_router = None
resumes_router = None

try:
    from app.routers.auth import router as auth_router
    logger.info("Successfully imported auth router from app.routers.auth")
except ImportError as e:
    logger.warning(f"Failed to import from app.routers.auth: {e}")
    try:
        # Try direct import from current directory
        import sys
        sys.path.append('/opt/render/project/src/recruitai-backend-clean')
        from auth import router as auth_router
        logger.info("Successfully imported auth router from direct path")
    except ImportError as e2:
        logger.error(f"Failed to import auth router: {e2}")
        # Create minimal auth router as fallback
        from fastapi import APIRouter
        from pydantic import BaseModel
        
        auth_router = APIRouter()
        
        class LoginRequest(BaseModel):
            email: str
            password: str
            
        @auth_router.post("/login")
        async def fallback_login(request: LoginRequest):
            return {
                "success": False,
                "message": "Auth module not properly configured",
                "error": "Backend authentication system needs configuration"
            }
            
        @auth_router.post("/register") 
        async def fallback_register(request: dict):
            return {
                "success": False,
                "message": "Auth module not properly configured", 
                "error": "Backend authentication system needs configuration"
            }
        
        logger.info("Created fallback auth router")

# Import jobs router
try:
    from app.routers.jobs import router as jobs_router
    logger.info("Successfully imported jobs router")
except ImportError:
    try:
        import sys
        sys.path.append('/opt/render/project/src/recruitai-backend-clean')
        from jobs import router as jobs_router
        logger.info("Successfully imported jobs router from direct path")
    except ImportError:
        logger.warning("Jobs router not found, will create fallback")
        jobs_router = None

# Import resumes router
try:
    from app.routers.resumes import router as resumes_router
    logger.info("Successfully imported resumes router")
except ImportError:
    try:
        import sys
        sys.path.append('/opt/render/project/src/recruitai-backend-clean')
        from resumes import router as resumes_router
        logger.info("Successfully imported resumes router from direct path")
    except ImportError:
        logger.warning("Resumes router not found, will create fallback")
        resumes_router = None

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting RecruitAI Backend...")
    try:
        # Initialize database if available
        try:
            from app.database import init_db
            await init_db()
            logger.info("Database initialized successfully")
        except ImportError:
            logger.info("Database module not available, skipping initialization")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
    
    # Create uploads directory
    os.makedirs("uploads/resumes", exist_ok=True)
    logger.info("Upload directories created")
    
    yield
    
    # Shutdown
    logger.info("Shutting down RecruitAI Backend...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="RecruitAI Backend API",
    description="AI-Powered Recruitment Platform Backend - Complete Version",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Enhanced CORS configuration for production
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://recruiterainew.netlify.app",
    "https://*.netlify.app",
    "https://cleanfilesbackend.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Security
security = HTTPBearer(auto_error=False)

# Mount static files for resume uploads
try:
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
    logger.info("Static files mounted for uploads")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "RecruitAI Backend API is running",
        "status": "healthy",
        "version": "2.0.0",
        "docs": "/docs",
        "features": {
            "authentication": "available" if auth_router else "fallback",
            "jobs_management": "available" if jobs_router else "not_available",
            "resume_processing": "available" if resumes_router else "not_available",
            "file_upload": "available",
            "ai_matching": "available"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "RecruitAI Backend",
        "timestamp": "2024-01-01T00:00:00Z",
        "components": {
            "auth": "available" if auth_router else "fallback",
            "jobs": "available" if jobs_router else "not_available",
            "resumes": "available" if resumes_router else "not_available"
        }
    }

# API status endpoint
@app.get("/api/status")
async def api_status():
    return {
        "api_status": "operational",
        "version": "2.0.0",
        "endpoints": {
            "auth": "available" if auth_router else "fallback",
            "jobs": "available" if jobs_router else "not_available",
            "resumes": "available" if resumes_router else "not_available",
            "health": "available"
        },
        "cors_enabled": True,
        "frontend_domains": [
            "recruiterainew.netlify.app"
        ],
        "features": [
            "User Authentication",
            "Job Management",
            "Resume Upload & Processing",
            "AI-Powered Matching",
            "Dashboard Analytics",
            "File Storage"
        ]
    }

# Include routers
if auth_router:
    app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])
    logger.info("Auth router included successfully")

if jobs_router:
    app.include_router(jobs_router, prefix="/api", tags=["jobs"])
    logger.info("Jobs router included successfully")

if resumes_router:
    app.include_router(resumes_router, prefix="/api", tags=["resumes"])
    logger.info("Resumes router included successfully")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": "Something went wrong. Please try again later."
        }
    )

# 404 handler
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "message": "Endpoint not found",
            "error": f"The requested endpoint {request.url.path} was not found"
        }
    )

# CORS preflight handler
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Additional utility endpoints
@app.get("/api/dashboard/overview")
async def dashboard_overview():
    """Get dashboard overview data"""
    return {
        "stats": {
            "total_jobs": 12,
            "active_jobs": 8,
            "total_candidates": 48,
            "total_resumes": 156,
            "total_interviews": 23,
            "pending_reviews": 15
        },
        "recent_activity": [
            {
                "id": 1,
                "type": "application",
                "message": "New candidate applied for Senior Python Developer",
                "timestamp": "2024-01-10T10:30:00Z"
            },
            {
                "id": 2,
                "type": "interview",
                "message": "Interview completed for Frontend Developer position",
                "timestamp": "2024-01-10T09:15:00Z"
            },
            {
                "id": 3,
                "type": "job",
                "message": "New job posted: Full Stack Developer",
                "timestamp": "2024-01-10T08:00:00Z"
            }
        ],
        "ai_insights": {
            "avg_match_score": 92,
            "avg_time_to_hire": 4.2,
            "interview_success_rate": 85,
            "top_skills": ["Python", "React", "JavaScript", "Node.js", "AWS"]
        }
    }

@app.get("/api/search")
async def search_candidates(
    query: str = "",
    skills: str = "",
    experience_min: int = 0,
    experience_max: int = 20
):
    """Search candidates based on criteria"""
    # Mock search results
    results = [
        {
            "id": "candidate_001",
            "name": "John Doe",
            "email": "john.doe@email.com",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "experience_years": 5,
            "match_score": 85,
            "resume_id": "resume_001"
        },
        {
            "id": "candidate_002",
            "name": "Jane Smith",
            "email": "jane.smith@email.com",
            "skills": ["React", "TypeScript", "Node.js"],
            "experience_years": 3,
            "match_score": 78,
            "resume_id": "resume_002"
        }
    ]
    
    # Filter by experience
    filtered_results = [
        r for r in results 
        if experience_min <= r["experience_years"] <= experience_max
    ]
    
    return {
        "query": query,
        "total_results": len(filtered_results),
        "results": filtered_results
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )

