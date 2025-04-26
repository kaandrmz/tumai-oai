"""
Student agent implementation for the multiagent system.
"""
from app.config import OPENAI_API_KEY, FASTAPI_URL
import requests
from openai import OpenAI

# def create_student_agent() -> Agent:
#     """
#     Create the student agent focused on learning through questioning.

#     Returns:
#         Configured student agent
#     """
#     student_agent = Agent(
#         role="Student",
#         goal="Understand the subject matter through asking effective questions",
#         backstory="""
#         You are a curious learner who wants to gain comprehensive knowledge on various topics.
#         You ask progressive questions that build upon previous answers to deepen your understanding.
#         You continue questioning until you are satisfied with your understanding of the topic.
#         You are specific in your questions and ask for clarification when needed.
#         You process information systematically and identify gaps in your knowledge.
#         """,
#         verbose=True,
#         allow_delegation=False,
#         llm=llm
#     )

#     return student_agent

class StudentAgent():
    def __init__(self):
        self.role = "Student"
        self.goal = "Understand the subject matter through asking effective questions"
        self.backstory = """
        You are a curious learner who wants to gain comprehensive knowledge on various topics.
        You ask progressive questions that build upon previous answers to deepen your understanding.
        You continue questioning until you are satisfied with your understanding of the topic.
        """

        # Initialize OpenAI client for direct API calls
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        pass

    def get_tasks(self):
        response = requests.get(f"{FASTAPI_URL}/tasks")
        return response.json()

    def reply(self, message: str) -> str:
        pass
