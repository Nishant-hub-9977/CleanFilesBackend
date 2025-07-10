from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn
import os
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import auth router with fallback
auth_router = None
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
        "docs": "/docs",
        "auth_router_status": "loaded" if auth_router else "fallback"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "RecruitAI Backend",
        "timestamp": "2024-01-01T00:00:00Z",
        "auth_available": auth_router is not None
    }

# API status endpoint
@app.get("/api/status")
async def api_status():
    return {
        "api_status": "operational",
        "endpoints": {
            "auth": "available" if auth_router else "fallback",
            "health": "available"
        },
        "cors_enabled": True,
        "frontend_domains": [
            "recruiterainew.netlify.app"
        ]
    }

# Include authentication router
if auth_router:
    app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])
    logger.info("Auth router included successfully")
else:
    logger.error("Auth router not available")

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

