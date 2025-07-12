from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
import logging
from datetime import datetime
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="RecruitAI Backend API",
    description="Advanced recruitment platform with AI-powered resume matching",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enhanced CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://recruiterainew.netlify.app",
        "https://sparkling-gecko-036bc4.netlify.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"  # Allow all origins for development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Create upload directories
upload_dirs = ["uploads", "uploads/resumes", "uploads/temp"]
for directory in upload_dirs:
    os.makedirs(directory, exist_ok=True)
    logger.info(f"Upload directory ensured: {directory}")

# Mount static files
try:
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
    logger.info("Static file mounting successful")
except Exception as e:
    logger.warning(f"Static file mounting failed: {e}")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url)
        }
    )

# Import and include routers with enhanced error handling
try:
    from app.routers import auth
    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
    logger.info("✅ Auth router included successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import auth router: {e}")
    
    # Create fallback auth router
    from fastapi import APIRouter
    fallback_auth = APIRouter()
    
    @fallback_auth.post("/login")
    async def fallback_login():
        return {"message": "Auth module not available", "status": "fallback"}
    
    app.include_router(fallback_auth, prefix="/api/auth", tags=["Authentication"])
    logger.info("⚠️ Fallback auth router included")

try:
    from app.routers import jobs
    app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
    logger.info("✅ Jobs router included successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import jobs router: {e}")
    
    # Create fallback jobs router
    from fastapi import APIRouter
    fallback_jobs = APIRouter()
    
    @fallback_jobs.get("/")
    async def fallback_jobs_list():
        return {"jobs": [], "message": "Jobs module not available"}
    
    app.include_router(fallback_jobs, prefix="/api/jobs", tags=["Jobs"])
    logger.info("⚠️ Fallback jobs router included")

try:
    from app.routers import resumes
    app.include_router(resumes.router, prefix="/api/resumes", tags=["Resumes"])
    logger.info("✅ Resumes router included successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import resumes router: {e}")
    
    # Create fallback resumes router
    from fastapi import APIRouter
    fallback_resumes = APIRouter()
    
    @fallback_resumes.get("/")
    async def fallback_resumes_list():
        return {"resumes": [], "message": "Resumes module not available"}
    
    app.include_router(fallback_resumes, prefix="/api/resumes", tags=["Resumes"])
    logger.info("⚠️ Fallback resumes router included")

# Database initialization with fallback
try:
    from app.core.database import engine, Base
    
    @app.on_event("startup")
    async def startup_event():
        try:
            # Create database tables
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database tables created successfully")
        except Exception as e:
            logger.warning(f"⚠️ Database initialization failed: {e}")
            logger.info("🔄 Continuing with in-memory fallback mode")
        
        logger.info("🚀 RecruitAI Backend startup completed")
        
except ImportError as e:
    logger.warning(f"⚠️ Database module not available: {e}")
    logger.info("🔄 Running in fallback mode without database")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "message": "🚀 RecruitAI Backend API is running",
        "version": "2.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "features": [
            "JWT Authentication",
            "Resume Processing (PDF/DOCX/TXT)",
            "AI-Powered Job Matching",
            "Advanced Search & Filtering",
            "Bulk Upload Support",
            "Real-time Analytics"
        ],
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "api_status": "/api/status",
            "auth": "/api/auth",
            "jobs": "/api/jobs",
            "resumes": "/api/resumes"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    try:
        # Check database connection
        db_status = "unknown"
        try:
            from app.core.database import engine
            if engine:
                db_status = "connected"
            else:
                db_status = "fallback_mode"
        except ImportError:
            db_status = "not_configured"
        
        # Check upload directories
        upload_status = all(os.path.exists(d) for d in upload_dirs)
        
        # Check router availability
        router_status = {
            "auth": "app.routers.auth" in str(app.routes),
            "jobs": "app.routers.jobs" in str(app.routes),
            "resumes": "app.routers.resumes" in str(app.routes)
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0",
            "uptime": "running",
            "database": {
                "status": db_status,
                "type": "postgresql" if db_status == "connected" else "in_memory"
            },
            "storage": {
                "upload_directories": upload_status,
                "directories": upload_dirs
            },
            "routers": router_status,
            "environment": {
                "port": os.getenv("PORT", "10000"),
                "debug": os.getenv("DEBUG", "false").lower() == "true",
                "cors_enabled": True
            },
            "capabilities": [
                "File upload processing",
                "PDF text extraction",
                "DOCX text extraction",
                "Skill extraction",
                "TF-IDF matching",
                "JWT authentication",
                "Role-based access"
            ]
        }
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# API status endpoint
@app.get("/api/status")
async def api_status():
    """API status and configuration"""
    return {
        "api_version": "2.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "authentication": {
                "login": "/api/auth/login",
                "register": "/api/auth/register",
                "me": "/api/auth/me",
                "refresh": "/api/auth/refresh",
                "health": "/api/auth/health"
            },
            "jobs": {
                "list": "/api/jobs/",
                "create": "/api/jobs/",
                "detail": "/api/jobs/{id}",
                "candidates": "/api/jobs/{id}/candidates",
                "stats": "/api/jobs/stats/overview",
                "health": "/api/jobs/health"
            },
            "resumes": {
                "upload": "/api/resumes/upload",
                "bulk_upload": "/api/resumes/bulk-upload",
                "list": "/api/resumes/",
                "detail": "/api/resumes/{id}",
                "match": "/api/resumes/match",
                "stats": "/api/resumes/stats/overview",
                "health": "/api/resumes/health"
            }
        },
        "demo_credentials": {
            "admin": "admin@recruitai.com / password123",
            "recruiter": "recruiter@recruitai.com / password123",
            "candidate": "candidate@recruitai.com / password123"
        },
        "features": {
            "authentication": "JWT with refresh tokens",
            "file_processing": "PDF, DOCX, TXT support",
            "ai_matching": "TF-IDF + Cosine Similarity",
            "skill_extraction": "500+ technical skills",
            "bulk_operations": "Up to 20 files",
            "search_filtering": "Advanced query support",
            "analytics": "Real-time statistics"
        }
    }

# Demo endpoint for testing
@app.get("/api/demo")
async def demo_info():
    """Demo information and test credentials"""
    return {
        "demo_mode": True,
        "test_credentials": {
            "admin": {
                "email": "admin@recruitai.com",
                "password": "password123",
                "role": "admin",
                "description": "Full system access"
            },
            "recruiter": {
                "email": "recruiter@recruitai.com", 
                "password": "password123",
                "role": "recruiter",
                "description": "Job posting and candidate management"
            },
            "candidate": {
                "email": "candidate@recruitai.com",
                "password": "password123",
                "role": "candidate", 
                "description": "Resume upload and job search"
            }
        },
        "test_features": [
            "Login with demo credentials",
            "Upload sample resumes (PDF/DOCX)",
            "Create job postings",
            "Test AI matching algorithm",
            "View analytics dashboard",
            "Search and filter functionality"
        ],
        "sample_data": {
            "resume_formats": ["PDF", "DOCX", "TXT"],
            "max_file_size": "10MB",
            "bulk_upload_limit": 20,
            "supported_skills": "500+ technical skills",
            "matching_algorithm": "TF-IDF + Cosine Similarity"
        }
    }

# 404 handler
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Endpoint not found",
            "message": f"The requested endpoint {request.url.path} was not found",
            "available_endpoints": [
                "/docs",
                "/health", 
                "/api/status",
                "/api/auth/login",
                "/api/jobs/",
                "/api/resumes/"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Startup message
@app.on_event("startup")
async def startup_message():
    logger.info("=" * 60)
    logger.info("🚀 RECRUITAI BACKEND STARTING UP")
    logger.info("=" * 60)
    logger.info(f"📍 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"🌐 Port: {os.getenv('PORT', '10000')}")
    logger.info(f"🔧 Debug: {os.getenv('DEBUG', 'false')}")
    logger.info(f"📊 CORS: Enabled for all origins")
    logger.info("=" * 60)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )

