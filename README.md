# Fantasy Football Report Generator - Web App

A web application that generates comprehensive historical PDF reports for Yahoo Fantasy Football leagues.

## Features

- 🔐 Secure Yahoo OAuth authentication
- 📊 Automatic league history discovery
- 📈 Comprehensive statistics and analytics
- 📥 Professional PDF report generation
- 🌐 Works on any device with a browser

## Quick Start (Local Development)

### 1. Clone and Setup

```bash
cd E:\FantasyFootballAutomation\web

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Configure Yahoo OAuth

1. Go to [Yahoo Developer Portal](https://developer.yahoo.com/apps/)
2. Click "Create an App"
3. Fill in:
   - **Application Name**: Fantasy Report Generator
   - **Application Type**: Installed Application
   - **Redirect URI(s)**: `http://localhost:8000/auth/callback`
   - **API Permissions**: Fantasy Sports (Read)
4. Click "Create App"
5. Copy your Client ID and Client Secret

### 3. Create Environment File

```bash
# Copy example env file
copy .env.example .env

# Edit .env with your credentials
```

Edit `.env`:
```
YAHOO_CLIENT_ID=your_client_id_here
YAHOO_CLIENT_SECRET=your_client_secret_here
YAHOO_REDIRECT_URI=http://localhost:8000/auth/callback
SECRET_KEY=generate-a-random-string-here
```

### 4. Run the App

```bash
cd backend
python main.py
```

Open http://localhost:8000 in your browser!

---

## Deployment Options

### Option A: Railway (Recommended - Easiest)

1. **Fork/Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/fantasy-report-generator.git
   git push -u origin main
   ```

2. **Deploy on Railway**
   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Add environment variables:
     - `YAHOO_CLIENT_ID`
     - `YAHOO_CLIENT_SECRET`
     - `YAHOO_REDIRECT_URI` = `https://YOUR_APP.railway.app/auth/callback`
     - `SECRET_KEY`
   - Railway will auto-deploy!

3. **Update Yahoo App**
   - Go back to Yahoo Developer Portal
   - Add your Railway URL to Redirect URIs:
     `https://YOUR_APP.railway.app/auth/callback`

### Option B: Render

1. Push to GitHub (same as above)

2. **Deploy on Render**
   - Go to [render.com](https://render.com)
   - Click "New" → "Web Service"
   - Connect your GitHub repo
   - Configure:
     - **Build Command**: `pip install -r backend/requirements.txt`
     - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Add environment variables

### Option C: Docker (Self-hosted)

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t fantasy-report .
docker run -p 8000:8000 --env-file .env fantasy-report
```

### Option D: DigitalOcean App Platform

1. Push to GitHub
2. Go to DigitalOcean → Apps → Create App
3. Connect GitHub repo
4. Configure as Python app
5. Add environment variables
6. Deploy!

---

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `YAHOO_CLIENT_ID` | Yahoo OAuth Client ID | Yes |
| `YAHOO_CLIENT_SECRET` | Yahoo OAuth Client Secret | Yes |
| `YAHOO_REDIRECT_URI` | OAuth callback URL | Yes |
| `SECRET_KEY` | Random string for sessions | Yes |
| `APP_URL` | Your app's public URL | No |
| `REPORTS_DIR` | Directory for generated reports | No |
| `MAX_REPORT_AGE_HOURS` | Auto-delete reports after N hours | No |

### Yahoo OAuth Setup

When creating your Yahoo App:

1. **Application Type**: Choose "Installed Application"
2. **Redirect URI**: Must match `YAHOO_REDIRECT_URI` exactly
   - Local: `http://localhost:8000/auth/callback`
   - Production: `https://yourdomain.com/auth/callback`
3. **API Permissions**: Select "Fantasy Sports" with Read access

---

## Project Structure

```
web/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── auth.py              # Yahoo OAuth handling
│   ├── yahoo_api.py         # Yahoo Fantasy API client
│   ├── report_service.py    # PDF report generation
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── index.html           # Main HTML page
│   ├── styles.css           # Styles
│   └── app.js               # Frontend JavaScript
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Troubleshooting

### "Invalid redirect URI"
- Make sure your `YAHOO_REDIRECT_URI` exactly matches what's in your Yahoo App settings
- Include the full URL with protocol (`http://` or `https://`)

### "Authentication failed"
- Check that your Client ID and Secret are correct
- Make sure your Yahoo App has Fantasy Sports permissions

### Report generation is slow
- The app needs to fetch data from Yahoo for each season
- A 10-year league history may take 1-2 minutes

### PDF doesn't download
- Check that the `reports/` directory exists and is writable
- Check server logs for errors

---

## License

MIT License - Feel free to use, modify, and distribute!

---

Made with ❤️ for Fantasy Football enthusiasts
