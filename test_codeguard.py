"""
Test file for CodeGuard analysis
This file contains various code issues for testing purposes.
"""

# Security Issue: Hardcoded API key
API_KEY = "sk-1234567890abcdef"
SECRET_TOKEN = "my_secret_token_12345"

# Bug: Missing error handling
def divide_numbers(a, b):
    result = a / b  # Will crash if b is 0
    return result

# Code Smell: Magic numbers
def calculate_discount(price):
    if price > 100:
        return price * 0.1  # What is 0.1? Should be a named constant
    return 0

# Performance Issue: Inefficient loop
def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):
        for j in range(len(items)):  # O(n²) complexity
            if i != j and items[i] == items[j]:
                duplicates.append(items[i])
    return duplicates

# Security Issue: SQL injection vulnerability
def get_user_data(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"  # SQL injection risk
    # Should use parameterized queries
    return query

# Bug: Unused variable
def process_data(data):
    processed = []
    temp = data.copy()  # temp is never used
    for item in data:
        processed.append(item * 2)
    return processed

# Code Smell: Long function with multiple responsibilities
def handle_user_request(user_id, action, data):
    # Fetch user
    user = get_user(user_id)
    # Validate action
    if action not in ['create', 'update', 'delete']:
        return {'error': 'Invalid action'}
    # Process data
    if action == 'create':
        result = create_record(data)
    elif action == 'update':
        result = update_record(user_id, data)
    else:
        result = delete_record(user_id)
    # Log action
    log_action(user_id, action)
    # Send notification
    send_notification(user.email, action)
    # Return result
    return result

# Security Issue: Weak password validation
def validate_password(password):
    if len(password) < 4:  # Too weak - should be at least 8 characters
        return False
    return True

# Bug: Missing return statement
def get_status():
    status = "active"
    # Missing return statement

# Code Smell: Global mutable state
counter = 0

def increment_counter():
    global counter
    counter += 1
    return counter

# Performance Issue: Unnecessary list comprehension
def filter_even_numbers(numbers):
    return [n for n in numbers if n % 2 == 0]  # Could use filter() for better performance

# Security Issue: Exposed sensitive data in logs
import logging

def process_payment(credit_card, amount):
    logging.info(f"Processing payment: {credit_card} for ${amount}")  # Should not log credit card
    # Process payment
    return True

# Bug: Incorrect comparison operator (syntax error)
def check_age(age):
    if age == 18:  
        return "Adult"
    return "Minor"

# Code Smell: Duplicate code
def calculate_area_rectangle(length, width):
    return length * width

def calculate_area_square(side):
    return side * side  # Could reuse calculate_area_rectangle(side, side)

# Missing docstring for complex function
def complex_algorithm(data, threshold, multiplier):
    result = []
    for item in data:
        if item > threshold:
            processed = item * multiplier
            if processed < 100:
                result.append(processed)
    return result

