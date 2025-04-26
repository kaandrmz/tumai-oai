"""
Teacher agent implementation for the multiagent system.
"""
from app.agents.prompts.prompt_factory import get_prompt
from app.config import OPENAI_API_KEY, DEFAULT_MODEL
from openai import OpenAI
from app.agents.case_generator_agent import CaseGeneratorAgent
from app.models import Task

class TeacherAgent():
    def __init__(self):
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.case_generator = CaseGeneratorAgent()

    def start_session(self, task: Task):
        """
        Starts the session:
        - select and adapt a real case from documents
        - create the first response

        Args:
            task: Task (title, description)

        Returns:
            scenario: str
            first_response: str
        """
        # Determine the medical field and difficulty from the task
        # Extract medical field from task title or description (simplistic approach for demo)
        medical_field = task.title if task.title in ["Neurology", "Cardiology", "Pulmonology"] else "General Medicine"
        difficulty_level = "Medium"  # Default difficulty

        # Select and adapt a real case from documents
        case = self.case_generator.select_case(
            medical_field=medical_field,
            difficulty_level=difficulty_level
        )

        # Use the generated scenario for the simulation
        scenario = case["scenario"]

        # Generate the first response (patient's initial statement)
        prompt_response = get_prompt("teacher/gen_response", {
            "scenario": scenario,
            "conversation_history": ""
        })

        gen_response_response = self.openai_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt_response}],
            temperature=0.7
        )

        first_response = gen_response_response.choices[0].message.content

        return scenario, first_response

    def eval_reply(self, reply: str) -> bool:
        """
        Evaluate the reply of the student.
        """
        return 1  # Placeholder implementation