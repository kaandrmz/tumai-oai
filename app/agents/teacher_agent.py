"""
Teacher agent implementation for the multiagent system.
"""
from app.agents.prompts.prompt_factory import get_prompt
from app.config import OPENAI_API_KEY, DEFAULT_MODEL
from openai import OpenAI
from app.agents.case_generator_agent import CaseGeneratorAgent
from app.models import Task
import logging
import re

# Set up logging
logger = logging.getLogger(__name__)

class TeacherAgent():
    def __init__(self):
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.case_generator = CaseGeneratorAgent()
        logger.info("TeacherAgent initialized")

    def start_session(self, task: Task):
        """
        Starts the session:
        - select and adapt a real case from documents
        - create the first response

        Args:
            task: Task (title, description)

        Returns:
            scenario: str
            diagnosis: str
            first_response: str
        """
        # Determine the medical field and difficulty from the task
        # Extract medical field from task title or description (simplistic approach for demo)
        medical_field = task.title if task.title in ["Neurology", "Cardiology", "Pulmonology", "General Medicine"] else "General Medicine"
        difficulty_level = "Medium"  # Default difficulty

        logger.info(f"Starting session with medical field: {medical_field}, difficulty: {difficulty_level}")

        # Select and adapt a real case from documents
        case = self.case_generator.select_case(
            medical_field=medical_field,
            difficulty_level=difficulty_level
        )

        # Use the generated scenario for the simulation
        scenario = case["scenario"]
        diagnosis = case["diagnosis"]

        logger.info(f"Case selected with diagnosis: {diagnosis}")

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
        logger.info("Generated first patient response")

        return scenario, diagnosis, first_response

    def eval_reply(self, reply: str, scenario: str, diagnosis: str, conversation_history: list) -> tuple:
        """
        Evaluate the reply of the student based on diagnostic accuracy, clinical reasoning,
        and appropriate questioning.

        Args:
            reply: The student's reply to evaluate
            scenario: The medical case scenario
            diagnosis: The correct diagnosis for the case
            conversation_history: Previous conversation exchanges

        Returns:
            tuple: (score, is_end, feedback)
                - score: Float from 0.0 to 1.0 representing evaluation score
                - is_end: Boolean indicating whether the session should end
                - feedback: Specific feedback about the reply
        """
        logger.info("Evaluating student reply")

        # Create a prompt for the evaluation model
        prompt = f"""
        **Role**: You are an expert medical educator evaluating a student doctor's diagnostic performance in a simulated patient case.

        **Task**: Analyze the student's response and provide structured feedback with scores. Use these exact response fields:

        1. **Diagnostic Reasoning Score** (0-10):
        - Evaluate logical progression from symptoms to differential diagnoses.
        - 10: Clear hypothesis-driven approach, considers multiple possibilities.
        - 5: Some logical gaps or limited differentials.
        - 0: Illogical or absent reasoning.

        2. **Information Gathering Score** (0-10):
        - Assess relevance and completeness of questions/history-taking.
        - 10: Systematic, covers vital signs, history, and red flags.
        - 5: Misses key elements or asks redundant questions.
        - 0: No meaningful data collection.

        3. **Diagnosis Accuracy Score** (0-10):
        - Rate correctness of the proposed diagnosis.
        - 10: Matches ground truth diagnosis with confidence.
        - 5: Partially correct (e.g., correct organ system but wrong condition).
        - 0: Incorrect diagnosis.

        4. **Communication Score** (0-10):
        - Judge clarity, professionalism, and patient-centeredness.
        - 10: Clear, empathetic, and structured communication.
        - 5: Understandable but lacks polish or empathy.
        - 0: Confusing or unprofessional.

        5. **End Conversation** (Yes/No):
        - "Yes" if: 
            - Diagnosis is correct AND student demonstrated mastery, OR
            - Critical errors require restarting the case.
        - "No" if: More teaching opportunities exist.

        6. **Reason** (1-2 sentences):
        - Justify the "End Conversation" decision.
        - Example: "Student correctly diagnosed asthma but needs practice with differentials."

        7. **Feedback** (3-4 bullet points):
        - Specific, actionable suggestions.
        - Example:
            - "Ask about symptom triggers next time."
            - "Consider COPD in your differentials."
            - "Improve eye contact during patient explanations."

        **Case Details**:
        {scenario[-1000:]} # reverse index bc diagnosis is at the end

        **Correct Diagnosis**:
        {diagnosis}

        **Conversation History**:
        {self._format_conversation_history(conversation_history)[:1000]}

        **Student's Response**:
        {reply}
        """

        try:
            # Generate the evaluation using OpenAI
            evaluation_response = self.openai_client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )

            evaluation_text = evaluation_response.choices[0].message.content
            logger.info("Received evaluation response")

            # Parse the evaluation results
            dr_score = self._extract_score(evaluation_text, "Diagnostic Reasoning Score")
            ig_score = self._extract_score(evaluation_text, "Information Gathering Score")
            da_score = self._extract_score(evaluation_text, "Diagnosis Accuracy Score")
            comm_score = self._extract_score(evaluation_text, "Communication Score")

            # Calculate overall score (0.0 to 1.0 scale)
            overall_score = (dr_score + ig_score + da_score + comm_score) / 40.0

            # Determine if conversation should end
            end_conversation = "yes" in self._extract_field(evaluation_text, "End Conversation").lower()

            # Extract feedback
            feedback = self._extract_field(evaluation_text, "Feedback")

            logger.info(f"Evaluation completed - Score: {overall_score:.2f}, End: {end_conversation}")
            return overall_score, end_conversation, feedback

        except Exception as e:
            logger.error(f"Error evaluating reply: {e}")
            # Default to continuing conversation with moderate score
            return 0.5, False, "Error evaluating response, please continue."

    # Corrected function for teacher_agent.py
    def _format_conversation_history(self, history: list) -> str:
        """
        Format the conversation history for easier evaluation. Handles history
        items that are dictionaries.

        Args:
            history: List of chat message dictionaries (e.g., {'role': 'user', 'content': '...'})

        Returns:
            Formatted conversation history string
        """
        formatted = []
        for message in history:
            try:
                # Use dictionary key access
                role_key = message.get('role', 'unknown')  # Use .get for safety
                content_key = message.get('content', '')  # Use .get for safety

                role = "Student" if role_key == "user" else "Patient"  # Assuming 'assistant' maps to 'Patient'
                formatted.append(f"{role}: {content_key}")
            except AttributeError:
                # Handle cases where an item might not be a dictionary as expected
                logger.error(f"Unexpected item format in conversation history: {message}")
                formatted.append(f"Unknown: [Error processing message]")

        return "\n".join(formatted)

    def _extract_score(self, text: str, field: str) -> float:
        """
        Extract a numerical score from the evaluation text.

        Args:
            text: The evaluation text
            field: The field name to look for

        Returns:
            Score as a float (0-10)
        """
        try:
            # Find the line with the field
            pattern = f"{field}: (\\d+(?:\\.\\d+)?)"
            match = re.search(pattern, text)
            if match:
                return float(match.group(1))
            logger.warning(f"Could not extract {field}, defaulting to 5.0")
            return 5.0  # Default middle score if not found
        except Exception as e:
            logger.error(f"Error extracting {field}: {e}")
            return 5.0  # Default middle score on error

    def _extract_field(self, text: str, field: str) -> str:
        """
        Extract a text field from the evaluation text.

        Args:
            text: The evaluation text
            field: The field name to look for

        Returns:
            The extracted text
        """
        try:
            pattern = f"{field}:\\s*(.+?)(?:\\n\\n|\\n[A-Za-z]+:|$)"
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()
            logger.warning(f"Could not extract text field {field}")
            return ""
        except Exception as e:
            logger.error(f"Error extracting text field {field}: {e}")
            return ""