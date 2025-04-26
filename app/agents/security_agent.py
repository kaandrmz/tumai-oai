"""
Security agent implementation for the multiagent system.
"""
from app.config import OPENAI_API_KEY
from openai import OpenAI
from typing import List

class SecurityAgent():
    def __init__(self, custom_keywords: List[str] = None):
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
        self.sensitive_keywords = [
            "confidential", "secret", "private", "personal", "sensitive",
            "password", "ssn", "social security", "credit card", "phone number",
            "address", "email address", "classified", "internal only",
            "not for distribution", "proprietary", "restricted"
        ]

        # Add custom keywords if provided (from SecurityFilter)
        if custom_keywords:
            self.sensitive_keywords.extend(custom_keywords)

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

    def analyze_security_risks(self, text: str) -> str:
        """
        More comprehensive analysis of security risks using OpenAI. (from SecurityFilter)

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

    # Merging SecurityFilter.contains_sensitive_info logic here
    def check_for_confidential_information(self, text: str) -> bool:
        """
        Check if the text contains confidential information using keyword matching
        and OpenAI analysis.
        """
        # Basic keyword check
        if self.contains_sensitive_info(text):
            return True

        # Advanced security check (Optional: Decide if a deeper check is always needed)
        # security_analysis = self.analyze_security_risks(text)
        # if security_analysis.startswith("UNSAFE"):
        #     return True

        return False

    def check_for_prompt_injection(self, text: str) -> bool:
        """
        Check if the text contains a prompt injection.
        (Placeholder - implement actual prompt injection detection logic here)
        """
        # TODO: Implement prompt injection detection logic
        # Example placeholder checks (very basic):
        injection_patterns = [
            "ignore previous instructions",
            "act as",
            "you are now",
            # Add more sophisticated patterns
        ]
        lowered_text = text.lower()
        if any(pattern in lowered_text for pattern in injection_patterns):
            print(f"Potential prompt injection detected: {text}")
            return True
        return False

    # Optional: Include filtering logic if needed by the agent's workflow
    def filter_confidential_content(self, text: str) -> str:
        """
        Filter out confidential content from text based on analysis. (from SecurityFilter)

        Args:
            text: Text to filter

        Returns:
            Filtered text or original text if safe
        """
        # Basic keyword check first for efficiency
        if self.contains_sensitive_info(text):
            return "[Some content has been removed due to confidentiality concerns based on keywords]"

        # Advanced security check
        security_analysis = self.analyze_security_risks(text)
        if security_analysis.startswith("UNSAFE"):
            # Provide more specific reason if available
            reason = security_analysis.split(":", 1)[1].strip() if ":" in security_analysis else "Detected confidential information"
            return f"[Content removed due to security analysis: {reason}]"

        return text
    
    