"""
Configuration module for the multiagent system.
Handles environment variables and LLM setup.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

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
