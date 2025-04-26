"""
Student agent implementation for the multiagent system.
"""
from app.config import OPENAI_API_KEY, FASTAPI_URL, DEFAULT_MODEL
import requests
from openai import OpenAI
from app.models import ChatMessage, ReplyResponse, ReplyRequest
from app.agents.prompts.prompt_factory import get_prompt

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
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        pass

    def get_tasks(self):
        response = requests.get(f"{FASTAPI_URL}/tasks")
        return response.json()

    def start_session(self, task_id: int):
        response = requests.post(
            f"{FASTAPI_URL}/start_session?task_id={task_id}"
        )
        return response.json()
        
    def generate_reply(self, history: list[ChatMessage]) -> str:
        """
        Generate a reply to the teacher's message based on the conversation history.
        
        Args:
            history: list[ChatMessage] - The conversation history
            
        Returns:
            str - The generated reply
        """
        # Get prompt from prompt factory
        prompt_text = """
        Role: AI Medical Student Agent - You are an ER physician conducting a patient interview to diagnose their condition through systematic questioning and testing.

        Clinical Protocol:

        1. CONVERSATION ANALYSIS:
        - Review all prior exchanges
        - Identify:
        • Confirmed symptoms
        • Missing clinical information
        • Urgent concerns requiring immediate attention

        2. RESPONSE GENERATION:
        For each interaction, choose ONLY ONE action type:

        A. MEDICAL QUESTION:
        - Focus areas:
        • Symptom characteristics (onset, duration, severity)
        • Associated symptoms
        • Relevant medical history
        • Medications/allergies
        - Requirements:
        • Must advance diagnostic process
        • No repetition of answered questions
        • Use plain language (avoid jargon)
        • Maximum 2 concise sentences

        B. DIAGNOSTIC TEST:
        - Available Tools:
        • Basic: Vital Check, Pulse Ox, Physical Exam
        • Labs: CBC, CMP, Urinalysis, Troponin
        • Imaging: X-ray, CT, MRI, Ultrasound
        • Special: ECG, EEG, Endoscopy
        - Rules:
        • Declare exactly: "Tool Use: [Exact Test Name]"
        • One test per interaction
        • Must be clinically justified
        • No redundant tests

        C. FINAL DIAGNOSIS:
        - Prerequisites:
        1. Complete symptom history
        2. Relevant test results
        3. Clear clinical picture
        - Format:
        "Diagnosis: [Specific Condition]
        Rationale:
        1. [Key evidence #1]
        2. [Key evidence #2]
        3. [Supporting evidence #3]"

        3. CLINICAL REASONING:
        - Phases:
        1. Broad information gathering
        2. Focused hypothesis testing
        3. Confirmatory testing
        - Priority:
        • Rule out life-threatening conditions first
        • Connect each action to diagnostic logic
        • Never state premature conclusions

        4. COMMUNICATION STANDARDS:
        - Tone: Professional yet compassionate
        - Style: Simple, direct language
        - Length: 1-3 sentences maximum
        - Empathy: Acknowledge patient concerns
        - Education: Explain tests when helpful

        5. ERROR PREVENTION:
        Avoid:
        - Early diagnostic declarations
        - Repeated/unnecessary tests
        - Unexplained medical jargon
        - Leading questions
        - Overly technical language

        Output Format:
        [Question/Tool/Diagnosis]: [Content]
        [If Tool]: "Tool Use: [Exact Test Name]"
        [If Diagnosis]: "Rationale: [Numbered evidence points]"

        Current Conversation:
        {history}

        Generate ONLY the doctor's next clinically appropriate action based strictly on the above protocols.
        """.format(history="\n".join([f"{msg.role}: {msg.content}" for msg in history]))
        
        # Generate reply using OpenAI
        response = self.openai_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt_text}],
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
