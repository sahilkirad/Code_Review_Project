import logging
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodeReviewLLM:
    def __init__(self, model_name="veritas-pro"): # <--- UPDATED to your new model
        """
        Uses the Fine-Tuned 'Veritas Pro' Model.
        """
        logger.info(f"Initializing Custom LLM: {model_name}")
        # Temperature 0.1 for precision
        # Add stop sequences to prevent long generation (from model's built-in stops)
        # Add timeout to prevent indefinite hanging
        # num_predict: Limit max tokens to force faster, concise responses (500 tokens = ~375 words)
        self.llm = ChatOllama(
            model=model_name, 
            temperature=0.1,
            stop=["<|im_end|>", "<|endoftext|>"],
            timeout=60.0,  # 1 minute timeout (reduced from 2 minutes)
            num_predict=1000  # Increased to 1000 tokens to allow for multiple issues (was 500)
        )

    def review_code(self, code_snippet: str, rag_context: list):
        # 1. Format the RAG context (handle both 'smell' and 'smell_type' keys)
        context_str = ""
        for item in rag_context:
            smell = item.get('smell') or item.get('smell_type', 'Unknown')
            fix = item.get('fix', 'Unknown')
            context_str += f"- SIMILAR PAST ISSUE: {smell}\n  FIX: {fix}\n"

        # 2. System Prompt - MATCH TRAINING DATA FORMAT EXACTLY
        # Training data uses: "You are an expert code reviewer. Output strictly valid JSON."
        # Add explicit JSON format example to force JSON output
        # Note: Escape curly braces by doubling them ({{ and }}) to prevent template variable errors
        system_message = """You are an expert code reviewer. Analyze the provided code THOROUGHLY and find ALL issues.

CRITICAL RULES - FOLLOW STRICTLY:
1. Analyze EVERY function, EVERY line, and EVERY code pattern
2. Find ALL security issues, bugs, code smells, and potential problems
3. DO NOT miss any issues - be thorough and comprehensive
4. DO NOT echo, repeat, or include the input code in your response
5. DO NOT generate example code or functions
6. Output ONLY a JSON object - nothing before, nothing after
7. Start immediately with {{ and end with }}
8. Each issue must have: type, severity, explanation, suggested_fix

Check for:
- Security issues (hardcoded secrets, SQL injection, command injection, XSS, etc.)
- Bugs (mutable defaults, missing error handling, logic errors, etc.)
- Code smells (poor practices, maintainability issues, etc.)
- Performance issues (inefficient algorithms, etc.)

Output format (JSON only):
{{
  "issues": [
    {{
      "type": "Security Issue",
      "severity": "High",
      "explanation": "Brief explanation",
      "suggested_fix": "How to fix"
    }}
  ]
}}

Your response must be ONLY this JSON format with ALL issues found. No code examples. No explanations. Just JSON."""

        # 3. User Message - MATCH TRAINING DATA FORMAT
        # Training data uses: "Review this code:\n\n{code}"
        # We'll add RAG context if available, but keep the format simple
        if context_str.strip():
            user_message_template = """Review this code THOROUGHLY and find ALL issues. Check every function, every line, and every code pattern. Output ONLY a JSON object with an "issues" array containing ALL issues found.

{code_snippet}

Similar past issues found:
{context_str}

Remember: Find ALL issues - security issues, bugs, code smells. Output ONLY: {{"issues": [...]}}"""
        else:
            # Match training format exactly when no RAG context
            user_message_template = """Review this code THOROUGHLY and find ALL issues. Check every function, every line, and every code pattern. Output ONLY a JSON object with an "issues" array containing ALL issues found.

{code_snippet}

Remember: Find ALL issues - security issues, bugs, code smells. Output ONLY: {{"issues": [...]}}"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", user_message_template)
        ])
        
        # Build the prompt chain
        prompt_chain = prompt | self.llm
        
        try:
            logger.info(f"Invoking LLM with code snippet ({len(code_snippet)} chars), RAG context ({len(rag_context)} items)")
            
            # First, get the raw response to debug
            prompt_input = {
                "context_str": context_str,
                "code_snippet": code_snippet
            }
            
            # Log the actual prompt being sent
            formatted_prompt = prompt.format(**prompt_input)
            logger.debug(f"Formatted prompt:\n{formatted_prompt}")
            
            # Get raw LLM response
            raw_response = prompt_chain.invoke(prompt_input)
            logger.info(f"Raw LLM response type: {type(raw_response)}")
            logger.info(f"Raw LLM response content: {raw_response.content if hasattr(raw_response, 'content') else str(raw_response)[:500]}")
            
            # Try to parse JSON
            import json
            import re
            raw_content = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
            
            # Store debug info early (before any parsing)
            debug_info = {
                "raw_response": raw_content[:2000],  # First 2000 chars for debugging
                "response_length": len(raw_content),
                "has_json": bool(re.search(r'\{.*"issues".*\}', raw_content, re.DOTALL))
            }
            
            # First, try direct JSON parsing
            try:
                parser = JsonOutputParser()
                result = parser.parse(raw_content)
                logger.info("Direct JSON parsing succeeded")
            except Exception as parse_error:
                logger.warning(f"Direct JSON parsing failed: {parse_error}")
                logger.debug(f"Raw response (first 1000 chars): {raw_content[:1000]}")
                
                # CRITICAL FIX: Find ALL JSON objects with "issues" key, then take the LAST one with actual issues
                # The model sometimes outputs empty {"issues": []} first, then example code, then the real JSON
                
                # Method 1: Find all positions where "issues" appears, then try to extract complete JSON from each
                issues_positions = [m.start() for m in re.finditer(r'"issues"', raw_content)]
                all_parsed = []
                
                for pos in issues_positions:
                    # Try to find the opening brace before "issues"
                    start = raw_content.rfind('{', 0, pos)
                    if start == -1:
                        continue
                    
                    # Try to find the matching closing brace (handle nested structures)
                    brace_count = 0
                    end = start
                    for i in range(start, len(raw_content)):
                        if raw_content[i] == '{':
                            brace_count += 1
                        elif raw_content[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end = i + 1
                                break
                    
                    if end > start:
                        try:
                            json_str = raw_content[start:end]
                            parsed = json.loads(json_str)
                            if "issues" in parsed:
                                all_parsed.append((parsed, len(parsed.get("issues", []))))
                                logger.debug(f"Found JSON object at position {start}-{end} with {len(parsed.get('issues', []))} issues")
                        except json.JSONDecodeError:
                            continue
                
                if all_parsed:
                    # Sort by number of issues (descending), prefer non-empty
                    all_parsed.sort(key=lambda x: x[1], reverse=True)
                    result = all_parsed[0][0]  # Take the one with most issues
                    logger.info(f"Successfully extracted JSON with {len(result.get('issues', []))} issues (found {len(all_parsed)} JSON objects, used the one with most issues)")
                else:
                    # Fallback: Try simple regex pattern
                    json_match = re.search(r'\{[^}]*"issues"[^}]*\}', raw_content, re.DOTALL)
                    if json_match:
                        try:
                            json_str = json_match.group()
                            result = json.loads(json_str)
                            logger.info("Successfully extracted JSON using fallback regex")
                        except json.JSONDecodeError:
                            logger.error("No valid JSON pattern found in response")
                            logger.error(f"Full response (first 2000 chars): {raw_content[:2000]}")
                            result = {"issues": [], "error": f"JSON parse error: No valid JSON found in response"}
                    else:
                        logger.error("No JSON pattern found in response")
                        logger.error(f"Full response (first 2000 chars): {raw_content[:2000]}")
                        result = {"issues": [], "error": f"JSON parse error: No valid JSON found in response"}
            
            # Handle case where model returns summary format instead of issues array
            if "issues" not in result and ("bugs" in result or "security_issues" in result or "performance_issues" in result):
                logger.warning("Model returned summary format instead of issues array. Attempting to request detailed issues...")
                # The model returned a summary - we need to ask it again with a more explicit prompt
                # For now, log this and return empty issues
                logger.error(f"Model returned unexpected format: {result}")
                logger.error("This suggests the model may not be properly fine-tuned or needs a more explicit prompt")
                result = {"issues": [], "error": "Model returned summary format instead of detailed issues array"}
            
            issues_count = len(result.get("issues", []))
            logger.info(f"LLM returned {issues_count} issues")
            
            if issues_count > 0:
                issue_types = [i.get("type", "Unknown") for i in result.get("issues", [])]
                severities = [i.get("severity", "Unknown") for i in result.get("issues", [])]
                logger.info(f"Issue types: {issue_types}")
                logger.info(f"Severities: {severities}")
            else:
                logger.warning("LLM returned NO ISSUES - this might indicate a problem with the model or prompt")
                logger.warning(f"Full result: {result}")
            
            if "error" in result:
                logger.error(f"LLM returned error in result: {result.get('error')}")
            
            # Always add debug info to result (even if parsing succeeded)
            result["_debug"] = debug_info
            
            return result
        except Exception as e:
            logger.error(f"LLM Error: {e}", exc_info=True)
            # Include debug info even on error
            error_result = {"issues": [], "error": str(e), "_debug": {
                "raw_response": "",
                "response_length": 0,
                "has_json": False
            }}
            return error_result