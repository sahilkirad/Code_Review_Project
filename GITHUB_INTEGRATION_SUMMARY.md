# GitHub CI/CD Integration - Phase 1 MVP

## ✅ What Was Built

### 1. **GitHub Integration Module** (`app/core/github/`)
   - **webhook.py**: Webhook signature validation and payload parsing
   - **client.py**: GitHub API client with rate limiting
   - **analyzer.py**: PR analysis orchestrator
   - **formatter.py**: Issues → Markdown comment formatter
   - **models.py**: Pydantic models for type safety

### 2. **Webhook Endpoint** (`/webhook/github`)
   - Validates GitHub webhook signatures
   - Parses pull request events
   - Queues background tasks (async)
   - Returns 200 OK immediately (<1s)

### 3. **Background Processing**
   - Uses FastAPI BackgroundTasks
   - Fetches PR files from GitHub
   - Analyzes Python files using existing CodeGuard workflow
   - Posts formatted comments back to PR

### 4. **Features Implemented**
   - ✅ Webhook signature verification (security)
   - ✅ Async background processing (handles GitHub's 10s timeout)
   - ✅ Python file filtering
   - ✅ File limit (max 10 files per PR)
   - ✅ Idempotency (won't re-analyze same commit)
   - ✅ Rate limiting (500ms between GitHub API calls)
   - ✅ Comment management (updates existing comments)
   - ✅ Error handling and logging

## 📁 File Structure

```
app/
  core/
    github/
      __init__.py
      webhook.py          # Signature validation
      client.py           # GitHub API wrapper
      analyzer.py         # PR analysis orchestrator
      formatter.py        # Markdown formatter
      models.py           # Data models
api.py                    # Webhook endpoint added
requirements.txt          # Updated with PyGithub
GITHUB_SETUP.md          # Setup instructions
test_github_integration.py # Test script
```

## 🚀 How to Use

### Step 1: Set Environment Variables
```bash
# Create .env file or set in your shell
export GITHUB_TOKEN=ghp_your_token_here
export GITHUB_WEBHOOK_SECRET=your_secret_here
```

### Step 2: Start Ngrok
```bash
ngrok http 8000
# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

### Step 3: Configure GitHub Webhook
1. Go to your repo → Settings → Webhooks → Add webhook
2. Payload URL: `https://your-ngrok-url.ngrok.io/webhook/github`
3. Content type: `application/json`
4. Secret: Your `GITHUB_WEBHOOK_SECRET`
5. Events: Select "Pull requests"
6. Save

### Step 4: Start API
```bash
python api.py
```

### Step 5: Test
1. Create a PR with Python files
2. Wait 30-60 seconds
3. Check PR comments for CodeGuard Bot 🛡️

## 🔍 How It Works

```
Developer opens PR
    ↓
GitHub sends webhook → /webhook/github
    ↓
Validate signature → Parse payload → Queue background task
    ↓
Return 200 OK (<1s) ✅
    ↓
[Background Task]
    ↓
Fetch PR files → Filter .py files → Analyze each file
    ↓
Format results → Post comment to PR
```

## 📊 Comment Format

The bot posts comments like:

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

## ⚙️ Configuration

Edit `app/core/github/analyzer.py` to adjust:
- `max_files`: Maximum files to analyze per PR (default: 10)
- `processed_commits`: Idempotency cache (in-memory, resets on restart)

## 🐛 Troubleshooting

### Webhook not working
- Check ngrok is running: http://localhost:4040
- Verify webhook URL in GitHub matches ngrok URL
- Check API logs for errors

### Signature verification fails
- Ensure `GITHUB_WEBHOOK_SECRET` matches GitHub webhook secret
- Check environment variables are loaded

### No comments posted
- Verify `GITHUB_TOKEN` has `repo` scope
- Check PR is still open (won't post on closed PRs)
- Review API logs for analysis errors

## 🔒 Security

- ✅ Webhook signature verification (HMAC SHA256)
- ✅ Environment variable for secrets
- ✅ Rate limiting to prevent abuse
- ✅ Idempotency to prevent duplicate processing

## 📈 Next Steps (Future Phases)

- [ ] Move to Celery + Redis for production scaling
- [ ] Add Redis for persistent idempotency
- [ ] Add monitoring and metrics
- [ ] Support for blocking merges (requires GitHub App)
- [ ] Multi-repository support
- [ ] Configurable file limits per repo

