"""
RecruitAI Backend - FastAPI Application
AI-Powered Recruitment Platform
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import os
from contextlib import asynccontextmanager

from app.core.database import engine, Base
from app.core.config import settings
from app.routers import auth, users, jobs, candidates, interviews, resumes, analytics, credits

# Create database tables
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    pass

# Initialize FastAPI app
app = FastAPI(
    title="RecruitAI API",
    description="AI-Powered Recruitment Platform - Backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(candidates.router, prefix="/api/candidates", tags=["Candidates"])
app.include_router(interviews.router, prefix="/api/interviews", tags=["Interviews"])
app.include_router(resumes.router, prefix="/api/resumes", tags=["Resumes"])
app.include_router(credits.router, prefix="/api/credits", tags=["Credits"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "RecruitAI API is running"}

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>RecruitAI API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; text-align: center; }
            .feature { margin: 20px 0; padding: 15px; background: #ecf0f1; border-radius: 5px; }
            .links { text-align: center; margin-top: 30px; }
            .links a { margin: 0 15px; padding: 10px 20px; background: #3498db; color: white; text-decoration: none; border-radius: 5px; }
            .links a:hover { background: #2980b9; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 RecruitAI API</h1>
            <p style="text-align: center; color: #7f8c8d; font-size: 18px;">AI-Powered Recruitment Platform Backend</p>
            
            <div class="feature">
                <h3>🤖 AI-Powered Interviews</h3>
                <p>Advanced AI conducts comprehensive video interviews with emotion detection and real-time analysis.</p>
            </div>
            
            <div class="feature">
                <h3>📄 Smart Resume Matching</h3>
                <p>Intelligent resume parsing and matching with automatic scoring against job requirements.</p>
            </div>
            
            <div class="feature">
                <h3>📊 Advanced Analytics</h3>
                <p>Detailed reports with skill assessments, AI recommendations, and hiring insights.</p>
            </div>
            
            <div class="feature">
                <h3>💳 Credit System</h3>
                <p>Flexible credit-based usage model with 10 free credits for new users.</p>
            </div>
            
            <div class="links">
                <a href="/docs">API Documentation</a>
                <a href="/health">Health Check</a>
                <a href="/redoc">ReDoc</a>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )

