"""
Security agent implementation for the multiagent system.
"""

import os
import sys
from crewai import Agent
from crewai.tools import tool

# Add the project root to path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import llm
from utils.security_filter import SecurityFilter


def create_security_agent(security_filter: SecurityFilter) -> Agent:
    """
    Create the security agent to prevent confidential information exposure.

    Args:
        security_filter: Initialized SecurityFilter instance

    Returns:
        Configured security agent
    """
    # Create tools using the decorator pattern
    @tool("FilterContent")
    def filter_content(text: str) -> str:
        """
        Filter out any confidential or sensitive information from the provided text.
        This tool examines text for sensitive content and removes or redacts it as necessary.

        Args:
            text: The text to filter for confidential information

        Returns:
            Filtered text with confidential information removed
        """
        return security_filter.filter_content(text)

    @tool("AnalyzeSecurityRisks")
    def analyze_security_risks(text: str) -> str:
        """
        Analyze text for potential security risks and confidential information.
        This tool provides an assessment of whether text contains sensitive data.

        Args:
            text: The text to analyze for security risks

        Returns:
            Analysis of security risks in the provided text
        """
        return security_filter.analyze_security_risks(text)

    security_agent = Agent(
        role="Security Officer",
        goal="Ensure no confidential information is exposed during the educational session",
        backstory="""
        You are a security professional specialized in information security.
        You monitor all exchanges to prevent data breaches and exposure of confidential information.
        You are vigilant and proactive in identifying potential security risks.
        You can intervene in conversations when sensitive information might be exposed.
        You understand the balance between sharing knowledge and protecting confidential data.
        """,
        verbose=True,
        allow_delegation=False,
        llm=llm,
        tools=[filter_content, analyze_security_risks]
    )

    return security_agent