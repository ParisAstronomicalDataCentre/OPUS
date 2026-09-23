"""
Configuration of OPUS (UWS server and client)

Settings are read from environment variables prefixed with OPUS_ and from the .env
file in the OPUS directory (see .env.dist and base.py).
"""

from .base import APP_PATH, CommonSettings
from .client import ClientSettings
from .server import ServerSettings

__all__ = ["APP_PATH", "CommonSettings", "ClientSettings", "ServerSettings"]
