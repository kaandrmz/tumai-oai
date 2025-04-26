"""
Teacher agent implementation for the multiagent system.
"""
from app.agents.prompts.prompt_factory import get_prompt
from app.config import OPENAI_API_KEY, DEFAULT_MODEL
from openai import OpenAI

from app.models import Task

class TeacherAgent():
    def __init__(self):
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        pass

    def start_session(self, task: Task):
        """
        Starts the session:
        - generate the scenario (e.g. specific patient diagnosis and symptoms)
        - create the first response
        
        Args:
            task: Task (title, description)

        Returns:
            scenario: str
            first_response: str
        """

        # generating the scenario
        prompt_scenario = get_prompt("teacher/gen_scenario", {
            "patient_context": "A 30-year-old woman with a history of migraines",
            "medical_field": "Neurology",
            "difficulty_level": "Medium"
        })
        gen_scenario_response = self.openai_client.responses.create(
            model=DEFAULT_MODEL,
            input=prompt_scenario
        )

        # generating the first response
        prompt_response = get_prompt("teacher/gen_response", {
            "scenario": gen_scenario_response.output_text,
            "conversation_history": ""
        })
        gen_response_response = self.openai_client.responses.create(
            model=DEFAULT_MODEL,
            input=prompt_response
        )

        return gen_scenario_response.output_text, gen_response_response.output_text

    def eval_reply(self, reply: str) -> bool:
        """
        Evaluate the reply of the student.
        """
        return 1
