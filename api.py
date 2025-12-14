# D:\Code Review\api.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
import json
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.core.graph import GraphState
from app.core.github.webhook import verify_webhook_signature, parse_webhook_payload
from app.core.github.analyzer import PRAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CodeGuard API")

# CORS configuration - allow frontend from environment variable or default to localhost
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
allowed_origins = [frontend_url] if frontend_url else ["http://localhost:3000"]
logger.info(f"CORS configured for origins: {allowed_origins}")

# Allow the Next.js frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event: Validate critical environment variables
@app.on_event("startup")
async def startup_event():
    """Validate environment variables on startup."""
    logger.info("🚀 CodeGuard API starting up...")
    
    # Check critical variables (warn but don't fail)
    critical_vars = {
        "PINECONE_API_KEY": "Pinecone integration",
        "PINECONE_INDEX_NAME": "Pinecone integration",
    }
    
    missing = []
    for var, feature in critical_vars.items():
        if not os.getenv(var):
            missing.append(f"{var} ({feature})")
            logger.warning(f"⚠️  {var} not set - {feature} will not work")
    
    if missing:
        logger.warning(f"⚠️  Missing environment variables: {', '.join(missing)}")
    else:
        logger.info("✅ All critical environment variables are set")
    
    # GitHub integration is optional (only needed for webhooks)
    if not os.getenv("GITHUB_TOKEN"):
        logger.info("ℹ️  GITHUB_TOKEN not set - GitHub webhook integration disabled")
    else:
        logger.info("✅ GitHub integration enabled")
    
    logger.info("✅ CodeGuard API ready!")

# Initialize the Brain once
workflow = GraphState()

# Initialize GitHub PR Analyzer (lazy initialization to handle missing token)
pr_analyzer = None

def get_pr_analyzer():
    """Lazy initialization of PR analyzer"""
    global pr_analyzer
    if pr_analyzer is None:
        try:
            pr_analyzer = PRAnalyzer()
            logger.info("GitHub PR Analyzer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PR Analyzer: {e}")
            logger.error("Make sure GITHUB_TOKEN is set in environment variables")
            raise
    return pr_analyzer

@app.get("/")
@app.head("/")  # Render uses HEAD for health checks
def health_check():
    """Health check endpoint for Render and general monitoring."""
    return {"status": "CodeGuard is online"}

@app.post("/analyze")
async def analyze_code(file: UploadFile = File(...)):
    """
    Receives a file, saves it temp, runs the Agent, and returns the Report.
    """
    temp_filename = None
    try:
        # 1. Save the uploaded file temporarily
        temp_filename = f"temp_{file.filename}"
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Run the Veritas Workflow
        # The workflow expects a dict with "file_path"
        result = workflow.run_workflow({"file_path": temp_filename})
        
        # 3. Transform result to match frontend expectations
        # Get debug info from workflow state if available
        workflow_debug = result.get("_llm_debug", {})
        
        # Log debug info for troubleshooting
        if workflow_debug:
            print(f"DEBUG: Found LLM debug info - length: {workflow_debug.get('response_length', 0)}, has_json: {workflow_debug.get('has_json', False)}")
        else:
            print(f"DEBUG: No LLM debug info found in result. Available keys: {list(result.keys())}")
        
        return {
            "report": {
                "issues": result.get("review_issues", []),
                "final_report": result.get("final_report", "")
            },
            "debug": {
                "llm_raw_response": workflow_debug.get("raw_response", "") if workflow_debug else "",
                "llm_response_length": workflow_debug.get("response_length", 0) if workflow_debug else 0,
                "llm_has_json": workflow_debug.get("has_json", False) if workflow_debug else False,
                "llm_error": result.get("review_issues", [{}])[0].get("error", "") if result.get("review_issues") else ""
            }
        }

    except Exception as e:
        import traceback
        error_detail = str(e)
        traceback_str = traceback.format_exc()
        print(f"ERROR in /analyze: {error_detail}")
        print(f"Traceback: {traceback_str}")
        raise HTTPException(status_code=500, detail=error_detail)
    finally:
        # 4. Clean up (delete the temp file) - always runs
        if temp_filename and os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception as cleanup_error:
                print(f"Warning: Could not delete temp file {temp_filename}: {cleanup_error}")

def analyze_pr_background(repo_full_name: str, pr_number: int, commit_sha: str):
    """
    Background task to analyze a pull request.
    This runs asynchronously after the webhook returns 200 OK.
    """
    logger.info(f"Background task started for PR #{pr_number} in {repo_full_name}")
    try:
        analyzer = get_pr_analyzer()
        success = analyzer.analyze_pr(repo_full_name, pr_number, commit_sha)
        if success:
            logger.info(f"Background analysis completed successfully for PR #{pr_number}")
        else:
            logger.warning(f"Background analysis failed for PR #{pr_number}")
    except Exception as e:
        logger.error(f"Error in background task for PR #{pr_number}: {e}", exc_info=True)

@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256")
):
    """
    GitHub webhook endpoint for pull request events.
    Validates signature, parses payload, and queues background analysis.
    
    Returns 200 OK immediately to satisfy GitHub's 10s timeout requirement.
    """
    try:
        # Read raw body for signature verification (must be done before parsing JSON)
        body_bytes = await request.body()
        
        # Verify webhook signature
        if not verify_webhook_signature(body_bytes, x_hub_signature_256):
            logger.warning("Webhook signature verification failed")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse JSON payload (body_bytes is already consumed, so parse from bytes)
        import json
        payload = json.loads(body_bytes.decode('utf-8'))
        webhook_data = parse_webhook_payload(payload)
        
        if not webhook_data:
            # Not a pull_request event we care about, return 200 anyway
            return {"status": "ignored", "message": "Event not processed"}
        
        # Extract PR information
        repo_full_name = webhook_data.repository.full_name
        pr_number = webhook_data.pull_request.number
        commit_sha = webhook_data.pull_request.head.sha
        
        logger.info(f"Webhook received: PR #{pr_number} ({webhook_data.action}) in {repo_full_name}")
        
        # Check if GitHub token is available before queuing
        if not os.getenv("GITHUB_TOKEN"):
            logger.warning("GITHUB_TOKEN not set - cannot process PR analysis")
            return {
                "status": "error",
                "message": "GitHub integration not configured (GITHUB_TOKEN missing)"
            }
        
        # Queue background task for analysis
        background_tasks.add_task(
            analyze_pr_background,
            repo_full_name,
            pr_number,
            commit_sha
        )
        
        # Return immediately (GitHub expects response within 10s)
        return {
            "status": "accepted",
            "message": f"PR #{pr_number} queued for analysis",
            "repo": repo_full_name,
            "pr_number": pr_number
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        # Still return 200 to prevent GitHub from retrying excessively
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("--- 🚀 CodeGuard API STARTING ON PORT 8000 ---")
    uvicorn.run(app, host="0.0.0.0", port=8000)