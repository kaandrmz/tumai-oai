"""
Configuration module for the multiagent system.
Handles environment variables and LLM setup.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

# Load environment variables
this_dir = Path(__file__).parent
load_dotenv(this_dir.parent / ".env")

# Set up OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found. Make sure it's set in your .env file.")

# Paths configuration
DOCUMENTS_PATH = os.getenv("DOCUMENTS_PATH", "./documents")

# LLM configuration
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.5"))

# Backend api
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

# Supabase configuration for Log Visualization
NEXT_PUBLIC_SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not NEXT_PUBLIC_SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Supabase URL or Service Key not found. Make sure they are set in your .env file.")

SELF_NAME = os.getenv("SELF_NAME")
SELF_URL = os.getenv("SELF_URL")
SELF_LOGO_URL = os.getenv("SELF_LOGO_URL")
if not SELF_NAME or not SELF_URL or not SELF_LOGO_URL:
    raise ValueError("Self name or URL or logo URL not found. Make sure they are set in your .env file.")
