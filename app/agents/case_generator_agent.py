"""
Modified case generator agent for selecting and adapting real medical cases from retrieved documents.
Uses the optimized document retriever for better performance.
"""
from typing import Dict, List, Optional
from openai import OpenAI
import random
import logging
import os

from app.config import OPENAI_API_KEY, DEFAULT_MODEL
from app.agents.security_agent import SecurityAgent

# Import the optimized document retriever instead of the original
try:
    from app.utils.document_retriever import OptimizedDocumentRetriever
except Exception as e:
    logging.error(f"Error importing OptimizedDocumentRetriever: {e}")

# Set up logging
logger = logging.getLogger(__name__)

class CaseGeneratorAgent:
    """
    Agent for selecting real medical cases from documents and adapting them
    to remove confidential information while preserving educational value.
    Uses pre-computed embeddings for better performance.
    """

    def __init__(self):
        """Initialize the case generator agent with necessary components."""
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.security_agent = SecurityAgent()
        self.document_retriever = None
        self.document_retrieval_available = False

        # Attempt to initialize the optimized document retriever
        try:
            self.document_retriever = OptimizedDocumentRetriever()
            self.document_retrieval_available = True
            logger.info("Optimized document retriever initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize optimized document retriever: {e}")
            logger.warning("Will fall back to generating cases without document retrieval")

        logger.info("CaseGeneratorAgent initialized")

    def retrieve_real_cases(self, medical_field: str, count: int = 3) -> List[Dict[str, str]]:
        """
        Retrieve real cases from the document repository.

        Args:
            medical_field: The medical field to focus on (e.g., "Cardiology")
            count: Number of cases to retrieve

        Returns:
            List of relevant case documents with metadata
        """
        logger.info(f"Retrieving {count} cases for {medical_field}")

        # Check if document retrieval is available
        if not self.document_retrieval_available or self.document_retriever is None:
            logger.warning("Document retrieval not available, returning empty list")
            return []

        # Build queries focused on finding real cases
        queries = [
            f"clinical case {medical_field}",
            f"patient case {medical_field}",
            f"{medical_field} diagnosis case",
            f"{medical_field} patient presentation",
            f"{medical_field} clinical presentation",
            f"{medical_field} symptoms",
            f"{medical_field} case study",
        ]

        # Add more general queries as fallbacks
        if medical_field != "General Medicine":
            queries.extend([
                "medical case",
                "clinical case",
                "patient case",
                "diagnosis case"
            ])

        # Retrieve cases using different queries to increase variety
        cases = []
        for query in queries:
            try:
                logger.info(f"Querying with: {query}")
                retrieved_text = self.document_retriever.retrieve_relevant_context(query)

                if retrieved_text and len(retrieved_text) > 200:  # Ensure we have substantial content
                    # Check if this is actually a case and not general medical information
                    if self._is_clinical_case(retrieved_text):
                        cases.append({
                            "content": retrieved_text,
                            "query": query,
                            "field": medical_field
                        })
                        logger.info(f"Found valid case with query: {query}")
                        if len(cases) >= count:
                            break
            except Exception as e:
                logger.error(f"Error retrieving case with query '{query}': {e}")

        return cases

    def _is_clinical_case(self, text: str) -> bool:
        """
        Check if the retrieved text is actually a clinical case.

        Args:
            text: The retrieved text to check

        Returns:
            True if the text appears to be a clinical case, False otherwise
        """
        # Keywords that suggest this is a clinical case
        case_indicators = [
            "case", "patient", "presented", "diagnosis", "symptoms",
            "history", "examination", "chief complaint", "medical history",
            "physical exam", "treatment", "hospital course"
        ]

        # Count how many indicators are present
        indicator_count = sum(1 for indicator in case_indicators if indicator.lower() in text.lower())

        # If more than 3 indicators are present, it's likely a clinical case
        return indicator_count >= 3

    def generate_fallback_case(self, medical_field: str, difficulty_level: str) -> Dict[str, str]:
        """
        Generate a fallback case when document retrieval fails.

        Args:
            medical_field: The medical field for the case
            difficulty_level: Desired difficulty level for the case

        Returns:
            Dictionary containing the generated scenario and final diagnosis
        """
        logger.info(f"Generating fallback case for {medical_field} at {difficulty_level} difficulty")

        # Create a prompt for generating a realistic medical case
        prompt = f"""
        Create a realistic medical case for a {difficulty_level.lower()} level {medical_field} scenario.
        
        The case should include:
        1. Patient presentation and chief complaint
        2. Relevant medical history
        3. Physical examination findings
        4. Relevant test results if applicable
        5. A clear final diagnosis that would be appropriate for {medical_field}
        
        Format your response as follows:
        
        **Scenario:**
        [Patient presentation and all clinical details]
        
        **Final Diagnosis:**
        [The final diagnosis]
        """

        try:
            # Generate the case using OpenAI
            response = self.openai_client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1500
            )

            case_text = response.choices[0].message.content

            # Parse the case text to separate scenario and diagnosis
            parts = case_text.split("**Final Diagnosis:**")
            if len(parts) > 1:
                scenario = parts[0].strip()
                diagnosis = parts[1].strip()
            else:
                # If the expected format isn't found, try alternative splits
                parts = case_text.split("Final Diagnosis:")
                if len(parts) > 1:
                    scenario = parts[0].strip()
                    diagnosis = parts[1].strip()
                else:
                    # Last resort: keep everything as scenario and add a generic diagnosis
                    scenario = case_text.strip()
                    diagnosis = f"Unspecified {medical_field} condition"

            logger.info("Fallback case generation successful")
            return {
                "scenario": scenario,
                "diagnosis": diagnosis
            }
        except Exception as e:
            logger.error(f"Error generating fallback case: {e}")
            # Return a minimal case if all else fails
            return {
                "scenario": f"A patient presents with symptoms consistent with a {medical_field} condition.",
                "diagnosis": f"Unspecified {medical_field} condition"
            }

    def select_case(self, medical_field: str, difficulty_level: str) -> Dict[str, str]:
        """
        Select a real case from documents and adapt it to remove confidential information.
        If document retrieval fails, fall back to generating a case.

        Args:
            medical_field: The medical field for the case
            difficulty_level: Desired difficulty level for the case

        Returns:
            Dictionary containing the adapted scenario and final diagnosis
        """
        logger.info(f"Selecting case for {medical_field} at {difficulty_level} difficulty")

        # First try to retrieve real cases from the document repository
        raw_cases = []

        if self.document_retrieval_available and self.document_retriever is not None:
            try:
                raw_cases = self.retrieve_real_cases(medical_field)
            except Exception as e:
                logger.error(f"Error retrieving cases: {e}")
                logger.warning("Falling back to generated cases")
                raw_cases = []

        # If no cases found or document retrieval failed, use fallback generation
        if not raw_cases:
            logger.warning("No suitable cases found in the document repository. Using fallback generation.")
            return self.generate_fallback_case(medical_field, difficulty_level)

        # Select a random case from retrieved cases
        selected_case = random.choice(raw_cases)
        logger.info(f"Selected case retrieved with query: {selected_case['query']}")

        # Log a preview of the selected case
        preview = selected_case['content'][:200].replace('\n', ' ')
        logger.info(f"Case preview: {preview}...")

        # Check if the case contains confidential information
        if self.security_agent.check_for_confidential_information(selected_case['content']):
            logger.info("Case contains confidential information, will adapt accordingly")

        # Prepare the prompt for adapting the case
        variables = {
            "medical_field": medical_field,
            "difficulty_level": difficulty_level,
            "raw_case": selected_case['content']
        }

        try:
            # Create adaptation prompt directly since prompt_factory might not work
            # if we're running in an error recovery mode
            prompt = f"""
            You are an expert medical educator adapting a real clinical case for educational purposes.
            
            Medical Field: {medical_field}
            Difficulty Level: {difficulty_level}
            
            Real Case Document:
            {selected_case['content']}
            
            Instructions:
            Take the real case above and adapt it for educational use, following these guidelines:
            
            1. PRESERVE THE CORE MEDICAL CASE
               - Keep the same medical condition, symptoms, progression, and diagnosis
               - Maintain the same level of clinical detail and educational value
               - Preserve the key decision points and diagnostic reasoning
            
            2. REMOVE ALL CONFIDENTIAL INFORMATION
               - Change all patient identifiers (name, age, exact dates, locations)
               - Remove specific identifiers (MRN, exact dates of service, provider names)
               - Modify any rare or unique characteristics that could identify the patient
               - Generalize demographic details while maintaining clinical relevance
            
            3. ADAPT THE DIFFICULTY
               - Adjust the presentation to match the {difficulty_level} level
            
            4. FORMAT THE OUTPUT
               - Structure the case as a clear patient scenario
               - Include presenting complaint, history, physical findings, and relevant test results
               - Clearly state the final diagnosis
               - Include a brief rationale for teaching purposes
            
            Output Format:
            
            **Scenario:**
            [Adapted patient presentation]
            [Relevant history]
            [Physical examination findings]
            [Test results if applicable]
            
            **Final Diagnosis:**
            [Diagnosis]
            
            ENSURE ALL CONFIDENTIAL INFORMATION IS REMOVED while preserving the educational value of the case.
            """

            # Process the case using the prompt
            logger.info("Adapting case to remove confidential information")
            case_response = self.openai_client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower temperature for more faithful adaptation
                max_tokens=1500
            )

            case_text = case_response.choices[0].message.content

            # Have security agent check the adapted case
            if self.security_agent.check_for_confidential_information(case_text):
                logger.warning("Adapted case still contains confidential information, applying stronger anonymization")
                # If any potential confidential information is found, anonymize further
                additional_instruction = (
                    "IMPORTANT: The case still contains confidential information. "
                    "Please anonymize more aggressively, changing all specific details "
                    "while preserving the medical learning points."
                )

                prompt += f"\n\n{additional_instruction}"

                case_response = self.openai_client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1500
                )
                case_text = case_response.choices[0].message.content

            # Parse the case text to separate scenario and diagnosis
            parts = case_text.split("**Final Diagnosis:**")
            if len(parts) > 1:
                scenario = parts[0].strip()
                diagnosis = parts[1].strip()
            else:
                # If the expected format isn't found, try alternative splits
                parts = case_text.split("Final Diagnosis:")
                if len(parts) > 1:
                    scenario = parts[0].strip()
                    diagnosis = parts[1].strip()
                else:
                    # Last resort: keep everything as scenario and add a generic diagnosis
                    scenario = case_text.strip()
                    diagnosis = f"Unspecified {medical_field} condition"

            logger.info("Case adaptation successful")
            return {
                "scenario": scenario,
                "diagnosis": diagnosis
            }

        except Exception as e:
            logger.error(f"Error adapting case: {e}")
            # Fall back to generating a case if adaptation fails
            return self.generate_fallback_case(medical_field, difficulty_level)