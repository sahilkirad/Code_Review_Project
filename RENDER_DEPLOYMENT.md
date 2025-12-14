# Deploy CodeGuard to Render

This guide will help you deploy the CodeGuard API to Render, eliminating the need for ngrok.

## Prerequisites

1. **Render Account**
   - Sign up at https://render.com (free tier available)
   - Connect your GitHub account

2. **Environment Variables Ready**
   - `GITHUB_TOKEN`: Your GitHub Personal Access Token
   - `GITHUB_WEBHOOK_SECRET`: Random secret string (same as in `.env`)
   - `PINECONE_API_KEY`: Your Pinecone API key
   - `PINECONE_INDEX_NAME`: Your Pinecone index name

## Step-by-Step Deployment

### Step 1: Push Code to GitHub

Make sure your code is pushed to a GitHub repository:

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### Step 2: Create New Web Service on Render

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository (if not already connected)
4. Select your repository
5. Configure the service:
   - **Name**: `codeguard-api` (or any name you prefer)
   - **Environment**: `Python 3`
   - **Python Version**: `3.10.0` (set in Environment Variables or use `runtime.txt`)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free (or choose a paid plan)

### Step 3: Configure Environment Variables

In the Render dashboard, go to **Environment** section and add:

```
GITHUB_TOKEN=ghp_your_token_here
GITHUB_WEBHOOK_SECRET=your_secret_here
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=your_index_name
```

**Important**: 
- Click "Save Changes" after adding each variable
- Values are hidden for security (you can't see them after saving)

### Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will:
   - Clone your repository
   - Install dependencies
   - Start your API
3. Wait 2-5 minutes for deployment to complete
4. Your API will be available at: `https://your-service-name.onrender.com`

### Step 5: Update GitHub Webhook

1. Go to your GitHub repository
2. **Settings** → **Webhooks** → Edit your existing webhook
3. Update **Payload URL** to: `https://your-service-name.onrender.com/webhook/github`
4. Keep the same **Secret** (your `GITHUB_WEBHOOK_SECRET`)
5. Click **"Update webhook"**

### Step 6: Test

1. Create a test PR in your repository
2. Check Render logs: **Dashboard** → **Your Service** → **Logs**
3. You should see:
   ```
   INFO: Webhook received: PR #X (opened) in username/repo
   INFO: Background task started for PR #X
   ```
4. Check the PR for CodeGuard Bot comment 🛡️

## Important Notes

### Free Tier Limitations
- **Spins down after 15 minutes of inactivity**
- First request after spin-down takes ~30 seconds (cold start)
- **Solution**: Use a paid plan ($7/month) for always-on service

### Keep Service Alive (Free Tier)
- Use a service like https://cron-job.org to ping your API every 10 minutes
- Ping URL: `https://your-service-name.onrender.com/`
- This prevents automatic spin-down

### CORS Configuration
The API currently allows `http://localhost:3000` for local frontend development.
If you deploy the frontend, update CORS in `api.py` to include your frontend URL.

### Logs
- View real-time logs in Render dashboard
- Logs are retained for 7 days (free tier) or 30 days (paid)

## Troubleshooting

### Build Fails
- Check **Logs** tab for error messages
- Common issues:
  - Missing dependencies in `requirements.txt`
  - Python version mismatch
  - Import errors

### Webhook Not Working
- Verify webhook URL in GitHub matches Render URL
- Check `GITHUB_WEBHOOK_SECRET` matches in both places
- Check Render logs for signature verification errors

### Service Not Starting
- Check **Logs** for startup errors
- Verify all environment variables are set
- Ensure `api.py` is in the root directory

### Slow Response Times
- Free tier has limited resources
- First request after spin-down is slow (cold start)
- Consider upgrading to paid plan for better performance

## Next Steps

After successful deployment:
1. ✅ Update GitHub webhook URL
2. ✅ Test with a PR
3. ✅ Monitor logs for any issues
4. ✅ (Optional) Set up cron job to keep service alive

---

**Congratulations!** 🎉 Your CodeGuard API is now deployed and accessible without ngrok!

