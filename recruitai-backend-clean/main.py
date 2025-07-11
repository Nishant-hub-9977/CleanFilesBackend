import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.routers import auth, jobs, resumes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RecruitAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://recruiterainew.netlify.app", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

uploads_dir = "uploads"
os.makedirs(uploads_dir, exist_ok=True)
logger.info(f"Upload directories created: {uploads_dir}")
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    logger.info("Database connected successfully")

    async def get_db():
        async with async_session() as session:
            yield session

    from sqlalchemy import text
    @app.on_event("startup")
    async def startup_event():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
else:
    logger.warning("DATABASE_URL not set, skipping DB initialization")
    async def get_db():
        yield None

app.include_router(auth.router)
logger.info("Auth router included successfully")
app.include_router(jobs.router)
logger.info("Jobs router included successfully")
app.include_router(resumes.router)
logger.info("Resumes router included successfully")

@app.get("/")
def read_root():
    return {"message": "RecruitAI Backend is running"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting RecruitAI Backend...")
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
