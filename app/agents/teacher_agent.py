"""
Teacher agent implementation for the multiagent system.
Optimized for better performance.
"""
from app.agents.prompts.prompt_factory import get_prompt
from app.config import OPENAI_API_KEY, DEFAULT_MODEL
from openai import OpenAI
from app.agents.case_generator_agent import CaseGeneratorAgent
from app.models import Task
import logging
import re
import functools
from cachetools import TTLCache, cached

# Set up logging
logger = logging.getLogger(__name__)

# Create a TTL cache for OpenAI completions
openai_completion_cache = TTLCache(maxsize=100, ttl=3600)  # Cache for 1 hour

class TeacherAgent():
    def __init__(self):
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self._case_cache = {}  # Cache for cases by medical field and difficulty
        logger.info("TeacherAgent initialized")

    def _get_cached_completion(self, model, messages, temperature=0.7, max_tokens=None):
        """Get a cached OpenAI completion or generate a new one"""
        # Create a cache key from the request parameters
        cache_key = f"{model}_{str(messages)}_{temperature}_{max_tokens}"

        # Check if we have a cached response
        if cache_key in openai_completion_cache:
            logger.info("Using cached OpenAI completion")
            return openai_completion_cache[cache_key]

        # Generate a new completion
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        response = self.openai_client.chat.completions.create(**kwargs)

        # Cache the response
        openai_completion_cache[cache_key] = response

        return response

    def get_case_from_cache(self, medical_field, difficulty_level):
        """Get a case from the cache or generate a new one"""
        cache_key = f"{medical_field}_{difficulty_level}"

        if cache_key in self._case_cache and self._case_cache[cache_key]:
            logger.info(f"Using cached case for {medical_field} at {difficulty_level} difficulty")
            return self._case_cache[cache_key].pop(0)

        return None

    def add_case_to_cache(self, medical_field, difficulty_level, case, max_cache_size=5):
        """Add a case to the cache"""
        cache_key = f"{medical_field}_{difficulty_level}"

        if cache_key not in self._case_cache:
            self._case_cache[cache_key] = []

        # Only cache if we're under the max size
        if len(self._case_cache[cache_key]) < max_cache_size:
            self._case_cache[cache_key].append(case)
            logger.info(f"Added case to cache for {medical_field} at {difficulty_level} difficulty")

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

        # Try to get a case from the cache
        case = self.get_case_from_cache(medical_field, difficulty_level)

        if not case:
            # If not in cache, generate a new case
            case_generator = CaseGeneratorAgent()
            case = case_generator.select_case(
                medical_field=medical_field,
                difficulty_level=difficulty_level
            )

            # Pre-generate a few more cases for this field and difficulty for future use
            for _ in range(2):  # Generate 2 additional cases
                try:
                    additional_case = case_generator.select_case(
                        medical_field=medical_field,
                        difficulty_level=difficulty_level
                    )
                    self.add_case_to_cache(medical_field, difficulty_level, additional_case)
                except Exception as e:
                    logger.warning(f"Failed to generate additional case: {e}")

        # Use the generated scenario for the simulation
        scenario = case["scenario"]
        diagnosis = case["diagnosis"]

        logger.info(f"Case selected with diagnosis: {diagnosis}")

        # Generate the first response (patient's initial statement)
        prompt_response = get_prompt("teacher/gen_response", {
            "scenario": scenario,
            "conversation_history": ""
        })

        gen_response_response = self._get_cached_completion(
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
        # Optimize by reducing the prompt size and focusing on key elements
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
        {scenario[:1000]}

        **Correct Diagnosis**:
        {diagnosis}

        **Conversation History**:
        {self._format_conversation_history(conversation_history)[:1000]}

        **Student's Response**:
        {reply}
        """

        try:
            # Generate the evaluation using OpenAI with caching
            evaluation_response = self._get_cached_completion(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500  # Reduce token count for faster response
            )

            evaluation_text = evaluation_response.choices[0].message.content
            logger.info("Received evaluation response")

            # Parse the evaluation results - use more direct regex patterns
            # Use a single regex pattern with named groups for faster extraction
            pattern = r"Diagnostic Reasoning Score: (\d+(?:\.\d+)?).+?Information Gathering Score: (\d+(?:\.\d+)?).+?Diagnosis Accuracy Score: (\d+(?:\.\d+)?).+?Communication Score: (\d+(?:\.\d+)?)"
            match = re.search(pattern, evaluation_text, re.DOTALL)

            if match:
                dr_score = float(match.group(1))
                ig_score = float(match.group(2))
                da_score = float(match.group(3))
                comm_score = float(match.group(4))
            else:
                # Fallback to individual extraction if the combined pattern fails
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
            except (AttributeError, TypeError):
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