"""
Security agent implementation for the multiagent system.
Optimized for better performance.
"""

from app.config import OPENAI_API_KEY
from openai import OpenAI
from typing import List, Dict, Tuple, Set
import re
import threading
import logging
import functools
from cachetools import TTLCache, cached

# Configure logging
logger = logging.getLogger(__name__)

# Create TTL caches for security checks
security_keyword_cache = TTLCache(maxsize=500, ttl=3600)  # Cache for 1 hour
security_analysis_cache = TTLCache(maxsize=200, ttl=1800)  # Cache for 30 minutes
prompt_injection_cache = TTLCache(maxsize=200, ttl=3600)  # Cache for 1 hour


class SecurityAgent:
    """
    Security agent with caching and batch processing capabilities.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, custom_keywords: List[str] = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SecurityAgent, cls).__new__(cls)
                cls._instance.initialized = False
            return cls._instance

    def __init__(self, custom_keywords: List[str] = None):
        """Initialize the security agent with default and custom keywords."""
        # Use singleton pattern to avoid multiple instances
        if self.initialized:
            # If custom keywords are provided on subsequent initialization, add them
            if custom_keywords:
                self._add_custom_keywords(custom_keywords)
            return

        self.role = "Security Officer"
        self.goal = "Ensure no confidential information is exposed during the educational session"
        self.backstory = """
        You are a security professional specialized in information security.
        You monitor all exchanges to prevent data breaches and exposure of confidential information.
        You are vigilant and proactive in identifying potential security risks.
        You can intervene in conversations when sensitive information might be exposed.
        You understand the balance between sharing knowledge and protecting confidential data.
        """

        # Default sensitive keywords (from SecurityFilter)
        self.sensitive_keywords = set([
            "confidential",
            "secret",
            "private",
            "personal",
            "sensitive",
            "password",
            "ssn",
            "social security",
            "credit card",
            "phone number",
            "address",
            "email address",
            "classified",
            "internal only",
            "not for distribution",
            "proprietary",
            "restricted",
        ])

        # Add custom keywords if provided
        if custom_keywords:
            self._add_custom_keywords(custom_keywords)

        # Regex patterns for prompt injection detection
        self.injection_patterns = [
            r"ignore\s+previous\s+instructions",
            r"disregard\s+previous\s+instructions",
            r"forget\s+your\s+instructions",
            r"act\s+as\s+if\s+you\s+were",
            r"you\s+are\s+now\s+a\s+different",
            r"stop\s+being\s+a\s+security\s+agent",
            r"pretend\s+to\s+be\s+a\s+different",
        ]

        # Compile the regex patterns for faster matching
        self.injection_regex = re.compile("|".join(self.injection_patterns), re.IGNORECASE)

        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)

        self.initialized = True
        logger.info("SecurityAgent initialized")

    def _add_custom_keywords(self, custom_keywords: List[str]):
        """Add custom keywords to the sensitive keywords set."""
        if not custom_keywords:
            return

        self.sensitive_keywords.update(custom_keywords)
        logger.info(f"Added {len(custom_keywords)} custom keywords to security agent")

    @cached(cache=security_keyword_cache)
    def contains_sensitive_info(self, text: str) -> bool:
        """
        Check if the text contains any sensitive keywords. (from SecurityFilter)
        Cached for improved performance.

        Args:
            text: Text to check for sensitive information

        Returns:
            True if sensitive information is found, False otherwise
        """
        if not text:
            return False

        lowered_text = text.lower()

        # Use faster set intersection checking
        for keyword in self.sensitive_keywords:
            if keyword in lowered_text:
                return True

        return False

    @cached(cache=security_analysis_cache)
    def analyze_security_risks(self, text: str) -> str:
        """
        More comprehensive analysis of security risks using OpenAI. (from SecurityFilter)
        Cached for improved performance.

        Args:
            text: Text to analyze for security risks

        Returns:
            Analysis result string, starting with "SAFE" or "UNSAFE"
        """
        if not text:
            return "SAFE"

        # Optimize the prompt for efficiency
        prompt = (
            "Analyze text for potential security risks or confidential information. "
            "Respond ONLY with 'SAFE' or 'UNSAFE: <reason>'. Be very concise."
            f"\n\nText: {text[:1000]}" # Limit to first 1000 chars for efficiency
        )

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4.1-mini-2025-04-14",  # Use smallest/fastest model that can do this task
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50  # Limit response size for faster completion
            )
            analysis = response.choices[0].message.content.strip()  # type: ignore
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing security risks: {e}")
            # Default to flagging as unsafe if analysis fails
            return "UNSAFE: Analysis failed"

    @cached(cache=prompt_injection_cache)
    def check_for_prompt_injection(self, text: str) -> bool:
        """
        Check if the text contains a prompt injection using regex patterns.
        Cached for improved performance.

        Args:
            text: Text to check for prompt injection

        Returns:
            True if prompt injection detected, False otherwise
        """
        if not text:
            return False

        # Use pre-compiled regex for faster matching
        if self.injection_regex.search(text):
            logger.warning(f"Potential prompt injection detected")
            return True

        return False

    def batch_check(self, texts: List[str]) -> List[str]:
        """
        Perform security checks on multiple texts at once.

        Args:
            texts: List of texts to check

        Returns:
            List of reasons why each text is unsafe, or empty strings for safe texts
        """
        results = []

        for text in texts:
            results.append(self.check(text))

        return results

    def check_for_confidential_information(self, text: str) -> bool:
        """
        Check if the text contains confidential information.

        Args:
            text: Text to check

        Returns:
            True if confidential information is detected, False otherwise
        """
        # First check with keywords for efficiency
        if self.contains_sensitive_info(text):
            return True

        # Then do a more comprehensive check with AI
        security_analysis = self.analyze_security_risks(text)
        if not security_analysis.startswith("SAFE"):
            return True

        return False

    def filter_confidential_content(self, text: str) -> str:
        """
        Filter out confidential content from text based on analysis.

        Args:
            text: Text to filter

        Returns:
            Filtered text or original text if safe
        """
        if not text:
            return text

        # Basic keyword check first for efficiency
        if self.contains_sensitive_info(text):
            return "[Some content has been removed due to confidentiality concerns based on keywords]"

        # Advanced security check
        security_analysis = self.analyze_security_risks(text)
        if security_analysis.startswith("UNSAFE"):
            # Provide more specific reason if available
            reason = (
                security_analysis.split(":", 1)[1].strip()
                if ":" in security_analysis
                else "Detected confidential information"
            )
            return f"[Content removed due to security analysis: {reason}]"

        return text

    def check(self, text: str) -> str:
        """
        Check the text for security risks and return a report.
        If safe, return empty string.

        Args:
            text: Text to check

        Returns:
            Empty string if safe, reason why unsafe otherwise
        """
        if not text:
            return ""

        # Check for prompt injection first (faster)
        if self.check_for_prompt_injection(text):
            return "Prompt injection detected"

        # Check for sensitive information (faster)
        if self.contains_sensitive_info(text):
            return "Sensitive information detected"

        # Do a more comprehensive analysis (slower)
        sec_risk_analysis = self.analyze_security_risks(text)
        if not sec_risk_analysis.startswith("SAFE"):
            return sec_risk_analysis

        # If no risks detected, return safe message
        return ""