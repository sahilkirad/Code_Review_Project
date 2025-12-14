from app.core.ingestion import CodeParser

# 1. Simulate a messy file with a Class and a Method
sample_code = """
import os

class PaymentProcessor:
    def __init__(self):
        self.api_key = os.getenv("API_KEY")

    def process_payment(self, amount):
        # Suppose the user changed line 10 (the print statement)
        tax = 0.1
        total = amount + (amount * tax)
        print(f"Processing payment: {total}")
        return total

def unrelated_function():
    pass
"""

# 2. Initialize the parser
parser = CodeParser()

# 3. Simulate a change on Line 12 (inside process_payment)
changed_line = 12
print(f"--- Testing Extraction for Change on Line {changed_line} ---")

result = parser.find_relevant_block(sample_code, changed_line)

if result:
    print(f"✅ FOUND: {result['type']} '{result['name']}'")
    print(f"Lines: {result['start_line']} - {result['end_line']}")
    print("--- Code Snippet Sent to LLM ---")
    print(result['code'])
    print("--------------------------------")
else:
    print("❌ FAILED: No relevant block found.")