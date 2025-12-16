# 🛡️ CodeGuard

> An AI-powered code review system that automatically analyzes pull requests and flags security vulnerabilities, bugs, and code smells using a custom fine-tuned LLM.

[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.124-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 Overview

CodeGuard is an intelligent code review bot that integrates seamlessly into your GitHub workflow. When you open a Pull Request, CodeGuard automatically:

- 🔍 **Analyzes Python code changes** for security vulnerabilities, bugs, and code smells
- 📊 **Posts detailed review comments** with severity ratings and suggested fixes
- 🧠 **Uses RAG (Retrieval Augmented Generation)** to reference similar past issues from a knowledge base
- ⚡ **Runs asynchronously** via GitHub Actions, ensuring no impact on your development workflow

Built with a **custom fine-tuned LLM** specifically trained for code review tasks, CodeGuard provides accurate, actionable feedback that helps maintain code quality and security standards.

---

## ✨ Key Features

### 🤖 Intelligent Analysis
- **Multi-layered Detection**: Combines syntax checking, semantic analysis, and pattern recognition
- **Severity Classification**: Automatically categorizes issues as High, Medium, or Low priority
- **Context-Aware Suggestions**: Provides specific, actionable fixes for each detected issue

### 🔗 GitHub Integration
- **Automatic PR Analysis**: Triggers on PR open, update, or reopen events
- **Rich Markdown Comments**: Beautifully formatted reports with tables and emojis
- **Idempotent Processing**: Prevents duplicate analysis of the same commit
- **Rate-Limited API Calls**: Respects GitHub API limits with intelligent throttling

### 🧬 RAG-Powered Context
- **Vector Database Integration**: Uses Pinecone to store and retrieve similar code patterns
- **Historical Learning**: References past issues to improve detection accuracy
- **Contextual Recommendations**: Suggests fixes based on how similar issues were resolved

### 🚀 Production-Ready
- **GitHub Actions Deployment**: Runs directly in GitHub's infrastructure
- **Model Caching**: Efficiently caches the 940MB fine-tuned model via GitHub Releases
- **Scalable Architecture**: Handles multiple PRs concurrently without performance degradation

---

## 🛠️ Tech Stack

### Core Framework
- **FastAPI**: High-performance async web framework for the API
- **LangGraph**: Orchestrates the multi-step code analysis workflow
- **LangChain**: Integrates LLM calls and RAG retrieval

### AI & Machine Learning
- **Custom Fine-Tuned LLM (Veritas)**: 
  - Base Model: `Qwen2.5-Coder-1.5B-Instruct` (coding-optimized)
  - Training: QLoRA (4-bit quantization) via Unsloth
  - Output: Structured JSON with issue classifications
- **Ollama**: Local LLM inference engine
- **Pinecone**: Vector database for RAG context retrieval
- **Sentence Transformers**: Generates embeddings for semantic search

### Infrastructure & Integration
- **GitHub Actions**: CI/CD pipeline for automated analysis
- **GitHub API**: Fetches PR files and posts comments via PyGithub
- **Python 3.10**: Runtime environment

---

## 🧠 The Custom LLM: Veritas

CodeGuard's intelligence comes from **Veritas**, a custom fine-tuned language model built specifically for code review tasks.

### Training Approach
- **Framework**: Unsloth (2x faster training, 60% less memory)
- **Technique**: QLoRA (4-bit quantization) for efficient fine-tuning
- **Hardware**: Google Colab Free Tier (Tesla T4 GPU)
- **Dataset**: Synthetic "Bad Code vs. Structured Fixes" examples
- **Output Format**: Strict JSON with issue type, severity, location, and suggested fixes

### Why Fine-Tuning?
While general-purpose LLMs can review code, a fine-tuned model offers:
- ✅ **Domain Expertise**: Specialized knowledge of code review patterns
- ✅ **Consistent Output**: Structured JSON format eliminates parsing errors
- ✅ **Efficiency**: Smaller model (1.5B parameters) with faster inference
- ✅ **Cost-Effective**: Runs locally via Ollama, no API costs

---

## ⚙️ How It Works

```
┌─────────────────┐
│  PR Created     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GitHub Actions  │
│   Triggered     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Download Model  │
│ (Cached)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Setup Ollama    │
│ Load Veritas    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ For each .py    │
│ file:           │
│  ├─ Syntax      │
│  ├─ RAG Search  │
│  ├─ LLM Analysis│
│  └─ Format      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Post PR Comment │
│ with Issues     │
└─────────────────┘
```

### Analysis Pipeline

1. **Syntax Validation**: Checks for basic Python syntax errors
2. **RAG Retrieval**: Searches Pinecone for similar code patterns and past issues
3. **LLM Analysis**: Veritas model analyzes the code with retrieved context
4. **Issue Aggregation**: Combines results from all files
5. **Markdown Formatting**: Converts structured JSON to readable GitHub comments
6. **Comment Posting**: Updates or creates PR comments with findings

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- GitHub repository with Actions enabled
- Pinecone account (for RAG functionality)
- GitHub Personal Access Token with `repo` scope

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/CodeGuard.git
   cd CodeGuard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Create .env file
   PINECONE_API_KEY=your_pinecone_key
   PINECONE_INDEX_NAME=your_index_name
   GITHUB_TOKEN=your_github_token
   ```

4. **Configure GitHub Actions**
   - Add secrets to your repository:
     - `PINECONE_API_KEY`
     - `PINECONE_INDEX_NAME`
   - The workflow will automatically download the model from GitHub Releases

5. **Test locally** (optional)
   ```bash
   uvicorn api:app --reload
   ```

### Usage

Once configured, CodeGuard automatically runs on every Pull Request:

1. **Create a PR** with Python file changes
2. **GitHub Actions triggers** the analysis workflow
3. **Wait 30-60 seconds** for analysis to complete
4. **Check PR comments** for CodeGuard's findings

---

## 📊 Example Output

CodeGuard posts comments like this:

```markdown
## 🛡️ CodeGuard Bot Analysis Report

**Analyzed:** 3 files | **Found:** 5 issues

### Summary
- 🔴 **High:** 2 issues
- 🟡 **Medium:** 2 issues
- 🔵 **Low:** 1 issue

---

### Issues by File

#### `app/core/auth.py` (2 issues)

| Severity | Type | Issue | Suggested Fix |
|:---|:---|:---|:---|
| 🔴 High | Security Issue | Hardcoded API key | Use environment variables |
| 🟡 Medium | Bug | Missing error handling | Add try-except block |
```

---

## 🎓 Key Learnings & Architecture Decisions

### Why GitHub Actions?
After experimenting with Ngrok (local) and Render (cloud), GitHub Actions emerged as the optimal solution:
- ✅ **No external dependencies**: Runs in GitHub's infrastructure
- ✅ **Faster execution**: Dedicated runners with better resources
- ✅ **Automatic scaling**: Each PR gets its own runner
- ✅ **Cost-effective**: Free for public repositories

### Why Fine-Tune Instead of Using GPT-4?
- **Cost**: No API costs (runs locally)
- **Speed**: Faster inference with smaller model
- **Consistency**: Structured JSON output eliminates parsing issues
- **Privacy**: Code never leaves your infrastructure

### Why RAG?
RAG enhances the LLM's accuracy by:
- Providing contextual examples from past code reviews
- Learning from historical issue patterns
- Suggesting fixes based on how similar issues were resolved

---

## 🔧 Configuration

### File Limits
- Maximum 10 Python files analyzed per PR (configurable)
- Prevents timeout on large PRs

### Analysis Scope
- Only analyzes `.py` files
- Skips binary files, images, and documentation

### Rate Limiting
- 500ms delay between GitHub API calls
- Respects GitHub's 5000 requests/hour limit

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Qwen Team**: For the excellent base model (Qwen2.5-Coder-1.5B-Instruct)
- **Unsloth**: For making fine-tuning accessible on free-tier hardware
- **Ollama**: For providing an easy-to-use local LLM inference engine
- **Pinecone**: For the vector database infrastructure



