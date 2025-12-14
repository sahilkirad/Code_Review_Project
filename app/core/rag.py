import os
import logging
from typing import List
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGSystem:
    def __init__(self):
        # 1. Initialize the Embedding Model
        # "all-MiniLM-L6-v2" is fast and effective for code/text similarity
        logger.info("Loading embedding model...")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # 2. Initialize Pinecone
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX_NAME")
        
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY not found in .env file")

        self.pc = Pinecone(api_key=self.api_key)
        self.index = self.pc.Index(self.index_name)

    def generate_embedding(self, text: str):
        """
        Converts text/code into a vector (list of floats).
        """
        # We assume the model outputs a numpy array, convert to list for Pinecone
        embedding = self.encoder.encode(text).tolist()
        return embedding

    def upsert_code_example(self, example_id: str, code_snippet: str, smell_type: str, fix: str):
        """
        Stores a known code smell and its fix in the database.
        """
        vector = self.generate_embedding(code_snippet)
        
        # Metadata is what we retrieve back to show the LLM
        metadata = {
            "code": code_snippet,
            "smell_type": smell_type,
            "fix": fix
        }
        
        # Upsert to Pinecone
        self.index.upsert(vectors=[(example_id, vector, metadata)])
        logger.info(f"Stored example {example_id} in Pinecone.")

    def search_similar_code(self, query_code: str, top_k: int = 3, similarity_threshold: float = 0.6):
        """
        Given a new piece of code, find the most similar examples in our DB.
        
        Args:
            query_code: Code snippet to search for
            top_k: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0.0-1.0) to include results
        
        Returns:
            List of matches above the similarity threshold
        """
        query_vector = self.generate_embedding(query_code)
        
        results = self.index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True
        )
        
        # Filter by similarity threshold
        filtered_matches = [
            match for match in results.get('matches', [])
            if match.get('score', 0) >= similarity_threshold
        ]
        
        return filtered_matches
    
    def batch_upsert_examples(self, examples: List[dict]):
        """
        Batch upsert multiple code examples to Pinecone for efficiency.
        
        Args:
            examples: List of dicts with keys: example_id, code_snippet, smell_type, fix
        """
        vectors_to_upsert = []
        
        for example in examples:
            vector = self.generate_embedding(example['code_snippet'])
            metadata = {
                "code": example['code_snippet'],
                "smell_type": example['smell_type'],
                "fix": example['fix']
            }
            vectors_to_upsert.append((example['example_id'], vector, metadata))
        
        if vectors_to_upsert:
            self.index.upsert(vectors=vectors_to_upsert)
            logger.info(f"Batch stored {len(vectors_to_upsert)} examples in Pinecone.")