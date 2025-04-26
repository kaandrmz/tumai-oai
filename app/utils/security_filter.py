"""
Security filter module for detecting and filtering confidential information.
"""

import os
import sys
from typing import List, Dict, Any

# Add the project root to path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import openai_client


class SecurityFilter:
    """
    Helper class to detect and filter out confidential information.
    """

    def __init__(self, custom_keywords: List[str] = None):
        """
        Initialize the security filter.

        Args:
            custom_keywords: Optional list of additional sensitive keywords to check for
        """
        # Default sensitive keywords
        self.sensitive_keywords = [
            "confidential", "secret", "private", "personal", "sensitive",
            "password", "ssn", "social security", "credit card", "phone number",
            "address", "email address", "classified", "internal only",
            "not for distribution", "proprietary", "restricted"
        ]

        # Add custom keywords if provided
        if custom_keywords:
            self.sensitive_keywords.extend(custom_keywords)

    def contains_sensitive_info(self, text: str) -> bool:
        """
        Check if the text contains any sensitive keywords.

        Args:
            text: Text to check for sensitive information

        Returns:
            True if sensitive information is found, False otherwise
        """
        lowered_text = text.lower()
        return any(keyword in lowered_text for keyword in self.sensitive_keywords)

    def analyze_security_risks(self, text: str) -> str:
        """
        More comprehensive analysis of security risks using OpenAI.

        Args:
            text: Text to analyze for security risks

        Returns:
            Analysis result string, starting with "SAFE" or "UNSAFE"
        """
        prompt = f"""
        Analyze the following text for potential security risks or confidential information.
        Respond with:
        - "SAFE" if no confidential information is present
        - "UNSAFE: <reason>" if confidential information is detected

        Text to analyze:
        {text}
        """

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=100
            )
            analysis = response.choices[0].message.content.strip()
            return analysis
        except Exception as e:
            print(f"Error analyzing security risks: {e}")
            # Default to flagging as unsafe if analysis fails
            return "UNSAFE: Analysis failed"

    def filter_content(self, text: str) -> str:
        """
        Filter out confidential content from text.

        Args:
            text: Text to filter

        Returns:
            Filtered text with confidential information removed
        """
        # Basic keyword check
        if self.contains_sensitive_info(text):
            return "[Some content has been removed due to confidentiality concerns]"

        # Advanced security check
        security_analysis = self.analyze_security_risks(text)
        if security_analysis.startswith("UNSAFE"):
            return f"[Content removed: {security_analysis}]"

        return text