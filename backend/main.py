"""Fantasy Football Report Generator - Web API."""

import os
import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from itsdangerous import URLSafeTimedSerializer

from config import get_settings
from auth import yahoo_oauth, YahooTokens
from yahoo_api import YahooFantasyAPI, discover_league_history, NFL_GAME_IDS, get_year_from_game_id
from report_service import ReportGenerator

# Initialize FastAPI app
app = FastAPI(
    title="Fantasy Football Report Generator",
    description="Generate comprehensive PDF reports for your Yahoo Fantasy Football league",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get settings
settings = get_settings()

# Create reports directory
reports_dir = Path(settings.reports_dir)
reports_dir.mkdir(parents=True, exist_ok=True)

# Session serializer for secure cookies
serializer = URLSafeTimedSerializer(settings.secret_key)

# In-memory storage for sessions and job status (use Redis in production)
sessions = {}
jobs = {}


class ReportRequest(BaseModel):
    """Request model for report generation."""
    league_key: str


class JobStatus(BaseModel):
    """Job status model."""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    message: str
    download_url: Optional[str] = None
    error: Optional[str] = None


# Get the absolute path to the project root
# Try multiple methods to find the frontend directory
def find_frontend_dir():
    """Find the frontend directory using multiple methods."""
    # Method 1: Relative to this file
    try:
        backend_dir = Path(__file__).parent.resolve()
        frontend = backend_dir.parent / "frontend"
        if frontend.exists() and (frontend / "index.html").exists():
            return frontend
    except:
        pass

    # Method 2: Check common locations
    common_paths = [
        Path("E:/FantasyFootballAutomation/web/frontend"),
        Path("../frontend").resolve(),
        Path("./frontend").resolve(),
    ]
    for p in common_paths:
        if p.exists() and (p / "index.html").exists():
            return p

    return None

FRONTEND_DIR = find_frontend_dir()
print(f"Frontend directory: {FRONTEND_DIR}")

# Mount static files
if FRONTEND_DIR and FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    print(f"Static files mounted from: {FRONTEND_DIR}")
else:
    print(f"WARNING: Frontend directory not found!")


@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main page."""
    if FRONTEND_DIR:
        html_path = FRONTEND_DIR / "index.html"
        if html_path.exists():
            return HTMLResponse(content=html_path.read_text(encoding='utf-8'))

    return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head><title>Setup Required</title></head>
        <body style="font-family: Arial; padding: 40px; background: #1a1a2e; color: white;">
            <h1>Fantasy Football Report Generator</h1>
            <p>Frontend not found. Searched in: {FRONTEND_DIR}</p>
            <p>Please ensure the frontend files are in the correct location.</p>
        </body>
        </html>
    """)


@app.get("/auth/login")
async def login():
    """Start Yahoo OAuth flow."""
    state = str(uuid.uuid4())
    sessions[state] = {"created": datetime.utcnow().isoformat()}

    auth_url = yahoo_oauth.get_authorization_url(state)
    return RedirectResponse(url=auth_url)


@app.get("/auth/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None):
    """Handle Yahoo OAuth callback."""
    if error:
        return RedirectResponse(url=f"/?error={error}")

    if not code or not state:
        return RedirectResponse(url="/?error=missing_params")

    if state not in sessions:
        return RedirectResponse(url="/?error=invalid_state")

    try:
        # Exchange code for tokens
        tokens = await yahoo_oauth.exchange_code(code)

        # Store tokens in session
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "tokens": tokens.to_dict(),
            "created": datetime.utcnow().isoformat(),
        }

        # Redirect with session cookie
        response = RedirectResponse(url="/?authenticated=true")
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=3600 * 24,  # 24 hours
            samesite="lax",
        )

        # Clean up state
        del sessions[state]

        return response

    except Exception as e:
        print(f"OAuth error: {e}")
        return RedirectResponse(url=f"/?error=auth_failed")


@app.get("/auth/status")
async def auth_status(request: Request):
    """Check authentication status."""
    session_id = request.cookies.get("session_id")

    if not session_id or session_id not in sessions:
        return {"authenticated": False}

    session = sessions[session_id]
    if "tokens" not in session:
        return {"authenticated": False}

    return {"authenticated": True}


@app.post("/auth/logout")
async def logout(request: Request):
    """Log out user."""
    session_id = request.cookies.get("session_id")

    if session_id and session_id in sessions:
        del sessions[session_id]

    response = JSONResponse({"success": True})
    response.delete_cookie("session_id")
    return response


@app.get("/api/leagues")
async def get_leagues(request: Request):
    """Get user's leagues for the current year."""
    session_id = request.cookies.get("session_id")

    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = sessions[session_id]
    tokens = YahooTokens.from_dict(session["tokens"])

    # Refresh if expired
    if tokens.is_expired():
        try:
            tokens = await yahoo_oauth.refresh_tokens(tokens.refresh_token)
            session["tokens"] = tokens.to_dict()
        except Exception as e:
            raise HTTPException(status_code=401, detail="Token refresh failed")

    api = YahooFantasyAPI(tokens)

    # Get leagues for recent years
    all_leagues = []
    print(f"[LEAGUES] Fetching leagues for years: 2025, 2024, 2023")
    for year in [2025, 2024, 2023]:
        try:
            print(f"[LEAGUES] Fetching year {year}...")
            league_ids = await api.get_user_leagues(year)
            print(f"[LEAGUES] Year {year}: found {len(league_ids)} leagues: {league_ids}")
            for lid in league_ids:
                try:
                    settings = await api.get_league_settings(lid)
                    all_leagues.append({
                        "league_key": lid,
                        "name": settings.get("name", "Unknown"),
                        "year": year,
                    })
                    print(f"[LEAGUES] Added league: {settings.get('name', 'Unknown')} ({lid})")
                except Exception as e:
                    print(f"[LEAGUES] Error getting settings for {lid}: {e}")
                    continue
        except Exception as e:
            print(f"[LEAGUES] Error fetching year {year}: {e}")
            continue

    print(f"[LEAGUES] Total leagues found: {len(all_leagues)}")
    return {"leagues": all_leagues}


@app.post("/api/report/generate")
async def generate_report(
    request: Request,
    report_request: ReportRequest,
    background_tasks: BackgroundTasks,
):
    """Start report generation."""
    session_id = request.cookies.get("session_id")

    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = sessions[session_id]
    tokens = YahooTokens.from_dict(session["tokens"])

    # Refresh if expired
    if tokens.is_expired():
        try:
            tokens = await yahoo_oauth.refresh_tokens(tokens.refresh_token)
            session["tokens"] = tokens.to_dict()
        except Exception as e:
            raise HTTPException(status_code=401, detail="Token refresh failed")

    # Create job
    job_id = str(uuid.uuid4())
    jobs[job_id] = JobStatus(
        job_id=job_id,
        status="pending",
        progress=0,
        message="Starting report generation...",
    )

    # Start background task
    background_tasks.add_task(
        generate_report_task,
        job_id,
        report_request.league_key,
        tokens,
    )

    return {"job_id": job_id}


@app.get("/api/report/status/{job_id}")
async def get_job_status(job_id: str):
    """Get report generation status."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return jobs[job_id]


@app.get("/api/report/download/{job_id}")
async def download_report(job_id: str):
    """Download generated report."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Report not ready")

    file_path = reports_dir / f"{job_id}.pdf"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    return FileResponse(
        path=str(file_path),
        filename=f"fantasy_report_{job_id[:8]}.pdf",
        media_type="application/pdf",
    )


async def generate_report_task(job_id: str, league_key: str, tokens: YahooTokens):
    """Background task to generate report."""
    try:
        job = jobs[job_id]
        job.status = "processing"
        job.progress = 5
        job.message = "Connecting to Yahoo Fantasy..."

        api = YahooFantasyAPI(tokens)

        # Discover league history
        job.progress = 10
        job.message = "Discovering league history..."

        league_keys, league_name = await discover_league_history(api, league_key)

        job.progress = 20
        job.message = f"Found {len(league_keys)} seasons for '{league_name}'"

        # Fetch all data
        generator = ReportGenerator(api)
        await generator.fetch_all_data(league_keys, job)

        # Generate PDF
        job.progress = 90
        job.message = "Generating PDF report..."

        output_path = reports_dir / f"{job_id}.pdf"
        await generator.generate_pdf(league_name, output_path)

        job.status = "completed"
        job.progress = 100
        job.message = "Report ready for download!"
        job.download_url = f"/api/report/download/{job_id}"

    except Exception as e:
        print(f"Report generation error: {e}")
        import traceback
        traceback.print_exc()

        job = jobs[job_id]
        job.status = "failed"
        job.error = str(e)
        job.message = f"Error: {str(e)}"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
