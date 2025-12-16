# GitHub Actions Setup Guide

## Overview

CodeGuard now runs automatically on every Pull Request using GitHub Actions. This eliminates the need for Render webhooks and provides faster, more reliable analysis.

## Prerequisites

1. **GitHub Repository Secrets**
   - `PINECONE_API_KEY`: Your Pinecone API key
   - `PINECONE_INDEX_NAME`: Your Pinecone index name
   - `GITHUB_TOKEN`: Automatically provided by GitHub Actions (no setup needed)

2. **Model Release**
   - Model must be uploaded to GitHub Releases (already done: v1.0.0)

## Setup Steps

### Step 1: Add Repository Secrets

1. Go to your GitHub repository
2. **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Add each secret:
   - **Name**: `PINECONE_API_KEY`
   - **Value**: Your Pinecone API key
   - Click **"Add secret"**
   
   Repeat for:
   - **Name**: `PINECONE_INDEX_NAME`
   - **Value**: Your Pinecone index name

### Step 2: Push Workflow File

The workflow file is already created at `.github/workflows/codeguard.yml`. Just commit and push:

```bash
git add .github/workflows/codeguard.yml
git commit -m "Add GitHub Actions workflow for CodeGuard"
git push origin main
```

### Step 3: Test

1. Create a test PR with Python files
2. The workflow will automatically run
3. Check the **Actions** tab to see progress
4. Results will be posted as a PR comment

## How It Works

1. **Trigger**: PR opened, synchronized, or reopened
2. **Setup**: Python 3.10, dependencies, Ollama
3. **Model**: Downloads from GitHub Release v1.0.0 (cached after first run)
4. **Analysis**: Runs CodeGuard on changed Python files
5. **Comment**: Posts formatted results to PR

## Workflow Features

- ✅ **Automatic**: Runs on every PR
- ✅ **Fast**: Model cached after first download
- ✅ **Reliable**: No spin-down issues
- ✅ **Smart**: Only analyzes changed Python files
- ✅ **Updates**: Updates existing comment instead of spamming

## Performance

- **First run**: ~5-8 minutes (downloads model)
- **Subsequent runs**: ~4-6 minutes (uses cached model)
- **Per file analysis**: ~30-60 seconds

## Troubleshooting

### Workflow not running
- Check if workflow file is in `.github/workflows/`
- Verify it's committed to the default branch (usually `main`)

### Model download fails
- Verify release v1.0.0 exists
- Check release asset name is exactly `veritas_final.gguf`

### Analysis fails
- Check Actions logs for errors
- Verify secrets are set correctly
- Ensure Pinecone API key is valid

### No comment posted
- Check Actions logs for errors
- Verify `GITHUB_TOKEN` permissions (should be automatic)
- Check if PR has Python files changed

## Next Steps

After setup:
1. ✅ Test with a real PR
2. ✅ Monitor Actions logs
3. ✅ Verify comments are posted correctly
4. ✅ (Optional) Add status checks in Phase 2

---

**Your CodeGuard is now running on GitHub Actions!** 🎉

