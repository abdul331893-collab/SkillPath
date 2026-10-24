from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.config import settings
from app.core.logging import logger
from app.api.routes import (
    health,
    auth,
    profiles,
    resumes,
    assessments,
    skills,
    careers,
    roadmaps,
    jobs,
    applications,
    admin,
    rag
)

app = FastAPI(
    title=settings.APP_NAME,
    description="SkillPath AI: Adaptive Career Intelligence System using LLMs and RAG.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
origins = settings.cors_origins
logger.info(f"Configuring CORS with allowed origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Validation Exception Handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    serializable_errors = []
    for err in exc.errors():
        clean_err = dict(err)
        if "ctx" in clean_err and isinstance(clean_err["ctx"], dict):
            clean_err["ctx"] = {k: str(v) for k, v in clean_err["ctx"].items()}
        serializable_errors.append(clean_err)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Request validation failed", "errors": serializable_errors},
    )

@app.on_event("startup")
async def startup_event():
    from app.core import security
    security.init_firebase()

    try:
        from app.services.career_service import CareerService
        CareerService.initialize_default_domains()
    except Exception as e:
        logger.warning(f"Startup career domains seed note: {e}")

    try:
        from app.services.job_matching import JobMatchingService
        JobMatchingService.initialize_default_jobs()
    except Exception as e:
        logger.warning(f"Startup jobs seed note: {e}")

    try:
        from app.services.assessment_service import AssessmentService
        AssessmentService.initialize_default_questions()
    except Exception as e:
        logger.warning(f"Startup assessment questions seed note: {e}")

# Include API routers under /api/v1
api_v1_prefix = "/api/v1"
app.include_router(health.router, prefix=api_v1_prefix)
app.include_router(auth.router, prefix=api_v1_prefix)
app.include_router(profiles.router, prefix=api_v1_prefix)
app.include_router(resumes.router, prefix=api_v1_prefix)
app.include_router(assessments.router, prefix=api_v1_prefix)
app.include_router(skills.router, prefix=api_v1_prefix)
app.include_router(careers.router, prefix=api_v1_prefix)
app.include_router(roadmaps.router, prefix=api_v1_prefix)
app.include_router(jobs.router, prefix=api_v1_prefix)
app.include_router(applications.router, prefix=api_v1_prefix)
app.include_router(admin.router, prefix=api_v1_prefix)
app.include_router(rag.router, prefix=api_v1_prefix)

@app.get("/")
async def root():
    return {
        "message": "Welcome to SkillPath AI API",
        "documentation": "/docs",
        "health": f"{api_v1_prefix}/health"
    }
