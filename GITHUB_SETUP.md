# GitHub CI/CD Integration Setup Guide

## Overview
CodeGuard can automatically analyze pull requests on GitHub and post review comments.

## Prerequisites

1. **GitHub Personal Access Token (PAT)**
   - Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Generate new token with `repo` scope (Full control of private repositories)
   - Save the token securely

2. **Webhook Secret**
   - Generate a random secret string (e.g., `openssl rand -hex 32`)
   - This will be used to verify webhook requests from GitHub

3. **Ngrok Account** (for exposing localhost)
   - Sign up at https://ngrok.com
   - Get your authtoken from the dashboard

## Environment Variables

Create a `.env` file in the project root:

```env
GITHUB_TOKEN=ghp_your_personal_access_token_here
GITHUB_WEBHOOK_SECRET=your_random_secret_string_here
```

## Setup Steps

### 1. Install Dependencies
```bash
pip install PyGithub
```

### 2. Start Ngrok Tunnel
```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### 3. Configure GitHub Webhook

**Option A: Using Render (Recommended - No ngrok needed)**
1. Go to your repository on GitHub
2. Settings → Webhooks → Add webhook (or edit existing)
3. **Payload URL**: `https://codeguard-api.onrender.com/webhook/github` (or your Render URL)
4. **Content type**: `application/json`
5. **Secret**: Your `GITHUB_WEBHOOK_SECRET` value
6. **Events**: Select "Pull requests" only
7. Click "Add webhook" or "Update webhook"

**Option B: Using Ngrok (For local development)**
1. Start ngrok: `ngrok http 8000`
2. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)
3. Go to your repository on GitHub
4. Settings → Webhooks → Add webhook
5. **Payload URL**: `https://your-ngrok-url.ngrok.io/webhook/github`
6. **Content type**: `application/json`
7. **Secret**: Your `GITHUB_WEBHOOK_SECRET` value
8. **Events**: Select "Pull requests" only
9. Click "Add webhook"

### 4. Start CodeGuard API
```bash
python api.py
```

The API will start on `http://localhost:8000`

## Testing

1. Create a test repository on GitHub
2. Create a branch and add a Python file with some issues
3. Open a Pull Request
4. Within 30-60 seconds, you should see a comment from "CodeGuard Bot" 🛡️

## How It Works

1. **Developer opens PR** → GitHub sends webhook
2. **Webhook received** → Signature validated → Returns 200 OK immediately
3. **Background task starts** → Fetches PR files → Analyzes each Python file
4. **Results formatted** → Posted as PR comment

## Troubleshooting

### Webhook not receiving requests
- Check ngrok is running and URL is correct
- Verify webhook URL in GitHub settings
- Check ngrok web interface: http://localhost:4040

### Signature verification fails
- Ensure `GITHUB_WEBHOOK_SECRET` matches GitHub webhook secret
- Check environment variables are loaded

### Analysis not posting comments
- Verify `GITHUB_TOKEN` has `repo` scope
- Check API logs for errors
- Ensure PR is still open (won't post on closed PRs)

### Rate limiting
- GitHub API has rate limits (5000 requests/hour)
- CodeGuard includes automatic rate limiting (500ms between requests)

## Notes

- Only Python (`.py`) files are analyzed
- Maximum 10 files per PR (to avoid timeout)
- Comments are updated if bot already commented (no spam)
- Analysis is idempotent (won't re-analyze same commit)

