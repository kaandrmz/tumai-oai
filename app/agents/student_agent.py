"""
Student agent implementation for the multiagent system.
"""
from app.config import OPENAI_API_KEY, FASTAPI_URL, DEFAULT_MODEL
import requests
from openai import OpenAI
from app.models import ChatMessage, ReplyResponse, ReplyRequest
from app.agents.prompts.prompt_factory import get_prompt

class StudentAgent():
    def __init__(self, teacher_url: str = FASTAPI_URL):
        self.role = "Student"
        self.goal = "Understand the subject matter through asking effective questions"
        self.backstory = """
        You are a curious learner who wants to gain comprehensive knowledge on various topics.
        You ask progressive questions that build upon previous answers to deepen your understanding.
        You continue questioning until you are satisfied with your understanding of the topic.
        """

        # Initialize OpenAI client for direct API calls
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        pass

    def get_tasks(self):
        response = requests.get(f"{FASTAPI_URL}/tasks")
        return response.json()

    def start_session(self, task_id: int, session_id: int | None = None):
        """Starts a new session with the teacher API, optionally using a provided session_id."""
        params = {"task_id": task_id}
        if session_id is not None:
            params["session_id"] = session_id
            
        endpoint = f"{FASTAPI_URL}/start_session"
        response = requests.post(endpoint, params=params)
        # Consider adding error handling for the request itself
        return response.json()
        
    def generate_reply(self, history: list[ChatMessage]) -> str:
        """
        Generate a reply to the teacher's message based on the conversation history.
        
        Args:
            history: list[ChatMessage] - The conversation history
            
        Returns:
            str - The generated reply
        """
        # Format history for prompt template
        formatted_history = "\n".join([f"{msg.role}: {msg.content}" for msg in history])
        
        # Get prompt from prompt factory
        prompt_text = get_prompt("student/gen_reply", {
            "history": formatted_history
        })
        
        # Generate reply using OpenAI
        response = self.openai_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    def generate_diagnosis(self, history: list[ChatMessage]) -> str:
        """
        Generate a final diagnosis based on the conversation history.
        
        Args:
            history: list[ChatMessage] - The conversation history
            
        Returns:
            str - The generated diagnosis
        """
        # Format history for prompt
        formatted_history = "\n".join([f"{msg.role}: {msg.content}" for msg in history])
        
        # Create diagnosis prompt
        diagnosis_prompt = f"""
You are an AI agent acting as a doctor. You've gathered information through the following conversation:

{formatted_history}

Based on this conversation, provide a final diagnosis for the patient in a compassionate manner.
Make your response sound like a doctor speaking directly to the patient.
"""
        
        # Generate diagnosis using OpenAI
        response = self.openai_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": diagnosis_prompt}],
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    def send_reply(self, session_id: int, history: list[ChatMessage]) -> dict:
        """
        Send a reply to the teacher and get the evaluation.
        
        Args:
            session_id: int - The session ID
            history: list[ChatMessage] - The conversation history
            
        Returns:
            dict - The teacher's evaluation and response
        """
        # Generate the student's reply
        reply_content = self.generate_reply(history)
        
        # Create the student's message
        student_message = ChatMessage(role="student", content=reply_content)
        
        # Add the student's reply to the history
        updated_history = history.copy()
        updated_history.append(student_message)
        
        # Convert history to the format expected by the API - pure list of dictionaries
        history_dicts = []
        for msg in updated_history:
            if hasattr(msg, 'dict'):
                history_dicts.append(msg.dict())
            else:
                history_dicts.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Send the reply to the teacher for evaluation
        # session_id as query parameter, history list as the body (not wrapped in an object)
        try:
            response = requests.post(
                f"{FASTAPI_URL}/eval_reply?session_id={session_id}",
                json=history_dicts  # Send ONLY the history list
            )
            
            # Parse and return the response
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error in API response: {response.status_code} - {response.text}")
                # If request fails, return the updated history so the conversation can continue
                return {
                    "session_id": session_id,
                    "history": updated_history,
                    "error": f"API error: {response.status_code} - {response.text}"
                }
        except Exception as e:
            print(f"Exception in send_reply: {e}")
            return {
                "session_id": session_id,
                "history": updated_history,
                "error": f"Exception: {str(e)}"
            }
