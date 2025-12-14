# 🚀 Render Deployment Checklist

## Pre-Deployment

- [ ] Code is pushed to GitHub repository
- [ ] All environment variables are ready:
  - [ ] `GITHUB_TOKEN` (GitHub PAT with `repo` scope)
  - [ ] `GITHUB_WEBHOOK_SECRET` (random secret string)
  - [ ] `PINECONE_API_KEY` (your Pinecone API key)
  - [ ] `PINECONE_INDEX_NAME` (your Pinecone index name)

## Deployment Steps

1. [ ] **Create Render Account**
   - Sign up at https://render.com
   - Connect GitHub account

2. [ ] **Create Web Service**
   - Click "New +" → "Web Service"
   - Select your repository
   - Configure:
     - Name: `codeguard-api`
     - Environment: `Python 3`
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `uvicorn api:app --host 0.0.0.0 --port $PORT`

3. [ ] **Add Environment Variables**
   - Add all 4 environment variables in Render dashboard
   - Save each one

4. [ ] **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (2-5 minutes)
   - Copy your Render URL (e.g., `https://codeguard-api.onrender.com`)

5. [ ] **Update GitHub Webhook**
   - Go to GitHub repo → Settings → Webhooks
   - Edit existing webhook
   - Update Payload URL to: `https://your-render-url.onrender.com/webhook/github`
   - Keep the same Secret
   - Save

6. [ ] **Test**
   - Create a test PR
   - Check Render logs
   - Verify CodeGuard Bot comment appears

## Post-Deployment

- [ ] Monitor logs for any errors
- [ ] Test with multiple PRs
- [ ] (Optional) Set up cron job to keep service alive (free tier)

## Troubleshooting

- **Build fails**: Check logs, verify `requirements.txt` is complete
- **Webhook not working**: Verify URL and secret match
- **Service slow**: Free tier spins down after 15 min inactivity

---

**Status**: ⬜ Not Started | 🟡 In Progress | ✅ Complete

