import json
import os
import sys

# Add the parent directory to sys.path so we can import 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.llm import CodeReviewLLM

# 1. Define Raw "Bad Code" Examples
# In a real project, you would load these from a file or git repo.
# Expanded Dataset for Synthetic Generation
raw_snippets = [
    # --- CATEGORY: SECURITY VULNERABILITIES ---
    """
    def get_user(user_id):
        # SQL Injection vulnerability
        query = "SELECT * FROM users WHERE id = " + user_id
        cursor.execute(query)
    """,
    """
    def verify_password(stored, attempt):
        # Timing attack vulnerability (standard comparison)
        return stored == attempt 
    """,
    """
    import subprocess
    def ping_site(url):
        # Command Injection vulnerability
        subprocess.call("ping " + url, shell=True)
    """,
    """
    def save_creds(username, password):
        # Hardcoded secret & plain text log
        with open("secrets.txt", "w") as f:
            f.write(f"{username}:{password}")
    """,
    
    # --- CATEGORY: PERFORMANCE ISSUES ---
    """
    def find_duplicate(numbers):
        # O(n^2) complexity
        duplicates = []
        for i in range(len(numbers)):
            for j in range(i + 1, len(numbers)):
                if numbers[i] == numbers[j]:
                    duplicates.append(numbers[i])
        return duplicates
    """,
    """
    def load_file(filename):
        # Reading entire file into memory at once
        f = open(filename, 'r')
        content = f.read()
        return content.splitlines()
    """,
    """
    def concat_strings(words):
        # Inefficient string concatenation
        result = ""
        for word in words:
            result += word + " "
        return result
    """,

    # --- CATEGORY: CODE STYLE & BEST PRACTICES ---
    """
    def Calc(x,y):
        # Non-standard naming (PascalCase function), generic names
        z = x + y
        return z
    """,
    """
    def process(data):
        if data:
            if len(data) > 0:
                if data[0] != None:
                    print(data[0]) # Deep nesting (Arrow Code)
    """,
    """
    def get_status(code):
        # Magic numbers instead of Enums/Constants
        if code == 1:
            return "Pending"
        elif code == 2:
            return "Active"
        elif code == 3:
            return "Banned"
    """,
    """
    x = 10 # Global variable usage
    def increment():
        global x
        x += 1
    """,

    # --- CATEGORY: POTENTIAL BUGS ---
    """
    def divide(a, b):
        # Missing ZeroDivisionError handling
        return a / b
    """,
    """
    def add_item(item, list=[]):
        # Mutable default argument (Classic Python Bug)
        list.append(item)
        return list
    """,
    """
    def read_config():
        f = open("config.txt")
        data = f.read()
        # Missing f.close() or 'with' statement
        return data
    """,
    """
    def check_equal(a, b):
        # Floating point equality check
        return a == b 
    """,

    # --- CATEGORY: ERROR HANDLING ---
    """
    def api_call():
        try:
            requests.get("https://api.com")
        except:
            # Bare except clause catches SystemExit/KeyboardInterrupt
            print("Something went wrong")
    """,
    """
    def parse_data(json_str):
        try:
            return json.loads(json_str)
        except ValueError:
            pass # Silent failure (Swallowing exceptions)
    """,

    # --- CATEGORY: MAINTAINABILITY ---
    """
    def god_function():
        # Function does too many things (SRP Violation)
        connect_db()
        data = fetch_data()
        clean_data = clean(data)
        email_user(clean_data)
        generate_pdf(clean_data)
        update_metrics()
    """,
    """
    # Duplicate Code Example 1
    def area_rect(w, h):
        if w < 0 or h < 0:
            raise ValueError("Positive only")
        return w * h

    # Duplicate Code Example 2
    def area_square(s):
        if s < 0:
            raise ValueError("Positive only")
        return s * s
    """,
    """
    class Animal:
        pass
    class Dog(Animal):
        pass
    # Deep inheritance hierarchy without reason
    class Poodle(Dog): 
        pass
    class ToyPoodle(Poodle):
        pass
    """
]

def generate_dataset():
    print("--- 🤖 Starting Synthetic Data Generation ---")
    llm = CodeReviewLLM(model_name="qwen2.5-coder:1.5b")
    
    output_file = "data/training_data.jsonl"
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    with open(output_file, "w") as f:
        for i, code in enumerate(raw_snippets):
            print(f"Generating example {i+1}/{len(raw_snippets)}...")
            
            # 1. Ask the generic model to review it
            # We pass an empty list [] for rag_context to force it to rely on its own knowledge
            response = llm.review_code(code, rag_context=[])
            
            # 2. Format it for Fine-Tuning (Chat Format)
            # This is the standard format for Llama/Qwen training
            training_example = {
                "messages": [
                    {"role": "system", "content": "You are an expert code reviewer. Output strictly valid JSON."},
                    {"role": "user", "content": f"Review this code:\n{code}"},
                    {"role": "assistant", "content": json.dumps(response)} # The model's answer is the target
                ]
            }
            
            # 3. Save line by line
            f.write(json.dumps(training_example) + "\n")
            
    print(f"✅ Data generation complete! Saved to {output_file}")

if __name__ == "__main__":
    generate_dataset()