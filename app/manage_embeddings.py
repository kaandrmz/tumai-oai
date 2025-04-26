#!/usr/bin/env python
"""
CLI tool for managing document embeddings for the medical case generator system.
This tool helps pre-compute, update, and manage vector embeddings for more efficient retrieval.
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Add the project root to path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.document_retriever import OptimizedDocumentRetriever
from app.config import DOCUMENTS_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('embeddings_management.log')
    ]
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Medical Document Embeddings Management Tool')

    # Main commands
    parser.add_argument('--regenerate', action='store_true',
                        help='Force regeneration of embeddings regardless of document changes')
    parser.add_argument('--check', action='store_true',
                        help='Check if documents have changed and embeddings need updating')
    parser.add_argument('--info', action='store_true',
                        help='Display information about current embeddings')
    parser.add_argument('--test-query', type=str,
                        help='Test a search query against the embeddings')

    # Configuration options
    parser.add_argument('--docs-path', type=str, default=DOCUMENTS_PATH,
                        help='Path to documents directory')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')

    args = parser.parse_args()

    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Initialize the retriever
    try:
        logger.info(f"Initializing OptimizedDocumentRetriever with docs path: {args.docs_path}")
        retriever = OptimizedDocumentRetriever(docs_path=args.docs_path)

        # Process commands
        if args.regenerate:
            logger.info("Regenerating embeddings...")
            start_time = datetime.now()
            retriever.regenerate_embeddings()
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Embeddings regenerated successfully in {duration:.2f} seconds")

        elif args.check:
            if not os.path.exists(retriever.embeddings_file):
                logger.info("No existing embeddings found. Generation required.")
            elif retriever._has_docs_changed():
                logger.info("Documents have changed. Embeddings need to be updated.")
            else:
                logger.info("Documents unchanged. Current embeddings are up-to-date.")

        elif args.info:
            if os.path.exists(retriever.embeddings_file):
                file_size = os.path.getsize(retriever.embeddings_file) / (1024 * 1024)  # Size in MB
                modified_date = datetime.fromtimestamp(os.path.getmtime(retriever.embeddings_file))

                print("\n=== Embeddings Information ===")
                print(f"Location: {retriever.embeddings_file}")
                print(f"Size: {file_size:.2f} MB")
                print(f"Last updated: {modified_date}")

                if os.path.exists(retriever.metadata_file):
                    import pandas as pd
                    try:
                        metadata = pd.read_csv(retriever.metadata_file)
                        print(f"Documents indexed: {len(metadata)}")
                        print("\nDocument Details:")
                        for idx, row in metadata.iterrows():
                            print(f"  - {os.path.basename(row['path'])}")
                    except Exception as e:
                        print(f"Error reading metadata: {e}")
                else:
                    print("No metadata file found.")
            else:
                print("No embeddings file found.")

        elif args.test_query:
            if not retriever.retriever:
                logger.error("Retriever not properly initialized.")
                return

            print(f"\nTesting query: '{args.test_query}'")
            print("\n--- Retrieved Contexts ---")
            contexts = retriever.retrieve_relevant_context(args.test_query)
            print(contexts)
            print("\n--- End of Retrieved Contexts ---")

        else:
            # Default behavior if no specific command
            parser.print_help()

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()