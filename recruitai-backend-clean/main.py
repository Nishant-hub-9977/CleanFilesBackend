from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from datetime import datetime
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="RecruitAI Backend (No Auth)",
    description="AI-Powered Recruitment Platform Backend - No Authentication Version",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration - Allow all origins for demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": str(exc)
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "recruitai-backend-no-auth",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "features": [
            "Resume upload and processing",
            "Job management",
            "Resume matching",
            "File processing (PDF, DOCX, TXT)",
            "Statistics and analytics",
            "No authentication required"
        ],
        "endpoints": {
            "resumes": "/api/resumes/",
            "jobs": "/api/jobs/",
            "health": "/health",
            "docs": "/docs"
        }
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RecruitAI Backend (No Auth Version)",
        "version": "2.0.0",
        "status": "running",
        "documentation": "/docs",
        "health": "/health",
        "features": [
            "No authentication required",
            "Resume processing",
            "Job management", 
            "AI matching",
            "File upload support"
        ]
    }

# Import and include routers (no auth versions)
try:
    from app.routers import resumes_no_auth
    app.include_router(resumes_no_auth.router, prefix="/api/resumes", tags=["resumes"])
    logger.info("Resumes router loaded successfully")
except ImportError as e:
    logger.warning(f"Could not import resumes router: {e}")

try:
    from app.routers import jobs_no_auth
    app.include_router(jobs_no_auth.router, prefix="/api/jobs", tags=["jobs"])
    logger.info("Jobs router loaded successfully")
except ImportError as e:
    logger.warning(f"Could not import jobs router: {e}")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("RecruitAI Backend (No Auth) starting up...")
    logger.info("Authentication: DISABLED")
    logger.info("CORS: Enabled for all origins")
    logger.info("Documentation available at: /docs")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("RecruitAI Backend (No Auth) shutting down...")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )

