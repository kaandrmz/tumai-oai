"""
Security agent implementation for the multiagent system.
"""
from app.config import OPENAI_API_KEY
from openai import OpenAI
from typing import List, Dict, Any
import re

class SecurityAgent():
    def __init__(self, custom_keywords: List[str] = None):
        self.role = "Security Officer"
        self.goal = "Ensure no confidential information is exposed during the educational session"
        self.backstory = """
        You are a security professional specialized in information security and HIPAA compliance.
        You monitor all exchanges to prevent data breaches and exposure of confidential information.
        You are vigilant and proactive in identifying potential security risks.
        You can intervene in conversations when sensitive information might be exposed.
        You understand the balance between sharing knowledge and protecting confidential data.
        """
        # Default sensitive keywords (from SecurityFilter)
        self.sensitive_keywords = [
            "confidential", "secret", "private", "personal", "sensitive",
            "password", "ssn", "social security", "credit card", "phone number",
            "address", "email address", "classified", "internal only",
            "not for distribution", "proprietary", "restricted",
            # Medical specific PII
            "medical record number", "mrn", "patient id", "patient name",
            "date of birth", "dob", "specific dates", "specific locations",
            "unique identifiers", "rare condition combination"
        ]

        # Add custom keywords if provided (from SecurityFilter)
        if custom_keywords:
            self.sensitive_keywords.extend(custom_keywords)

        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)

    def contains_sensitive_info(self, text: str) -> bool:
        """
        Check if the text contains any sensitive keywords. (from SecurityFilter)

        Args:
            text: Text to check for sensitive information

        Returns:
            True if sensitive information is found, False otherwise
        """
        lowered_text = text.lower()
        return any(keyword in lowered_text for keyword in self.sensitive_keywords)

    def check_for_patient_identifiers(self, text: str) -> bool:
        """
        Check for potential patient identifiers using regex patterns

        Args:
            text: Text to check for patient identifiers

        Returns:
            True if potential patient identifiers found, False otherwise
        """
        # Check for patterns that might indicate patient identifiers
        # MRN pattern (typically 6-10 digits)
        mrn_pattern = r'\b\d{6,10}\b'
        # DOB pattern (various date formats)
        dob_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        # Patient name pattern (looking for "Mr./Mrs./Ms. [Name]" or "Patient [Name]")
        name_pattern = r'\b(Mr\.|Mrs\.|Ms\.|Dr\.|Patient)\s+[A-Z][a-z]+\b'

        if (re.search(mrn_pattern, text) or
            re.search(dob_pattern, text) or
            re.search(name_pattern, text)):
            return True

        return False

    def analyze_security_risks(self, text: str) -> str:
        """
        More comprehensive analysis of security risks using OpenAI.

        Args:
            text: Text to analyze for security risks

        Returns:
            Analysis result string, starting with "SAFE" or "UNSAFE"
        """
        prompt = f"""
        Analyze the following text for potential security risks, HIPAA violations, or confidential medical information.
        Particularly look for:
        1. Patient identifiers (names, dates of birth, addresses, unique IDs)
        2. Specific details that could identify a real person or case
        3. References to real healthcare facilities with specific patient information
        4. Information that violates medical confidentiality standards
        
        Respond with:
        - "SAFE" if no confidential information is present
        - "UNSAFE: <reason>" if confidential information is detected

        Text to analyze:
        {text}
        """

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
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

    def check_for_confidential_information(self, text: str) -> bool:
        """
        Check if the text contains confidential information using keyword matching
        and OpenAI analysis.
        """
        # Basic keyword check
        if self.contains_sensitive_info(text):
            return True

        # Check for patient identifiers
        if self.check_for_patient_identifiers(text):
            return True

        # Advanced security check
        security_analysis = self.analyze_security_risks(text)
        if security_analysis.startswith("UNSAFE"):
            return True

        return False

    def check_for_prompt_injection(self, text: str) -> bool:
        """
        Check if the text contains a prompt injection.
        """
        injection_patterns = [
            "ignore previous instructions",
            "act as",
            "you are now",
            "disregard",
            "instead of",
            "forget",
            # Add more sophisticated patterns
        ]
        lowered_text = text.lower()
        if any(pattern in lowered_text for pattern in injection_patterns):
            print(f"Potential prompt injection detected: {text}")
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
        # Basic keyword check first for efficiency
        if self.contains_sensitive_info(text):
            return self._redact_sensitive_information(text)

        # Check for patient identifiers
        if self.check_for_patient_identifiers(text):
            return self._redact_sensitive_information(text)

        # Advanced security check
        security_analysis = self.analyze_security_risks(text)
        if security_analysis.startswith("UNSAFE"):
            # Provide more specific reason if available
            reason = security_analysis.split(":", 1)[1].strip() if ":" in security_analysis else "Detected confidential information"
            return self._redact_sensitive_information(text, reason)

        return text

    def _redact_sensitive_information(self, text: str, reason: str = None) -> str:
        """
        Redact or generalize sensitive information in text.

        Args:
            text: Text containing sensitive information
            reason: Optional reason for redaction

        Returns:
            Redacted text
        """
        prompt = f"""
        The following text contains sensitive or confidential medical information that needs to be redacted or generalized.
        
        Original text:
        {text}
        
        Please rewrite this text to:
        1. Replace any specific patient identifiers with generic placeholders (e.g., "Patient X", "a middle-aged patient")
        2. Remove or generalize any information that could identify a real person or case
        3. Maintain the educational value and medical accuracy of the content
        4. Keep the same overall message and medical concepts
        
        Your rewritten text should be safe to use in an educational context while preserving the clinical teaching value.
        """

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=1000
            )
            redacted_text = response.choices[0].message.content.strip()

            # Add explanation if reason was provided
            if reason:
                redacted_text = f"[Content modified for confidentiality: {reason}]\n\n{redacted_text}"

            return redacted_text
        except Exception as e:
            print(f"Error redacting sensitive information: {e}")
            # If redaction fails, replace with generic message
            return "[Content removed due to confidentiality concerns]"

    def validate_reply(self, request: Dict[str, Any]) -> bool:
        """
        Validates a request for confidential information or prompt injections.

        Args:
            request: The request object to validate

        Returns:
            True if the request is valid, False otherwise
        """
        # Extract content to check from the request
        if hasattr(request, 'history') and request.history:
            # Check the most recent message in history
            latest_message = request.history[-1]
            content = latest_message.content if hasattr(latest_message, 'content') else ""
        else:
            # If no history or not object with history attribute
            content = str(request)

        # Check for prompt injections
        if self.check_for_prompt_injection(content):
            return False

        # Check for confidential information
        if self.check_for_confidential_information(content):
            return False

        return True