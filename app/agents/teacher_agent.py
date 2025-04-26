"""
Teacher agent implementation for the multiagent system.
"""

import os
import sys
from crewai import Agent
from crewai.tools import tool

# Add the project root to path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import llm
from utils.document_retriever import DocumentRetriever


def create_teacher_agent(document_retriever: DocumentRetriever) -> Agent:
    """
    Create the teacher agent with RAG capabilities.

    Args:
        document_retriever: Initialized DocumentRetriever instance

    Returns:
        Configured teacher agent
    """
    # Create a tool using the decorator pattern
    @tool("RetrieveContext")
    def retrieve_relevant_context(query: str) -> str:
        """
        Retrieve relevant information from the knowledge base about a specific topic or question.
        This tool searches through the available documents to find information related to the query.

        Args:
            query: The topic or question to search for information about

        Returns:
            Information related to the query from the knowledge base
        """
        return document_retriever.retrieve_relevant_context(query)

    teacher_agent = Agent(
        role="Teacher",
        goal="Share knowledge accurately from the provided documents while respecting confidentiality",
        backstory="""
        You are an experienced educator with deep domain knowledge in various subjects.
        You have access to a library of documents that you use to provide accurate information.
        You care about student understanding and adapt your teaching style to the student's needs.
        You respect confidentiality and are careful not to share sensitive information.
        """,
        verbose=True,
        allow_delegation=True,
        llm=llm,
        tools=[retrieve_relevant_context]
    )

    return teacher_agent