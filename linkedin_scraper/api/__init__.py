"""API module for the LinkedIn Knowledge Management System."""

from .app import create_app
from .routes import api_bp, web_bp

__all__ = ['create_app', 'api_bp', 'web_bp']