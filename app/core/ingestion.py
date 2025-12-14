import ast
import logging

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodeParser:
    """
    Parses Python source code to extract functions and classes.
    This ensures the LLM receives complete logical blocks, not just random lines.
    """

    def extract_functions_and_classes(self, source_code: str):
        """
        Scans the source code and returns a list of dicts.
        Each dict contains: name, type, start_line, end_line, and the full code.
        """
        tree = ast.parse(source_code)
        extracted_blocks = []

        # Walk through every node in the syntax tree
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                
                # Determine the type of block
                block_type = "class" if isinstance(node, ast.ClassDef) else "function"
                
                # Get the exact source code for this block
                # ast.get_source_segment works in Python 3.8+
                segment = ast.get_source_segment(source_code, node)
                
                block_info = {
                    "name": node.name,
                    "type": block_type,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "code": segment
                }
                extracted_blocks.append(block_info)
        
        return extracted_blocks
    
    def extract_module_level_code(self, source_code: str):
        """
        Extracts code that exists at the module level (outside functions/classes).
        This includes imports, constants, top-level assignments, etc.
        
        Returns:
            Dict with module-level code and its line range, or None if no module-level code exists.
        """
        try:
            tree = ast.parse(source_code)
            lines = source_code.splitlines()
            
            # Get all function and class line ranges
            block_ranges = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    block_ranges.append((node.lineno, node.end_lineno))
            
            # If no blocks, entire file is module-level
            if not block_ranges:
                return {
                    "name": "<module>",
                    "type": "module",
                    "start_line": 1,
                    "end_line": len(lines),
                    "code": source_code
                }
            
            # Find module-level code (code not in any function/class)
            module_lines = []
            for i, line in enumerate(lines, start=1):
                in_block = False
                for start, end in block_ranges:
                    if start <= i <= end:
                        in_block = True
                        break
                if not in_block:
                    module_lines.append((i, line))
            
            if not module_lines:
                return None
            
            # Extract module-level code
            start_line = module_lines[0][0]
            end_line = module_lines[-1][0]
            module_code = "\n".join([line for _, line in module_lines])
            
            # Only return if there's meaningful code (not just blank lines/comments)
            if module_code.strip() and len(module_code.strip()) > 10:
                return {
                    "name": "<module>",
                    "type": "module",
                    "start_line": start_line,
                    "end_line": end_line,
                    "code": module_code
                }
            
            return None
        except Exception as e:
            logger.warning(f"Failed to extract module-level code: {str(e)}")
            return None

    def find_relevant_block(self, source_code: str, changed_line: int):
        """
        Given a specific line number that changed (from a Git diff),
        find the smallest function or class that contains it.
        """
        blocks = self.extract_functions_and_classes(source_code)
        
        best_match = None
        
        for block in blocks:
            # Check if the changed line falls inside this block
            if block["start_line"] <= changed_line <= block["end_line"]:
                # If we found a match, we prefer the 'smallest' one (most specific)
                # e.g., a method inside a class is better than the whole class
                if best_match is None:
                    best_match = block
                else:
                    # If this block is smaller (fewer lines) than the current best, take it
                    current_len = best_match["end_line"] - best_match["start_line"]
                    new_len = block["end_line"] - block["start_line"]
                    if new_len < current_len:
                        best_match = block
                        
        return best_match