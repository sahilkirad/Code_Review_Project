from app.core.rag import RAGSystem
import time

def test_rag():
    print("--- Initializing RAG System ---")
    rag = RAGSystem()
    
    # 1. Define a "Training Example" (A known code smell)
    bad_code = """
    def calculate(a, b):
        return a + b
    """
    smell = "Missing Docstring"
    fix = """
    def calculate(a, b):
        '''Adds two numbers.'''
        return a + b
    """
    
    print(f"--- Uploading Test Example: {smell} ---")
    rag.upsert_code_example("test-id-001", bad_code, smell, fix)
    
    # Wait a moment for Pinecone to index
    print("Waiting 5 seconds for indexing...")
    time.sleep(5)
    
    # 2. Simulate a User Query (Similar but not identical code)
    user_code = """
    def subtract(x, y):
        return x - y
    """
    print("--- Searching for similar code ---")
    results = rag.search_similar_code(user_code, top_k=1)
    
    if results:
        match = results[0]
        print("✅ SUCCESS: Found similar example!")
        print(f"Score: {match['score']}")
        print(f"Retrieved Metadata (Smell Type): {match['metadata']['smell_type']}")
    else:
        print("❌ FAILED: No results found.")

if __name__ == "__main__":
    test_rag()