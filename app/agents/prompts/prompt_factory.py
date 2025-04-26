"""
Fixed prompt factory module with caching for improved performance.
"""
from typing import Dict
from pathlib import Path
import logging
import functools
import json
from cachetools import TTLCache, cached

# Configure logging
logger = logging.getLogger(__name__)

# Get the current directory
current_dir = Path(__file__).parent
PROMPTS_FOLDER = current_dir

# Create a TTL cache for prompts to avoid reading files repeatedly
prompt_template_cache = TTLCache(maxsize=50, ttl=3600)  # Cache for 1 hour
prompt_result_cache = TTLCache(maxsize=200, ttl=600)    # Cache for 10 minutes

# Cache prompt templates (the raw file contents)
@cached(cache=prompt_template_cache)
def _load_prompt_template(prompt_name: str) -> str:
    """
    Load a prompt template from file, with caching.

    Args:
        prompt_name: Name of the prompt template file (without .txt extension)

    Returns:
        The prompt template text
    """
    try:
        prompt_path = PROMPTS_FOLDER / f"{prompt_name}.txt"
        with open(prompt_path, "r") as file:
            prompt = file.read()
        return prompt
    except FileNotFoundError:
        logger.error(f"Prompt template file {prompt_name}.txt not found")
        # Return an empty string as fallback
        return ""
    except Exception as e:
        logger.error(f"Error loading prompt template {prompt_name}: {e}")
        return ""

def _create_cache_key(vars_dict: Dict[str, str]) -> str:
    """
    Create a hashable cache key from a variables dictionary.

    Args:
        vars_dict: Dictionary of variables

    Returns:
        String representation of the dictionary for use as a cache key
    """
    # Sort keys for consistent ordering and create a string representation
    try:
        # Use JSON for a more reliable string representation
        return json.dumps(vars_dict, sort_keys=True)
    except:
        # Fallback if JSON conversion fails
        items = sorted(vars_dict.items())
        return str(items)

# Non-caching version of get_prompt for direct calls
def get_prompt(prompt_name: str, vars: Dict[str, str]) -> str:
    """
    Get a prompt with variables replaced.

    Args:
        prompt_name: Name of the prompt template to use
        vars: Dictionary of variables to replace in the template

    Returns:
        The prompt with variables replaced
    """
    # Load the prompt template (cached)
    prompt = _load_prompt_template(prompt_name)

    # Replace variables
    for key, value in vars.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", value)

    return prompt

# Cached version that uses a hashable key
@cached(cache=prompt_result_cache)
def get_prompt_cached(prompt_name: str, vars_key: str) -> str:
    """
    Get a prompt with variables replaced (cached version).

    Args:
        prompt_name: Name of the prompt template to use
        vars_key: JSON string representation of the variables dictionary

    Returns:
        The prompt with variables replaced
    """
    # Convert string back to dictionary
    vars = json.loads(vars_key)

    # Load the prompt template (cached)
    prompt = _load_prompt_template(prompt_name)

    # Replace variables
    for key, value in vars.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", value)

    return prompt

# Optimized version with automatic key generation
def get_prompt_optimized(prompt_name: str, vars: Dict[str, str]) -> str:
    """
    Optimized version of get_prompt with caching.
    Automatically handles creating a proper cache key.

    Args:
        prompt_name: Name of the prompt template to use
        vars: Dictionary of variables to replace in the template

    Returns:
        The prompt with variables replaced
    """
    # First attempt: try to use the cached version
    try:
        # Create a proper cache key from the variables dictionary
        vars_key = _create_cache_key(vars)
        # Use the cached version
        return get_prompt_cached(prompt_name, vars_key)
    except Exception as e:
        # If caching fails, fall back to direct version
        logger.warning(f"Prompt caching failed, using direct version: {e}")
        return get_prompt(prompt_name, vars)