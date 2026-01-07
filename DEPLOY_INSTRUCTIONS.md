# 🚀 DEPLOY YOUR RHI PLATFORM - STEP BY STEP

Your code is ready and pushed to GitHub: https://github.com/caseyglarkin2-png/RHI

## Option 1: Railway (EASIEST - Handles Both Services)

### Step-by-Step:

1. **Go to Railway**
   - Visit: https://railway.app
   - Click "Start a New Project"
   - Login with GitHub

2. **Deploy from GitHub**
   - Select "Deploy from GitHub repo"
   - Choose `caseyglarkin2-png/RHI`
   - Railway will auto-detect Docker Compose

3. **Railway creates 2 services automatically:**
   - ✅ `api` (backend - FastAPI)
   - ✅ `web` (frontend - Next.js)

4. **Configure Environment Variables**

   **For the `api` service (backend):**
   - Click on `api` service
   - Go to "Variables" tab
   - Add: `RHI_BASELINE_YEARS` = `5`
   - Add: `RHI_FRONTEND_ORIGIN` = `https://<your-web-service>.railway.app`
     (Get this URL from the web service after it deploys)

   **For the `web` service (frontend):**
   - Click on `web` service
   - Go to "Variables" tab
   - Add: `NEXT_PUBLIC_API_BASE_URL` = `https://<your-api-service>.railway.app/api/v1`
     (Get this URL from the api service)

5. **Generate Public URLs**
   - Click on each service
   - Go to "Settings" → "Networking"
   - Click "Generate Domain"
   - Copy these URLs for the env vars above

6. **Redeploy with Correct URLs**
   - After setting env vars, click "Deploy" on both services
   - Wait 2-3 minutes for build

7. **Access Your Dashboard**
   - Frontend: `https://rhi-web-production.railway.app` (your URL)
   - Backend: `https://rhi-api-production.railway.app/api/v1/health`
   - API Docs: `https://rhi-api-production.railway.app/docs`

**Cost:** Free tier includes $5 credit/month (enough for testing)

---

## Option 2: Render (Also Free Tier Available)

### Backend First:

1. Go to https://render.com
2. New → Web Service
3. Connect GitHub: `caseyglarkin2-png/RHI`
4. Settings:
   - **Name:** `rhi-backend`
   - **Root Directory:** `backend`
   - **Environment:** Docker
   - **Dockerfile Path:** `backend/Dockerfile`
   - Click "Advanced" → Add env vars:
     - `RHI_BASELINE_YEARS` = `5`
     - `RHI_FRONTEND_ORIGIN` = `https://rhi-frontend.onrender.com` (update after frontend deploys)
5. Click "Create Web Service"
6. Wait for deploy (~3-5 min)
7. **Copy the URL:** `https://rhi-backend.onrender.com`

### Frontend Second:

1. New → Web Service
2. Same repo: `caseyglarkin2-png/RHI`
3. Settings:
   - **Name:** `rhi-frontend`
   - **Root Directory:** `frontend`
   - **Environment:** Docker
   - **Dockerfile Path:** `frontend/Dockerfile`
   - Add env var:
     - `NEXT_PUBLIC_API_BASE_URL` = `https://rhi-backend.onrender.com/api/v1`
4. Create & wait for deploy

### Update Backend CORS:

1. Go back to backend service
2. Environment → Edit `RHI_FRONTEND_ORIGIN`
3. Set to: `https://rhi-frontend.onrender.com`
4. Manual Deploy → Deploy latest commit

**Access:** Visit `https://rhi-frontend.onrender.com`

---

## Option 3: Local Docker (Testing)

```bash
cd /workspaces/RHI
docker compose up --build
```

Then visit: http://localhost:3000

---

## ⚠️ Important Notes

1. **First deploy takes 5-10 minutes** (building Docker images)
2. **Free tiers sleep after inactivity** - first request may be slow
3. **CORS must match exactly** - backend needs frontend's exact URL
4. **Check logs** if something fails - Railway/Render show build logs

---

## 🧪 Testing After Deployment

```bash
# Test backend health
curl https://your-backend-url.railway.app/api/v1/health

# Test RHI endpoint
curl https://your-backend-url.railway.app/api/v1/rhi/latest

# Check if frontend loads
open https://your-frontend-url.railway.app
```

---

## 🆘 Troubleshooting

**Frontend shows "UI hit turbulence":**
- Check `NEXT_PUBLIC_API_BASE_URL` env var is set correctly
- Verify backend is running: visit `/api/v1/health`
- Check browser console for CORS errors

**Backend CORS error:**
- Update `RHI_FRONTEND_ORIGIN` to match frontend URL exactly
- Include `https://` prefix
- Redeploy backend after changing

**Build fails:**
- Check Railway/Render logs for errors
- Verify Dockerfile paths are correct
- Try manual deploy

---

## 📊 What You'll See

Once deployed, your dashboard will show:
- **Headline RHI Score** (~77.7/100 with mock data)
- **Component Radar Chart** (Trucking, Ocean, Air, Rail, Macro)
- **Driver Decomposition** (what moved the index today vs yesterday)
- **Auto-refresh** every 60 seconds

---

## Next: Replace Mock Data

See [README_NEW.md](README_NEW.md) for instructions on connecting:
- EIA API (diesel/jet fuel prices)
- FRED (PMI, economic data)
- Freightos (ocean rates)
- ATA/AAR (trucking/rail data)

Your platform is production-ready - just swap the mock store for real APIs! 🚀
