"""Local development: DEBUG on, cookies allowed over HTTP."""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
