from app.agents.teacher_agent import TeacherAgent
from app.models import Task
import logging

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_teacher_agent():
    """
    Test the TeacherAgent by generating a medical case scenario and initial patient response.
    """
    logger.info("Initializing TeacherAgent...")
    teacher_agent = TeacherAgent()

    # Create different test tasks for different medical specialties
    test_cases = [
        Task(id=1, title="Cardiology", description="Diagnose a cardiac condition"),
        Task(id=2, title="Neurology", description="Diagnose a neurological condition"),
        Task(id=3, title="General Medicine", description="Diagnose a general medical condition")
    ]

    # Test each specialty
    for task in test_cases:
        logger.info(f"Testing medical specialty: {task.title}")

        try:
            # Start session for this specialty
            scenario, first_response = teacher_agent.start_session(task)

            # Print the results
            print("\n" + "=" * 50)
            print(f"MEDICAL CASE: {task.title}")
            print("=" * 50)
            print("\nScenario:")
            print("-" * 40)
            print(scenario)
            print("\nPatient's Initial Statement:")
            print("-" * 40)
            print(first_response)
            print("\n")

            logger.info(f"Successfully generated case for {task.title}")

        except Exception as e:
            logger.error(f"Error testing {task.title}: {e}")
            print(f"\nError with {task.title}: {e}\n")


if __name__ == "__main__":
    test_teacher_agent()