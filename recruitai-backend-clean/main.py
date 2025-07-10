from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn
import os
from contextlib import asynccontextmanager
import logging

# Import routers
try:
    from app.routers import auth
    from app.database import init_db
    from app.models import User
except ImportError as e:
    print(f"Import warning: {e}")
    # Create minimal auth router if import fails
    from fastapi import APIRouter
    auth = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting RecruitAI Backend...")
    try:
        # Initialize database if available
        if 'init_db' in globals():
            await init_db()
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down RecruitAI Backend...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="RecruitAI Backend API",
    description="AI-Powered Recruitment Platform Backend",
    version="1.0.0",
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

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "RecruitAI Backend API is running",
        "status": "healthy",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "RecruitAI Backend",
        "timestamp": "2024-01-01T00:00:00Z"
    }

# API status endpoint
@app.get("/api/status")
async def api_status():
    return {
        "api_status": "operational",
        "endpoints": {
            "auth": "available",
            "health": "available"
        },
        "cors_enabled": True,
        "frontend_domains": [
            "recruiterainew.netlify.app"
        ]
    }

# Include authentication router - FIXED: removed .router
app.include_router(auth, prefix="/api/auth", tags=["authentication"])

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

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )

