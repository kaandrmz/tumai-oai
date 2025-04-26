"""
Document retrieval module using RAG (Retrieval Augmented Generation).
Handles document loading, processing, and retrieval.
"""

import os
import sys
from typing import List, Optional
import logging

from langchain_community.document_loaders import TextLoader, PyPDFLoader, DirectoryLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

# Add the project root to path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import OPENAI_API_KEY, DOCUMENTS_PATH

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DocumentRetriever:
    """
    Helper class to handle document retrieval with RAG.
    Loads documents, processes them, and provides retrieval functionality.
    """

    def __init__(self, docs_path: str = DOCUMENTS_PATH):
        """
        Initialize the document retriever.

        Args:
            docs_path: Path to documents directory or file
        """
        self.docs_path = docs_path
        self.vector_store = None
        self.retriever = None

        # Create documents directory if it doesn't exist
        if not os.path.exists(self.docs_path):
            os.makedirs(self.docs_path)
            logger.info(f"Created documents directory at {self.docs_path}")

            # Create a sample document for testing
            with open(os.path.join(self.docs_path, "sample.txt"), "w") as f:
                f.write("This is a sample document for testing the RAG system.\n")
                f.write("It contains information about quantum computing.\n")
                f.write("Quantum computing is a type of computing that uses quantum phenomena such as superposition and entanglement.\n")
            logger.info("Created a sample document for testing")

        # Set up the document retriever
        self.setup_retriever()

    def _load_documents(self) -> List[Document]:
        """
        Load documents from the specified path.

        Returns:
            List of loaded documents

        Raises:
            ValueError: If no supported documents are found
        """
        loaders = []

        if os.path.isdir(self.docs_path):
            # Handle directory of documents

            # Load text files if any exist
            if any(file.endswith('.txt') for file in os.listdir(self.docs_path)):
                text_loader = DirectoryLoader(
                    self.docs_path,
                    glob="**/*.txt",
                    loader_cls=TextLoader
                )
                loaders.append(text_loader)

            # Load PDF files if any exist
            if any(file.endswith('.pdf') for file in os.listdir(self.docs_path)):
                pdf_loader = DirectoryLoader(
                    self.docs_path,
                    glob="**/*.pdf",
                    loader_cls=PyPDFLoader
                )
                loaders.append(pdf_loader)
        else:
            # Handle single file
            if self.docs_path.endswith('.txt'):
                loaders.append(TextLoader(self.docs_path))
            elif self.docs_path.endswith('.pdf'):
                loaders.append(PyPDFLoader(self.docs_path))

        if not loaders:
            raise ValueError(f"No supported documents found in {self.docs_path}")

        # Load all documents
        docs = []
        for loader in loaders:
            try:
                docs.extend(loader.load())
                logger.info(f"Loaded documents using {loader.__class__.__name__}")
            except Exception as e:
                logger.error(f"Error loading documents with {loader.__class__.__name__}: {e}")

        if not docs:
            raise ValueError(f"Could not load any documents from {self.docs_path}")

        return docs

    def setup_retriever(self):
        """
        Set up document loading, processing and creating the retriever.

        Raises:
            Exception: If there's an error during setup
        """
        try:
            # Load documents
            docs = self._load_documents()

            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len
            )
            split_docs = text_splitter.split_documents(docs)

            # Create vector store and retriever
            embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
            self.vector_store = FAISS.from_documents(split_docs, embeddings)
            self.retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )

            logger.info(f"Successfully processed {len(split_docs)} document chunks")

        except Exception as e:
            logger.error(f"Error setting up document retriever: {e}")
            raise

    def retrieve_relevant_context(self, query: str) -> str:
        """
        Retrieve relevant context for a query.

        Args:
            query: The query to retrieve context for

        Returns:
            String containing relevant context

        Raises:
            ValueError: If retriever is not set up
        """
        if not self.retriever:
            logger.error("Retriever not set up")
            return "I don't have any information on that topic yet."

        try:
            docs = self.retriever.get_relevant_documents(query)
            return "\n\n".join([doc.page_content for doc in docs])
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return "I encountered an error while retrieving information on that topic."