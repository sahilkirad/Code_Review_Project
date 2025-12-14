"""
PR Analysis Orchestrator
Fetches PR files, analyzes them, and aggregates results
"""
import logging
import time
from typing import List, Dict, Any, Optional
from .client import GitHubClient
from .formatter import CommentFormatter
from app.core.graph import GraphState

logger = logging.getLogger(__name__)

class PRAnalyzer:
    """
    Orchestrates analysis of pull requests.
    Fetches files, runs analysis, and formats results.
    """
    
    def __init__(self):
        self.github_client = GitHubClient()
        self.workflow = GraphState()
        self.formatter = CommentFormatter()
        self.max_files = 10  # Limit files per PR to avoid timeout
        self.processed_commits = {}  # Simple in-memory idempotency
    
    def is_already_processed(self, repo: str, pr_number: int, commit_sha: str) -> bool:
        """
        Check if this PR commit has already been processed.
        
        Args:
            repo: Repository full name
            pr_number: Pull request number
            commit_sha: Commit SHA
            
        Returns:
            True if already processed, False otherwise
        """
        key = (repo, pr_number, commit_sha)
        if key in self.processed_commits:
            # Re-process if older than 1 hour (for re-analysis)
            if time.time() - self.processed_commits[key] < 3600:
                logger.info(f"PR #{pr_number} commit {commit_sha[:7]} already processed, skipping")
                return True
        return False
    
    def mark_as_processed(self, repo: str, pr_number: int, commit_sha: str):
        """Mark PR commit as processed"""
        key = (repo, pr_number, commit_sha)
        self.processed_commits[key] = time.time()
    
    def analyze_pr(self, repo_full_name: str, pr_number: int, commit_sha: str) -> bool:
        """
        Analyze a pull request and post results as comment.
        
        Args:
            repo_full_name: Repository full name (e.g., "owner/repo")
            pr_number: Pull request number
            commit_sha: Commit SHA of the PR head
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting analysis for PR #{pr_number} in {repo_full_name}")
            
            # Check idempotency
            if self.is_already_processed(repo_full_name, pr_number, commit_sha):
                return True
            
            # Get PR to check state
            pr = self.github_client.get_pull_request(repo_full_name, pr_number)
            if pr.state != "open":
                logger.info(f"PR #{pr_number} is {pr.state}, skipping analysis")
                return False
            
            # Get changed files
            files = self.github_client.get_pr_files(repo_full_name, pr_number)
            
            if not files:
                logger.info(f"No Python files found in PR #{pr_number}")
                # Post a comment saying no Python files
                comment = f"## {CommentFormatter.BOT_ICON} {CommentFormatter.BOT_NAME}\n\nNo Python files found in this PR. Analysis skipped."
                self.github_client.post_comment(repo_full_name, pr_number, comment)
                return True
            
            # Limit number of files
            if len(files) > self.max_files:
                logger.warning(f"PR has {len(files)} files, limiting to {self.max_files}")
                files = files[:self.max_files]
            
            # Analyze each file
            files_analyzed = []
            total_issues = 0
            high_count = 0
            medium_count = 0
            low_count = 0
            
            for file_info in files:
                logger.info(f"Analyzing file: {file_info.filename}")
                
                # Get file content
                file_content = self.github_client.get_file_content(
                    repo_full_name,
                    file_info.filename,
                    commit_sha
                )
                
                if not file_content:
                    logger.warning(f"Could not fetch content for {file_info.filename}")
                    continue
                
                # Run analysis
                try:
                    result = self.workflow.run_workflow({
                        "code_snippet": file_content,
                        "filename": file_info.filename
                    })
                    
                    issues = result.get("review_issues", [])
                    
                    # Count by severity
                    for issue in issues:
                        severity = issue.get("severity", "Low").lower()
                        if severity == "high":
                            high_count += 1
                        elif severity == "medium":
                            medium_count += 1
                        else:
                            low_count += 1
                    
                    total_issues += len(issues)
                    
                    if issues:
                        files_analyzed.append({
                            "filename": file_info.filename,
                            "issues": issues
                        })
                        logger.info(f"Found {len(issues)} issues in {file_info.filename}")
                    
                except Exception as e:
                    logger.error(f"Error analyzing {file_info.filename}: {e}")
                    continue
            
            # Format and post comment
            comment_body = self.formatter.format_pr_comment(
                files_analyzed,
                total_issues,
                high_count,
                medium_count,
                low_count
            )
            
            success = self.github_client.post_comment(repo_full_name, pr_number, comment_body)
            
            if success:
                self.mark_as_processed(repo_full_name, pr_number, commit_sha)
                logger.info(f"Successfully analyzed and posted comment for PR #{pr_number}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error analyzing PR #{pr_number}: {e}", exc_info=True)
            # Try to post error comment
            try:
                error_comment = f"## {CommentFormatter.BOT_ICON} {CommentFormatter.BOT_NAME}\n\n❌ **Analysis failed:** {str(e)}\n\nPlease check the logs for details."
                self.github_client.post_comment(repo_full_name, pr_number, error_comment)
            except:
                pass
            return False

