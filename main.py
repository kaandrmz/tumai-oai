"""
Main entry point for the multiagent RAG educational system.
"""

import os
import argparse
from crewai import Process
import uvicorn
from dotenv import load_dotenv
import logging

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
        result = orchestrator.run_educational_session(topic)

        # Print result
        logger.info("\n=== Educational Session Results ===")
        logger.info(f"Topic: {topic}")
        logger.info(f"Result: {result}")
        logger.info("==================================\n")

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