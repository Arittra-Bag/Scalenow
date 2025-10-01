"""FastAPI application factory for the LinkedIn Knowledge Management System."""

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import logging
from typing import Optional

from ..utils.config import Config
from ..utils.logger import setup_logger
from .routes import api_router, web_router
from .middleware import setup_middleware

logger = logging.getLogger(__name__)


def create_app(config: Optional[Config] = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    
    if config is None:
        config = Config.from_env()
    
    # Initialize logging
    setup_logger(config=config)
    
    # Create FastAPI app
    app = FastAPI(
        title="LinkedIn Knowledge Management System",
        description="AI-powered system for extracting and organizing knowledge from LinkedIn posts",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Setup custom middleware
    setup_middleware(app, config)
    
    # Include routers
    app.include_router(api_router, prefix="/api/v1", tags=["API"])
    app.include_router(web_router, tags=["Web"])
    
    # Setup static files and templates
    setup_static_files(app)
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Add startup and shutdown events
    setup_events(app, config)
    
    logger.info("FastAPI application created successfully")
    return app


def setup_static_files(app: FastAPI):
    """Setup static files and templates."""
    try:
        # Static files directory
        static_dir = Path(__file__).parent / "static"
        static_dir.mkdir(exist_ok=True)
        
        # Templates directory
        templates_dir = Path(__file__).parent / "templates"
        templates_dir.mkdir(exist_ok=True)
        
        # Mount static files
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        # Setup templates
        templates = Jinja2Templates(directory=str(templates_dir))
        app.state.templates = templates
        
        logger.info("Static files and templates configured")
        
    except Exception as e:
        logger.error(f"Failed to setup static files: {e}")


def setup_exception_handlers(app: FastAPI):
    """Setup global exception handlers."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "status_code": exc.status_code,
                "path": str(request.url)
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "Internal server error",
                "status_code": 500,
                "path": str(request.url)
            }
        )


def setup_events(app: FastAPI, config: Config):
    """Setup startup and shutdown events."""
    
    @app.on_event("startup")
    async def startup_event():
        """Application startup tasks."""
        logger.info("LinkedIn Knowledge Management System starting up...")
        
        # Initialize application state
        app.state.config = config
        
        # Create necessary directories
        config.create_directories()
        
        logger.info("Application startup completed")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown tasks."""
        logger.info("LinkedIn Knowledge Management System shutting down...")
        
        # Cleanup tasks here if needed
        
        logger.info("Application shutdown completed")


# Health check endpoint
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "LinkedIn Knowledge Management System",
        "version": "1.0.0"
    }


# Create the main app instance
app = create_app()