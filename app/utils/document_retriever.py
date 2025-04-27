"""
Enhanced document retrieval module using pre-computed embeddings.
Handles document loading, processing, and retrieval with optimized performance.
Uses FAISS save_local/load_local for persistence.
"""

import os
import sys
import logging
import pickle  # Keep for potential other uses, but not for FAISS object
import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Tuple
from pathlib import Path
import time # Added for mtime comparison

from langchain_community.document_loaders import TextLoader, PyPDFLoader, DirectoryLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

# Add the project root to path to enable imports
try:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.append(project_root)
    from app.config import OPENAI_API_KEY, DOCUMENTS_PATH
except ImportError as e:
    print(f"Error importing project modules: {e}")
    print("Please ensure the script is run from the correct location or adjust sys.path.append.")
    # Provide a default or exit
    DOCUMENTS_PATH = './documents' # Example fallback
    print(f"Using fallback documents path: {DOCUMENTS_PATH}")
    # Decide if OPENAI_API_KEY needs a fallback or if exit is required
    if 'OPENAI_API_KEY' not in locals():
       OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") # Try env var as fallback
       if not OPENAI_API_KEY:
           print("Error: OPENAI_API_KEY not found in config or environment variables.")
           sys.exit(1)

# Configure logging
# Check if logging is already configured (e.g., by the management script)
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OptimizedDocumentRetriever:
    """
    Enhanced document retriever that uses pre-computed embeddings stored using
    FAISS save_local/load_local methods.
    Avoids re-computing embeddings on each initialization for improved performance.
    """

    def __init__(self, docs_path: str = DOCUMENTS_PATH, openai_api_key: str = OPENAI_API_KEY):
        """
        Initialize the optimized document retriever.

        Args:
            docs_path: Path to documents directory or file.
            openai_api_key: OpenAI API key.
        """
        if not openai_api_key:
            raise ValueError("OpenAI API Key is required.")

        self.docs_path = Path(docs_path) # Use pathlib for easier path handling
        self.embeddings_dir = self.docs_path.parent / "embeddings" # Place embeddings dir next to docs dir
        self.vector_store_path = str(self.embeddings_dir / "faiss_vector_store") # FAISS save_local uses a FOLDER path
        self.metadata_file = self.embeddings_dir / "doc_metadata.csv"
        self.vector_store = None
        self.retriever = None

        # Initialize embeddings model here - needed for both generation and loading
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)

        # Create necessary directories
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)

        # Set up the document retriever
        self.setup_retriever()

    def _load_documents(self) -> List[Document]:
        """ Load documents from the specified path. """
        loaders = []
        docs_path_str = str(self.docs_path)

        if self.docs_path.is_dir():
             # Check for specific file types before creating DirectoryLoader
            txt_files = list(self.docs_path.rglob("*.txt"))
            pdf_files = list(self.docs_path.rglob("*.pdf"))

            if txt_files:
                 loaders.append(DirectoryLoader(docs_path_str, glob="**/*.txt", loader_cls=TextLoader, recursive=True, show_progress=True))
            if pdf_files:
                 loaders.append(DirectoryLoader(docs_path_str, glob="**/*.pdf", loader_cls=PyPDFLoader, recursive=True, show_progress=True))

        elif self.docs_path.is_file():
            if self.docs_path.suffix == '.txt':
                loaders.append(TextLoader(docs_path_str))
            elif self.docs_path.suffix == '.pdf':
                loaders.append(PyPDFLoader(docs_path_str))

        if not loaders:
            raise ValueError(f"No supported documents (.txt, .pdf) found in {self.docs_path}")

        docs = []
        for loader in loaders:
            try:
                loaded_docs = loader.load()
                if loaded_docs: # Ensure docs were actually loaded
                     docs.extend(loaded_docs)
                     logger.info(f"Loaded {len(loaded_docs)} document(s) using {loader.__class__.__name__}")
                else:
                     logger.warning(f"Loader {loader.__class__.__name__} did not load any documents.")
            except Exception as e:
                # Provide more context on PDF loading errors
                if isinstance(loader, (PyPDFLoader, DirectoryLoader)) and 'pdf' in str(loader.glob):
                    logger.error(f"Error loading PDF documents with {loader.__class__.__name__}. Ensure PyPDFium is installed (`pip install pypdfium2`) and PDFs are valid. Error: {e}", exc_info=True)
                else:
                    logger.error(f"Error loading documents with {loader.__class__.__name__}: {e}", exc_info=True)

        if not docs:
            # Check if path exists if no docs were loaded
            if not self.docs_path.exists():
                 raise ValueError(f"Document path does not exist: {self.docs_path}")
            else:
                 raise ValueError(f"Could not load any supported documents from {self.docs_path}")


        # Add source path to metadata for better tracking
        for doc in docs:
            if 'source' not in doc.metadata:
                 # Sometimes DirectoryLoader doesn't set it as expected, fallback to loader path
                 doc.metadata['source'] = getattr(loader, 'path', str(self.docs_path)) # Use path attribute if available

        return docs

    def _check_vector_store_exists(self) -> bool:
        """ Check if the FAISS vector store files exist. """
        index_file = Path(self.vector_store_path) / "index.faiss"
        pkl_file = Path(self.vector_store_path) / "index.pkl"
        return index_file.exists() and pkl_file.exists()

    def _has_docs_changed(self) -> bool:
        """ Check if documents have changed since last embedding generation. """
        if not self.metadata_file.exists():
            logger.info("Metadata file not found. Assuming changes.")
            return True

        # Load existing metadata
        try:
            metadata_df = pd.read_csv(self.metadata_file)
            # Ensure required columns exist
            if 'path' not in metadata_df.columns or 'mtime' not in metadata_df.columns:
                logger.warning("Metadata file is missing 'path' or 'mtime' columns. Assuming changes.")
                return True
            # Convert path to string for comparison if needed, and mtime to float
            stored_metadata = {row['path']: float(row['mtime']) for _, row in metadata_df.iterrows()}
        except Exception as e:
            logger.error(f"Error reading or parsing metadata file {self.metadata_file}: {e}. Assuming changes.")
            return True

        current_files_metadata = {}
        try:
            if self.docs_path.is_dir():
                for file_path in self.docs_path.rglob('*'):
                    if file_path.is_file() and file_path.suffix in ['.txt', '.pdf']:
                        current_files_metadata[str(file_path)] = file_path.stat().st_mtime
            elif self.docs_path.is_file() and self.docs_path.suffix in ['.txt', '.pdf']:
                 current_files_metadata[str(self.docs_path)] = self.docs_path.stat().st_mtime
            else:
                 logger.warning(f"Document path {self.docs_path} is neither a valid file nor directory.")
                 return True # Treat invalid path as needing update

        except Exception as e:
            logger.error(f"Error accessing document files in {self.docs_path}: {e}. Assuming changes.")
            return True

        # Compare stored metadata with current files
        if set(current_files_metadata.keys()) != set(stored_metadata.keys()):
            logger.info("Detected added or removed document files.")
            return True

        for file_path, current_mtime in current_files_metadata.items():
            # Use a small tolerance for floating point comparison
            if current_mtime > stored_metadata.get(file_path, 0) + 1e-6 : # Check if current time is significantly newer
                logger.info(f"Detected modification in file: {file_path}")
                return True

        logger.info("No document changes detected based on metadata.")
        return False # No changes detected


    def _generate_embeddings(self) -> Tuple[FAISS, pd.DataFrame]:
        """ Generate embeddings for documents and save them using FAISS.save_local. """
        docs = self._load_documents()
        if not docs:
             raise RuntimeError("No documents were loaded, cannot generate embeddings.") # Should not happen if _load_docs raises error

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        split_docs = text_splitter.split_documents(docs)
        logger.info(f"Processing {len(split_docs)} document chunks for embedding.")
        if not split_docs:
             raise RuntimeError("Splitting documents resulted in zero chunks.")

        # Create vector store using the initialized embeddings model
        try:
            vector_store = FAISS.from_documents(split_docs, self.embeddings)
        except Exception as e:
             logger.error(f"Error creating FAISS index from documents: {e}", exc_info=True)
             raise RuntimeError("Failed to create FAISS index.") from e


        # Collect metadata about the source documents
        metadata = []
        source_files = set()
        if self.docs_path.is_dir():
             for file_path in self.docs_path.rglob('*'):
                 if file_path.is_file() and file_path.suffix in ['.txt', '.pdf']:
                      source_files.add(file_path)
        elif self.docs_path.is_file() and self.docs_path.suffix in ['.txt', '.pdf']:
             source_files.add(self.docs_path)

        for file_path in source_files:
            try:
                stat_result = file_path.stat()
                metadata.append({
                    'path': str(file_path),
                    'mtime': stat_result.st_mtime,
                    'size': stat_result.st_size
                })
            except Exception as e:
                 logger.warning(f"Could not get metadata for file {file_path}: {e}")


        metadata_df = pd.DataFrame(metadata)

        # Save embeddings using FAISS save_local
        try:
            vector_store.save_local(self.vector_store_path)
            logger.info(f"Successfully saved FAISS index to {self.vector_store_path}")
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}", exc_info=True)
            raise RuntimeError("Failed to save FAISS index.") from e

        # Save metadata
        try:
            metadata_df.to_csv(self.metadata_file, index=False)
            logger.info(f"Successfully saved metadata to {self.metadata_file}")
        except Exception as e:
             logger.error(f"Error saving metadata file: {e}", exc_info=True)
             # Don't necessarily raise here, as embeddings were saved, but log prominently


        return vector_store, metadata_df

    def _load_embeddings(self) -> FAISS:
        """ Load pre-computed embeddings using FAISS.load_local. """
        logger.info(f"Attempting to load FAISS index from {self.vector_store_path}")
        try:
            # Crucially, pass the embeddings model again when loading
            # allow_dangerous_deserialization=True is often needed for Langchain's pkl file
            vector_store = FAISS.load_local(
                self.vector_store_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info(f"Successfully loaded FAISS index from {self.vector_store_path}")
            return vector_store
        except ImportError as ie:
            logger.error(f"Import error during FAISS load: {ie}. Do you have all dependencies installed?", exc_info=True)
            raise RuntimeError("Failed to load FAISS index due to missing dependency.") from ie
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}", exc_info=True)
            # If loading fails, maybe delete potentially corrupt files? Or let user handle it?
            # For now, just raise.
            raise RuntimeError(f"Failed to load FAISS index from {self.vector_store_path}.") from e

    def setup_retriever(self):
        """ Set up document retriever, using pre-computed embeddings if valid. """
        try:
            # Check if store exists AND documents haven't changed
            if self._check_vector_store_exists() and not self._has_docs_changed():
                try:
                    self.vector_store = self._load_embeddings()
                    logger.info("Using pre-computed embeddings.")
                except Exception as load_err:
                    logger.warning(f"Failed to load existing embeddings: {load_err}. Will attempt regeneration.")
                    # Force regeneration if loading fails
                    self.vector_store, _ = self._generate_embeddings()
            else:
                if not self._check_vector_store_exists():
                     logger.info("Embeddings files not found.")
                # Else: _has_docs_changed() was true

                logger.info("Generating new embeddings...")
                self.vector_store, _ = self._generate_embeddings()

            # Create retriever if vector_store was successfully loaded or generated
            if self.vector_store:
                self.retriever = self.vector_store.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 5} # Return top 5 results
                )
                logger.info("Retriever setup complete.")
            else:
                 # This case should ideally not be reached if _generate raises errors
                 raise RuntimeError("Vector store could not be initialized.")

        except Exception as e:
            logger.error(f"Fatal error setting up document retriever: {e}", exc_info=True)
            # Make sure retriever is None if setup fails
            self.retriever = None
            self.vector_store = None
            raise # Re-raise the exception to signal failure to the caller


    def retrieve_relevant_context(self, query: str) -> str:
        """ Retrieve relevant context for a query. """
        if not self.retriever:
            logger.error("Retriever is not available (failed setup?). Cannot retrieve context.")
            # Consider raising an error or returning a more specific message
            # raise RuntimeError("Retriever is not initialized.")
            return "Error: The document retrieval system is not ready."

        try:
            start_time = time.time()
            docs = self.retriever.get_relevant_documents(query)
            end_time = time.time()
            logger.info(f"Retrieved {len(docs)} documents for query in {end_time - start_time:.2f} seconds.")
            if not docs:
                 return "I couldn't find specific information related to your query in the documents."
            # Format the output nicely
            context_parts = [f"Source: {doc.metadata.get('source', 'N/A')}\n{doc.page_content}" for doc in docs]
            return "\n\n---\n\n".join(context_parts)
        except Exception as e:
            logger.error(f"Error retrieving context for query '{query}': {e}", exc_info=True)
            return "I encountered an error while trying to find information for your query."

    def regenerate_embeddings(self) -> None:
        """ Force regeneration of embeddings. """
        logger.warning("Forcing regeneration of embeddings...")
        try:
            # Generate embeddings and update the vector store
            self.vector_store, _ = self._generate_embeddings()
            # Recreate the retriever with the new vector store
            if self.vector_store:
                 self.retriever = self.vector_store.as_retriever(
                     search_type="similarity",
                     search_kwargs={"k": 5}
                 )
                 logger.info("Successfully regenerated embeddings and updated retriever.")
            else:
                 # Should not happen if _generate raises on failure
                 raise RuntimeError("Embeddings regeneration failed to produce a vector store.")
        except Exception as e:
            logger.error(f"Error during forced regeneration of embeddings: {e}", exc_info=True)
            # Keep existing retriever? Or set to None? Setting to None indicates failure.
            self.retriever = None
            self.vector_store = None
            raise # Re-raise to signal failure


