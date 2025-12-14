"""
GitHub API Client using PyGithub
Handles fetching PR files and posting comments
"""
import os
import logging
import time
from typing import List, Optional
from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository
from github.IssueComment import IssueComment
from .models import FileInfo

logger = logging.getLogger(__name__)

class GitHubClient:
    """
    Wrapper around PyGithub for GitHub API operations.
    Includes rate limiting and error handling.
    """
    
    def __init__(self):
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable not set")
        
        self.github = Github(token)
        self.last_request_time = 0
        self.min_interval = 0.5  # 500ms between requests to avoid rate limits
        
    def _rate_limit_delay(self):
        """Add delay between requests to respect rate limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
    
    def get_repository(self, repo_full_name: str) -> Repository:
        """Get repository object"""
        self._rate_limit_delay()
        return self.github.get_repo(repo_full_name)
    
    def get_pull_request(self, repo_full_name: str, pr_number: int) -> PullRequest:
        """Get pull request object"""
        repo = self.get_repository(repo_full_name)
        self._rate_limit_delay()
        return repo.get_pull(pr_number)
    
    def get_pr_files(self, repo_full_name: str, pr_number: int) -> List[FileInfo]:
        """
        Get list of files changed in a PR, filtered to Python files only.
        
        Args:
            repo_full_name: Repository full name (e.g., "owner/repo")
            pr_number: Pull request number
            
        Returns:
            List of FileInfo objects for Python files only
        """
        pr = self.get_pull_request(repo_full_name, pr_number)
        self._rate_limit_delay()
        files = pr.get_files()
        
        python_files = []
        for file in files:
            # Only process Python files
            if file.filename.endswith('.py'):
                # Skip deleted files (can't analyze them)
                if file.status == 'removed':
                    continue
                
                python_files.append(FileInfo(
                    filename=file.filename,
                    status=file.status,
                    additions=file.additions,
                    deletions=file.deletions,
                    changes=file.changes,
                    patch=file.patch
                ))
        
        logger.info(f"Found {len(python_files)} Python files in PR #{pr_number}")
        return python_files
    
    def get_file_content(self, repo_full_name: str, file_path: str, ref: str = "main") -> str:
        """
        Get file content from repository.
        
        Args:
            repo_full_name: Repository full name
            file_path: Path to file in repository
            ref: Git reference (branch, commit SHA, etc.)
            
        Returns:
            File content as string
        """
        repo = self.get_repository(repo_full_name)
        self._rate_limit_delay()
        try:
            content = repo.get_contents(file_path, ref=ref)
            if isinstance(content, list):
                # If it's a directory, return empty
                return ""
            return content.decoded_content.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to get file content for {file_path}: {e}")
            return ""
    
    def find_existing_comment(self, repo_full_name: str, pr_number: int, bot_name: str = "CodeGuard Bot") -> Optional[IssueComment]:
        """
        Find existing comment from bot to avoid duplicates.
        
        Args:
            repo_full_name: Repository full name
            pr_number: Pull request number
            bot_name: Name to search for in comments
            
        Returns:
            IssueComment if found, None otherwise
        """
        pr = self.get_pull_request(repo_full_name, pr_number)
        self._rate_limit_delay()
        comments = pr.get_issue_comments()
        
        for comment in comments:
            if bot_name in comment.body:
                return comment
        
        return None
    
    def post_comment(self, repo_full_name: str, pr_number: int, comment_body: str, update_existing: bool = True) -> bool:
        """
        Post comment on pull request. Updates existing comment if found.
        
        Args:
            repo_full_name: Repository full name
            pr_number: Pull request number
            comment_body: Markdown comment body
            update_existing: If True, update existing bot comment instead of creating new one
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pr = self.get_pull_request(repo_full_name, pr_number)
            
            # Check if PR is still open
            if pr.state != "open":
                logger.info(f"PR #{pr_number} is {pr.state}, skipping comment")
                return False
            
            # Try to find existing comment
            if update_existing:
                existing_comment = self.find_existing_comment(repo_full_name, pr_number)
                if existing_comment:
                    self._rate_limit_delay()
                    existing_comment.edit(comment_body)
                    logger.info(f"Updated existing comment on PR #{pr_number}")
                    return True
            
            # Create new comment
            self._rate_limit_delay()
            pr.create_issue_comment(comment_body)
            logger.info(f"Posted new comment on PR #{pr_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to post comment on PR #{pr_number}: {e}")
            return False

