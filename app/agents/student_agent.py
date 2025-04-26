"""
Student agent implementation for the multiagent system.
"""
from app.config import OPENAI_API_KEY, FASTAPI_URL
import requests
from openai import OpenAI

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

    def start_session(self, task_id: int):
        response = requests.post(
            f"{FASTAPI_URL}/start_session?task_id={task_id}"
        )
        return response.json()
