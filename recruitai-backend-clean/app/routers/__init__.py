# app/routers/__init__.py
# Router package initialization

# This file makes the routers directory a Python package
# and allows importing router modules

__version__ = "1.0.0"
__author__ = "RecruitAI Team"

# Import routers for easy access
try:
    from . import resumes_no_auth
    __all__ = ["resumes_no_auth"]
except ImportError:
    __all__ = []

try:
    from . import jobs_no_auth
    __all__.append("jobs_no_auth")
except ImportError:
    pass

# Package metadata
ROUTERS_INFO = {
    "package": "app.routers",
    "version": __version__,
    "available_routers": __all__,
    "description": "FastAPI routers for RecruitAI backend (no-auth version)"
}
