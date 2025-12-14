from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, END
from app.core.rag import RAGSystem
from app.core.llm import CodeReviewLLM
from app.core.ingestion import CodeParser
import os
import logging
import ast
import hashlib
import time
from functools import lru_cache

logger = logging.getLogger(__name__)

# Simple in-memory cache for embeddings and results
_embedding_cache = {}
_result_cache = {}

def clear_cache():
    """Clear the result cache. Useful for testing."""
    global _result_cache
    _result_cache = {}
    logger.info("Cache cleared")

# Initialize our tools ONCE (global scope for efficiency)
rag_system = RAGSystem()
llm_client = CodeReviewLLM(model_name="veritas-pro")  # Using fine-tuned model
code_parser = CodeParser()

class GraphState(TypedDict):
    filename: str
    code_snippet: str
    rag_context: List[dict]
    review_issues: List[dict]
    final_report: str
    syntax_errors: List[dict]
    file_size: int
    num_blocks: int
    blocks: List[dict]
    block_issues: List[dict]  # Issues per block
    _llm_debug: Optional[Dict[str, Any]]  # Debug info from LLM (raw response, length, has_json)

def syntax_check_node(state: GraphState):
    """
    NEW NODE: Checks for syntax errors before semantic analysis.
    """
    code = state["code_snippet"]
    filename = state["filename"]
    syntax_errors = []
    
    logger.info(f"--- 🔍 Syntax Check for {filename} ---")
    
    try:
        # Try to parse the code
        ast.parse(code)
        logger.info(f"Syntax check passed: No syntax errors in {filename}")
    except SyntaxError as e:
        syntax_errors.append({
            "type": "Syntax Error",
            "severity": "High",
            "explanation": f"Syntax error at line {e.lineno}: {e.msg}",
            "suggested_fix": f"Fix syntax error: {e.msg}. Check line {e.lineno} for missing brackets, commas, or indentation issues."
        })
        logger.warning(f"❌ Syntax error detected in {filename}: {e.msg} at line {e.lineno}")
    except Exception as e:
        logger.warning(f"Unexpected error during syntax check: {str(e)}", exc_info=True)
    
    logger.info(f"Syntax check complete: {len(syntax_errors)} syntax errors found")
    
    return {"syntax_errors": syntax_errors}

def retrieve_node(state: GraphState):
    """
    REAL NODE: Queries Pinecone for similar code with adaptive top_k.
    """
    code = state["code_snippet"]
    file_size = state.get("file_size", 0)
    num_blocks = state.get("num_blocks", 0)
    filename = state.get("filename", "unknown")
    
    logger.info(f"--- 🔍 Retrieving Context for {filename} ---")
    
    # Adaptive top_k based on file complexity
    # Increased to fetch more relevant examples from Pinecone
    if file_size > 1000 or num_blocks > 10:
        top_k = 5  # More context for complex files
        logger.info(f"Using top_k=5 (complex file: {file_size} lines, {num_blocks} blocks)")
    elif file_size < 200:
        top_k = 3  # Increased from 1 to 3 for better context (was: minimal context for simple files)
        logger.info(f"Using top_k=3 (simple file: {file_size} lines) - fetching more examples for better context")
    else:
        top_k = 3  # Increased from 2 to 3 for better context
        logger.info(f"Using top_k=3 (medium file: {file_size} lines) - fetching more examples for better context")
    
    # Adaptive similarity threshold
    similarity_threshold = 0.6  # Default, can be made configurable
    
    # Search Pinecone with similarity threshold
    logger.info(f"Searching Pinecone with top_k={top_k}, similarity_threshold={similarity_threshold}")
    matches = rag_system.search_similar_code(code, top_k=top_k, similarity_threshold=similarity_threshold)
    logger.info(f"Found {len(matches)} similar code examples in Pinecone")
    
    # Extract and normalize metadata (handle both 'smell' and 'smell_type' keys)
    context = []
    for m in matches:
        metadata = m.get('metadata', {})
        # Normalize to use 'smell' key for consistency
        normalized = {
            'smell': metadata.get('smell') or metadata.get('smell_type', 'Unknown'),
            'fix': metadata.get('fix', 'Unknown')
        }
        context.append(normalized)
        logger.debug(f"RAG context: {normalized.get('smell', 'Unknown')}")
    
    return {"rag_context": context}

def analyze_node(state: GraphState):
    """
    REAL NODE: Analyzes code blocks or entire file based on file characteristics.
    Now includes module-level code analysis when doing block-level analysis.
    """
    code = state["code_snippet"]
    context = state["rag_context"]
    blocks = state.get("blocks", [])
    file_size = state.get("file_size", 0)
    filename = state.get("filename", "unknown")
    
    logger.info(f"--- 🧠 Analyzing Code with LLM for {filename} ---")
    logger.info(f"File size: {file_size} lines, Blocks found: {len(blocks)}")
    
    all_issues = []
    block_issues = []
    
    # Block-level analysis for files with blocks and appropriate size
    if blocks and file_size > 200:
        logger.info(f"--- Using BLOCK-LEVEL analysis: {len(blocks)} blocks ---")
        
        # Track all debug info from multiple LLM calls
        all_debug_info = []
        
        # CRITICAL FIX: Also analyze module-level code (imports, constants, top-level assignments)
        module_block = code_parser.extract_module_level_code(code)
        if module_block:
            logger.info(f"--- Analyzing MODULE-LEVEL code (lines {module_block['start_line']}-{module_block['end_line']}) ---")
            module_result = llm_client.review_code(module_block["code"], context)
            module_issues = module_result.get("issues", [])
            
            # Capture debug info
            module_debug = module_result.get("_debug", {})
            if module_debug:
                all_debug_info.append(module_debug)
            
            logger.info(f"Module-level analysis found {len(module_issues)} issues")
            
            # Add module context to issues
            for issue in module_issues:
                issue["block_name"] = "<module>"
                issue["block_type"] = "module"
                issue["block_lines"] = f"{module_block['start_line']}-{module_block['end_line']}"
            
            all_issues.extend(module_issues)
            block_issues.append({
                "block": "<module>",
                "type": "module",
                "issues": module_issues
            })
        
        # Analyze each function/class block
        for block in blocks:
            block_code = block.get("code", "")
            block_name = block.get("name", "unknown")
            block_type = block.get("type", "function")
            
            logger.info(f"--- Analyzing {block_type} '{block_name}' (lines {block.get('start_line', 0)}-{block.get('end_line', 0)}) ---")
            
            # Analyze each block with context
            block_result = llm_client.review_code(block_code, context)
            block_issue_list = block_result.get("issues", [])
            
            # Capture debug info from each block
            block_debug = block_result.get("_debug", {})
            if block_debug:
                all_debug_info.append(block_debug)
            
            logger.info(f"Block '{block_name}' analysis found {len(block_issue_list)} issues")
            if block_issue_list:
                logger.debug(f"Issues in '{block_name}': {[i.get('type', 'Unknown') for i in block_issue_list]}")
            
            # Add block context to each issue
            for issue in block_issue_list:
                issue["block_name"] = block_name
                issue["block_type"] = block_type
                issue["block_lines"] = f"{block.get('start_line', 0)}-{block.get('end_line', 0)}"
            
            all_issues.extend(block_issue_list)
            block_issues.append({
                "block": block_name,
                "type": block_type,
                "issues": block_issue_list
            })
        
        # Use the debug info with the longest response (most complete) from block analysis
        if all_debug_info:
            llm_debug = max(all_debug_info, key=lambda x: x.get("response_length", 0))
            logger.info(f"Block-level analysis: Using LLM debug info with response_length={llm_debug.get('response_length', 0)} (from {len(all_debug_info)} LLM calls)")
        else:
            llm_debug = {}
            logger.warning("Block-level analysis: No LLM debug info found")
    else:
        # Full file analysis for small files or when no blocks found
        logger.info(f"--- Using FULL-FILE analysis ---")
        result = llm_client.review_code(code, context)
        all_issues = result.get("issues", [])
        
        # Capture debug info from LLM response
        debug_info = result.get("_debug", {})
        if debug_info:
            logger.warning(f"LLM Debug Info: Response length={debug_info.get('response_length', 0)}, Has JSON={debug_info.get('has_json', False)}")
            if not debug_info.get("has_json", False):
                logger.error(f"LLM did not return JSON! Raw response preview: {debug_info.get('raw_response', '')[:500]}")
        
        logger.info(f"Full-file analysis found {len(all_issues)} issues")
        if all_issues:
            logger.debug(f"Issue types found: {[i.get('type', 'Unknown') for i in all_issues]}")
        else:
            logger.warning(f"LLM returned NO ISSUES for file {filename}. This might indicate a problem.")
            if debug_info:
                logger.error(f"LLM Debug: {debug_info}")
    
    logger.info(f"--- Total issues found: {len(all_issues)} ---")
    
    # Pass debug info through state
    # For full-file analysis, get debug from result
    # For block-level analysis, llm_debug was already set above
    if 'llm_debug' not in locals():
        llm_debug = {}
        if 'result' in locals() and isinstance(result, dict):
            llm_debug = result.get("_debug", {})
            if llm_debug:
                logger.info(f"Full-file analysis: Using LLM debug info with response_length={llm_debug.get('response_length', 0)}")
            else:
                logger.warning("Full-file analysis: No LLM debug info found in result")
    
    return {
        "review_issues": all_issues,
        "block_issues": block_issues,
        "_llm_debug": llm_debug
    }

def store_node(state: GraphState):
    """
    NEW NODE: Stores analyzed results in Pinecone for future reference.
    Runs asynchronously after returning results to user.
    """
    logger.info("--- 💾 STORE NODE: Starting storage process ---")
    
    issues = state.get("review_issues", [])
    code_snippet = state["code_snippet"]
    filename = state["filename"]
    
    logger.info(f"Store node called for {filename} with {len(issues)} total issues")
    
    if not issues:
        logger.info(f"No issues to store for {filename} (empty issues list)")
        return {}  # Nothing to store
    
    # Prepare examples for batch storage (only High/Medium severity)
    examples_to_store = []
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    
    for issue in issues:
        severity = issue.get("severity", "").lower()
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        if severity in ["high", "medium"]:
            # Generate unique ID
            code_hash = hashlib.md5(code_snippet.encode()).hexdigest()[:8]
            issue_type = issue.get("type", "Unknown").replace(" ", "_")
            example_id = f"{filename}_{issue_type}_{code_hash}_{int(time.time())}"
            
            examples_to_store.append({
                "example_id": example_id,
                "code_snippet": code_snippet[:500],  # Limit code length for storage
                "smell_type": issue.get("type", "Unknown"),
                "fix": issue.get("suggested_fix", "No fix provided")
            })
    
    logger.info(f"Issue severity breakdown: High={severity_counts['high']}, Medium={severity_counts['medium']}, Low={severity_counts['low']}")
    logger.info(f"Prepared {len(examples_to_store)} examples for storage (High/Medium only)")
    
    # Batch store in background (non-blocking)
    if examples_to_store:
        try:
            logger.info(f"Attempting to store {len(examples_to_store)} examples in Pinecone...")
            rag_system.batch_upsert_examples(examples_to_store)
            logger.info(f"✅ SUCCESS: Stored {len(examples_to_store)} examples from {filename} in Pinecone")
        except Exception as e:
            logger.error(f"❌ FAILED to store examples in Pinecone: {str(e)}", exc_info=True)
            # Don't fail the workflow if storage fails
    else:
        logger.info(f"No High/Medium severity issues to store (only Low severity issues found)")
    
    return {}

def output_node(state: GraphState):
    """
    Formatting Node - Combines all issues and formats the report.
    """
    logger.info("--- 📝 Formatting Report ---")
    issues = state.get("review_issues", [])
    syntax_errors = state.get("syntax_errors", [])
    
    logger.info(f"Output node: {len(issues)} issues from analyze_node, {len(syntax_errors)} syntax errors")
    
    # Combine syntax errors with review issues (syntax errors first)
    all_issues = syntax_errors + issues
    
    logger.info(f"Total issues after combining: {len(all_issues)}")
    
    if not all_issues:
        report = "✅ Code looks clean! No issues found."
        logger.info("No issues found - code appears clean")
    else:
        report = f"❌ Found {len(all_issues)} issues:\n"
        for i in all_issues:
            block_info = ""
            if "block_name" in i:
                block_info = f" (in {i['block_type']} '{i['block_name']}' at lines {i.get('block_lines', '?')})"
            report += f"- [{i['severity']}] {i['type']}{block_info}: {i['explanation']}\n"
        logger.info(f"Report generated with {len(all_issues)} issues")
    
    # Pass through debug info if available (CRITICAL: Must preserve from analyze_node)
    llm_debug = state.get("_llm_debug", {})
    
    if llm_debug:
        logger.info(f"Output node: Preserving LLM debug info (response_length={llm_debug.get('response_length', 0)})")
    else:
        logger.warning("Output node: No LLM debug info found in state - this should not happen if analyze_node ran")
    
    # Return combined issues so they're included in the final result
    return {
        "final_report": report,
        "review_issues": all_issues,  # Include syntax errors in review_issues
        "_llm_debug": llm_debug  # Pass debug info to API - CRITICAL
    }

# Build the Workflow with new nodes
workflow = StateGraph(GraphState)
workflow.add_node("syntax_check", syntax_check_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("analyze", analyze_node)
workflow.add_node("output", output_node)
workflow.add_node("store", store_node)

workflow.set_entry_point("syntax_check")
workflow.add_edge("syntax_check", "retrieve")
workflow.add_edge("retrieve", "analyze")
workflow.add_edge("analyze", "output")
workflow.add_edge("output", "store")  # Store after output (non-blocking)
workflow.add_edge("store", END)

app = workflow.compile()

class GraphState:
    """
    Wrapper class for the code review workflow.
    Handles file reading, code parsing, and state initialization.
    """
    def __init__(self):
        self.workflow = app
    
    def _filter_false_positives(self, issues: List[dict], code_snippet: str) -> List[dict]:
        """
        Filters out false positives by validating issues against actual code.
        Preserves syntax errors as they are always valid.
        """
        filtered = []
        code_lower = code_snippet.lower()
        
        for issue in issues:
            issue_type = issue.get("type", "").lower()
            explanation = issue.get("explanation", "").lower()
            
            # Never filter syntax errors - they are always real
            if "syntax error" in issue_type or "syntax" in issue_type:
                filtered.append(issue)
                continue
            
            # Filter: Don't flag os.getenv() as hardcoded secrets
            if "hardcoded" in explanation or "hard-coded" in explanation:
                if "os.getenv" in code_snippet or "os.environ" in code_snippet or ".env" in code_lower:
                    continue  # Skip this false positive
            
            # Filter: Don't flag environment variable usage as security issues
            if "security" in issue_type and ("os.getenv" in code_snippet or "os.environ" in code_snippet):
                if "api_key" in explanation or "secret" in explanation or "password" in explanation:
                    # Check if it's actually using env vars correctly
                    if "os.getenv" in code_snippet or "os.environ.get" in code_snippet:
                        continue  # Skip false positive
            
            filtered.append(issue)
        
        return filtered
    
    def _get_code_hash(self, code: str) -> str:
        """Generate hash for caching."""
        return hashlib.md5(code.encode()).hexdigest()
    
    def _check_cache(self, code_hash: str) -> Optional[dict]:
        """Check if result is cached."""
        if code_hash in _result_cache:
            cached = _result_cache[code_hash]
            # Cache valid for 1 hour
            if time.time() - cached.get("timestamp", 0) < 3600:
                logger.info("Using cached result")
                return cached.get("result")
        return None
    
    def _store_cache(self, code_hash: str, result: dict):
        """Store result in cache."""
        _result_cache[code_hash] = {
            "result": result,
            "timestamp": time.time()
        }
    
    def run_workflow(self, input_data: dict):
        """
        Runs the workflow with file_path or direct code snippet.
        Uses CodeParser to analyze logical blocks for better accuracy.
        Implements file size adaptation and caching.
        
        Args:
            input_data: Dict with either:
                - "file_path": path to file (reads file content)
                - OR "code_snippet": direct code string
                - "filename": optional filename (defaults to "code.py")
        
        Returns:
            Dict with final_report and other state data
        """
        # Handle file_path input
        if "file_path" in input_data:
            file_path = input_data["file_path"]
            filename = input_data.get("filename", os.path.basename(file_path))
            
            # Read file content with error handling
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    full_code = f.read()
            except UnicodeDecodeError:
                # Try with different encoding if UTF-8 fails
                try:
                    with open(file_path, "r", encoding="latin-1") as f:
                        full_code = f.read()
                except Exception as e:
                    raise ValueError(f"Could not read file {file_path}: {str(e)}")
        else:
            # Direct code snippet provided
            full_code = input_data.get("code_snippet", "")
            filename = input_data.get("filename", "code.py")
        
        # Check cache
        code_hash = self._get_code_hash(full_code)
        cached_result = self._check_cache(code_hash)
        if cached_result:
            logger.info(f"Cache HIT for {filename} (hash: {code_hash[:8]}...)")
            return cached_result
        else:
            logger.info(f"Cache MISS for {filename} (hash: {code_hash[:8]}...)")
        
        # Calculate file metrics
        file_size = len(full_code.splitlines())
        
        # Parse code into logical blocks (functions/classes) with error handling
        blocks = []
        try:
            blocks = code_parser.extract_functions_and_classes(full_code)
        except SyntaxError:
            # If code has syntax errors, still analyze it
            blocks = []
        except Exception as e:
            logger.warning(f"Code parsing failed: {str(e)}. Analyzing entire file.")
            blocks = []
        
        num_blocks = len(blocks)
        
        # File size adaptation: Determine analysis strategy
        logger.info(f"File size: {file_size} lines, Blocks extracted: {len(blocks)}")
        
        if file_size < 200:
            # Small files: Always use full-file analysis for simplicity
            code_snippet = full_code
            use_blocks = False
            logger.info(f"Strategy: FULL-FILE analysis (small file: {file_size} lines < 200)")
        elif file_size > 1000:
            # Large files: Use block-level analysis
            code_snippet = full_code  # Keep full for context
            use_blocks = True
            logger.info(f"Strategy: BLOCK-LEVEL analysis (large file: {file_size} lines > 1000)")
        else:
            # Medium files: Use full-file analysis for better context (blocks can miss module-level code)
            # Only use blocks if file is very large or has many blocks
            code_snippet = full_code
            use_blocks = len(blocks) > 15  # Only use blocks if there are many blocks
            if use_blocks:
                logger.info(f"Strategy: BLOCK-LEVEL analysis (medium file with many blocks: {len(blocks)} blocks)")
            else:
                logger.info(f"Strategy: FULL-FILE analysis (medium file: {file_size} lines, {len(blocks)} blocks)")
        
        # Create initial state with all new fields
        initial_state = {
            "filename": filename,
            "code_snippet": code_snippet,
            "rag_context": [],
            "review_issues": [],
            "final_report": "",
            "syntax_errors": [],
            "file_size": file_size,
            "num_blocks": num_blocks,
            "blocks": blocks if use_blocks else [],
            "block_issues": [],
            "_llm_debug": None  # Initialize debug info (will be populated by analyze_node)
        }
        
        # Run the workflow
        try:
            result = self.workflow.invoke(initial_state)
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            # Return partial results if available
            result = initial_state
            result["final_report"] = f"Error during analysis: {str(e)}"
        
        # Filter false positives
        issues_before_filter = len(result.get("review_issues", []))
        if result.get("review_issues"):
            result["review_issues"] = self._filter_false_positives(
                result["review_issues"], 
                code_snippet
            )
            issues_after_filter = len(result.get("review_issues", []))
            if issues_before_filter != issues_after_filter:
                logger.info(f"False positive filter: {issues_before_filter} → {issues_after_filter} issues")
        
        # Cache the result
        self._store_cache(code_hash, result)
        logger.info(f"Cached result for {filename}")
        
        return result

# For backward compatibility, export the class
# But also keep 'app' exported for direct use