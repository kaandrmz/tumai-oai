"""
Main entry point for the multiagent RAG educational system.
"""

import os
import argparse
from crewai import Process
import uvicorn
from dotenv import load_dotenv
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import after environment variables are loaded
from orchestration.crew_setup import CrewOrchestrator
from api.endpoints import app


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="CrewAI Educational System")

    parser.add_argument(
        "--mode",
        type=str,
        choices=["api", "cli"],
        default="api",
        help="Run in API mode or CLI mode"
    )

    parser.add_argument(
        "--topic",
        type=str,
        default="general knowledge",
        help="Topic for the educational session (CLI mode only)"
    )

    parser.add_argument(
        "--docs",
        type=str,
        default=None,
        help="Path to the documents directory"
    )

    parser.add_argument(
        "--process",
        type=str,
        choices=["sequential", "hierarchical"],
        default="sequential",
        help="CrewAI process type"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for the API server (API mode only)"
    )

    return parser.parse_args()


def print_conversation(result):
    """
    Print the conversation between the teacher and student in a readable format.

    Args:
        result: Result from the educational session
    """
    print("\n" + "="*80)
    print("EDUCATIONAL CONVERSATION")
    print("="*80)

    try:
        # Check if result is a string (direct output from the latest CrewAI version)
        if isinstance(result, str):
            # Extract the conversation parts if they exist
            if "STUDENT:" in result and "TEACHER:" in result:
                # Split by student and teacher markers
                parts = []

                # Process student parts
                student_parts = result.split("STUDENT:")
                for part in student_parts[1:]:  # Skip the first empty part
                    end_idx = part.find("TEACHER:")
                    if end_idx != -1:
                        student_text = part[:end_idx].strip()
                        parts.append(("STUDENT", student_text))
                    else:
                        parts.append(("STUDENT", part.strip()))

                # Process teacher parts
                teacher_parts = result.split("TEACHER:")
                for part in teacher_parts[1:]:  # Skip the first empty part
                    end_idx = part.find("STUDENT:")
                    if end_idx != -1:
                        teacher_text = part[:end_idx].strip()
                        parts.append(("TEACHER", teacher_text))
                    else:
                        parts.append(("TEACHER", part.strip()))

                # Sort by position in original text
                parts.sort(key=lambda x: result.find(f"{x[0]}:{x[1]}"))

                # Print the conversation in order
                for role, text in parts:
                    print(f"\n[{role}]:")
                    print(f"{role}: {text}")
                    print("-"*80)
            else:
                # If no structured markers, print the raw output
                print("\nConversation Result:")
                print(result)
        else:
            # For CrewOutput objects or dictionaries
            print("\nConversation Result (Raw Format):")
            # Try to access different attributes that might contain the text
            try:
                if hasattr(result, 'raw'):
                    print(result.raw)
                elif hasattr(result, 'result'):
                    print(result.result)
                elif hasattr(result, '__dict__'):
                    print(json.dumps(result.__dict__, indent=2))
                else:
                    print(str(result))
            except:
                print(str(result))

    except Exception as e:
        logger.error(f"Error printing conversation: {e}")
        print("\nCould not format conversation cleanly. Raw result:")
        print(str(result))

    print("="*80 + "\n")


def read_output_files():
    """
    Read and display the content of output files created by the agents.
    """
    print("\n" + "="*80)
    print("EDUCATIONAL SESSION OUTPUTS FROM FILES")
    print("="*80)

    output_files = [
        "student_learning.txt",
        "teacher_response.txt",
        "teacher_preparation.txt"
    ]

    for filename in output_files:
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    content = f.read()
                print(f"\n[{filename}]:")
                print(content)
                print("-"*80)
        except Exception as e:
            logger.error(f"Error reading file {filename}: {e}")

    print("="*80 + "\n")


def run_cli_mode(topic, docs_path, process_type_str):
    """
    Run the system in CLI mode.

    Args:
        topic: Topic for the educational session
        docs_path: Path to the documents directory
        process_type_str: Process type string ("sequential" or "hierarchical")
    """
    logger.info(f"Running in CLI mode with topic: {topic}")

    # Set process type
    process_type = Process.sequential
    if process_type_str == "hierarchical":
        process_type = Process.hierarchical

    try:
        # Create orchestrator
        orchestrator = CrewOrchestrator(docs_path)

        # Set up crew
        orchestrator.setup_crew(topic, process_type)

        # Run educational session
        print(f"\nStarting educational session on topic: '{topic}'")
        print("This may take a few minutes...\n")

        result = orchestrator.run_educational_session(topic)

        # Print the conversation in a readable format
        print_conversation(result)

        # Also read from output files which might contain more information
        read_output_files()

        # Log completion
        logger.info(f"Educational session completed successfully")

        return result
    except Exception as e:
        logger.error(f"Error running CLI mode: {e}")
        raise


def run_api_mode(port):
    """
    Run the system in API mode.

    Args:
        port: Port to run the API server on
    """
    logger.info(f"Starting API server on port {port}")
    logger.info(f"API documentation available at http://localhost:{port}/docs")

    try:
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        logger.error(f"Error running API mode: {e}")
        raise


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()

    # Determine mode
    if args.mode == "cli":
        run_cli_mode(args.topic, args.docs, args.process)
    else:  # API mode
        run_api_mode(args.port)


if __name__ == "__main__":
    main()