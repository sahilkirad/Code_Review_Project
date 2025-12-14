"""
Format analysis results as GitHub Markdown comments
"""
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class CommentFormatter:
    """
    Formats CodeGuard analysis results into GitHub Markdown comments.
    """
    
    BOT_NAME = "CodeGuard Bot"
    BOT_ICON = "🛡️"
    
    @staticmethod
    def format_issues_table(issues: List[Dict[str, Any]]) -> str:
        """
        Format issues as a Markdown table.
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Markdown table string
        """
        if not issues:
            return ""
        
        # Sort by severity (High first)
        severity_order = {"High": 0, "Medium": 1, "Low": 2}
        sorted_issues = sorted(
            issues,
            key=lambda x: (severity_order.get(x.get("severity", "Low"), 2), x.get("type", ""))
        )
        
        table_rows = []
        for issue in sorted_issues:
            severity = issue.get("severity", "Unknown")
            issue_type = issue.get("type", "Unknown")
            explanation = issue.get("explanation", "No explanation")
            suggested_fix = issue.get("suggested_fix", "No fix provided")
            
            # Truncate long explanations
            if len(explanation) > 100:
                explanation = explanation[:97] + "..."
            if len(suggested_fix) > 150:
                suggested_fix = suggested_fix[:147] + "..."
            
            # Severity emoji
            severity_emoji = {
                "High": "🔴",
                "Medium": "🟡",
                "Low": "🔵"
            }.get(severity, "⚪")
            
            table_rows.append(
                f"| {severity_emoji} {severity} | `{issue_type}` | {explanation} | {suggested_fix} |"
            )
        
        table = "\n".join([
            "| Severity | Type | Issue | Suggested Fix |",
            "|:---|:---|:---|:---|"
        ] + table_rows)
        
        return table
    
    @staticmethod
    def format_file_section(filename: str, issues: List[Dict[str, Any]]) -> str:
        """
        Format issues for a specific file.
        
        Args:
            filename: File path
            issues: List of issues for this file
            
        Returns:
            Markdown section string
        """
        if not issues:
            return ""
        
        table = CommentFormatter.format_issues_table(issues)
        
        return f"""
#### `{filename}` ({len(issues)} issue{'s' if len(issues) != 1 else ''})

{table}
"""
    
    @classmethod
    def format_pr_comment(
        cls,
        files_analyzed: List[Dict[str, Any]],
        total_issues: int,
        high_count: int,
        medium_count: int,
        low_count: int
    ) -> str:
        """
        Format complete PR analysis comment.
        
        Args:
            files_analyzed: List of dicts with 'filename' and 'issues'
            total_issues: Total number of issues found
            high_count: Number of high severity issues
            medium_count: Number of medium severity issues
            low_count: Number of low severity issues
            
        Returns:
            Complete Markdown comment
        """
        header = f"## {cls.BOT_ICON} {cls.BOT_NAME} Analysis Report\n\n"
        
        # Summary
        summary = f"**Analyzed:** {len(files_analyzed)} file{'s' if len(files_analyzed) != 1 else ''} | **Found:** {total_issues} issue{'s' if total_issues != 1 else ''}\n\n"
        
        if total_issues == 0:
            return header + summary + "✅ **No issues detected!** Code looks clean.\n"
        
        # Severity breakdown
        severity_section = "### Summary\n"
        if high_count > 0:
            severity_section += f"- 🔴 **High:** {high_count} issue{'s' if high_count != 1 else ''}\n"
        if medium_count > 0:
            severity_section += f"- 🟡 **Medium:** {medium_count} issue{'s' if medium_count != 1 else ''}\n"
        if low_count > 0:
            severity_section += f"- 🔵 **Low:** {low_count} issue{'s' if low_count != 1 else ''}\n"
        severity_section += "\n---\n\n"
        
        # Issues by file
        files_section = "### Issues by File\n\n"
        for file_data in files_analyzed:
            filename = file_data.get("filename", "unknown")
            issues = file_data.get("issues", [])
            if issues:
                files_section += cls.format_file_section(filename, issues)
        
        return header + summary + severity_section + files_section

