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
from yahoo_api import YahooFantasyAPI, discover_league_history as yahoo_discover_league_history, NFL_GAME_IDS, get_year_from_game_id
from sleeper_api import SleeperFantasyAPI, SleeperUser, lookup_user as sleeper_lookup_user, discover_league_history as sleeper_discover_league_history
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
    start_year: Optional[int] = None
    end_year: Optional[int] = None


class SleeperConnectRequest(BaseModel):
    """Request model for Sleeper connection."""
    username: str


class SleeperReportRequest(BaseModel):
    """Request model for Sleeper report generation."""
    league_id: str
    start_year: Optional[int] = None
    end_year: Optional[int] = None


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
            "platform": "yahoo",
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
        return {"authenticated": False, "platform": None}

    session = sessions[session_id]
    platform = session.get("platform")

    # Check for Yahoo session
    if platform == "yahoo":
        if "tokens" not in session:
            return {"authenticated": False, "platform": None}
        return {"authenticated": True, "platform": "yahoo"}

    # Check for Sleeper session
    if platform == "sleeper":
        if "sleeper_user" not in session:
            return {"authenticated": False, "platform": None}
        return {
            "authenticated": True,
            "platform": "sleeper",
            "username": session["sleeper_user"].get("username"),
        }

    return {"authenticated": False, "platform": None}


@app.post("/auth/logout")
async def logout(request: Request):
    """Log out user."""
    session_id = request.cookies.get("session_id")

    if session_id and session_id in sessions:
        del sessions[session_id]

    response = JSONResponse({"success": True})
    response.delete_cookie("session_id")
    return response


# =====================
# Sleeper Auth Routes
# =====================

@app.post("/auth/sleeper/connect")
async def sleeper_connect(connect_request: SleeperConnectRequest):
    """Connect to Sleeper via username lookup."""
    username = connect_request.username.strip()

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    try:
        user = await sleeper_lookup_user(username)

        if not user:
            raise HTTPException(status_code=404, detail=f"Sleeper user '{username}' not found")

        # Create session
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "platform": "sleeper",
            "sleeper_user": user.to_dict(),
            "created": datetime.utcnow().isoformat(),
        }

        response = JSONResponse({
            "success": True,
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "display_name": user.display_name,
            }
        })
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=3600 * 24,  # 24 hours
            samesite="lax",
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"Sleeper connect error: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to Sleeper")


@app.get("/api/sleeper/leagues")
async def get_sleeper_leagues(request: Request):
    """Get user's Sleeper leagues."""
    session_id = request.cookies.get("session_id")

    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = sessions[session_id]
    if session.get("platform") != "sleeper" or "sleeper_user" not in session:
        raise HTTPException(status_code=401, detail="Not authenticated with Sleeper")

    user = SleeperUser.from_dict(session["sleeper_user"])
    api = SleeperFantasyAPI(user)

    # Get leagues for recent years
    all_leagues = []
    current_year = datetime.now().year

    for year in range(current_year, current_year - 3, -1):
        try:
            leagues = await api.get_user_leagues(year)
            for league in leagues:
                all_leagues.append({
                    "league_id": league["league_id"],
                    "name": league["name"],
                    "year": year,
                    "total_rosters": league.get("total_rosters", 0),
                })
        except Exception as e:
            print(f"[Sleeper] Error getting leagues for {year}: {e}")
            continue

    return {"leagues": all_leagues}


@app.post("/api/sleeper/report/generate")
async def generate_sleeper_report(
    request: Request,
    report_request: SleeperReportRequest,
    background_tasks: BackgroundTasks,
):
    """Start Sleeper report generation."""
    session_id = request.cookies.get("session_id")

    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = sessions[session_id]
    if session.get("platform") != "sleeper" or "sleeper_user" not in session:
        raise HTTPException(status_code=401, detail="Not authenticated with Sleeper")

    user = SleeperUser.from_dict(session["sleeper_user"])

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
        generate_sleeper_report_task,
        job_id,
        report_request.league_id,
        user,
        report_request.start_year,
        report_request.end_year,
    )

    return {"job_id": job_id}


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
    for year in [2025, 2024, 2023]:
        try:
            leagues = await api.get_user_leagues(year)
            for league in leagues:
                all_leagues.append({
                    "league_key": league["league_key"],
                    "name": league["name"],
                    "year": year,
                })
        except Exception:
            continue

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
        report_request.start_year,
        report_request.end_year,
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


async def generate_report_task(
    job_id: str,
    league_key: str,
    tokens: YahooTokens,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
):
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

        league_keys, league_name = await yahoo_discover_league_history(api, league_key)

        # Filter by year range if specified
        if start_year or end_year:
            filtered_keys = []
            for lk, year in league_keys:
                if start_year and year < start_year:
                    continue
                if end_year and year > end_year:
                    continue
                filtered_keys.append((lk, year))
            league_keys = filtered_keys

            if not league_keys:
                raise ValueError(f"No seasons found in the specified year range ({start_year or 'any'} - {end_year or 'any'})")

        job.progress = 20
        years_found = [y for _, y in league_keys]
        if start_year or end_year:
            job.message = f"Processing {len(league_keys)} seasons ({min(years_found)}-{max(years_found)}) for '{league_name}'"
        else:
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


async def generate_sleeper_report_task(
    job_id: str,
    league_id: str,
    user: SleeperUser,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
):
    """Background task to generate Sleeper report."""
    try:
        job = jobs[job_id]
        job.status = "processing"
        job.progress = 5
        job.message = "Connecting to Sleeper..."

        api = SleeperFantasyAPI(user)

        # Discover league history
        job.progress = 10
        job.message = "Discovering league history..."

        league_ids, league_name = await sleeper_discover_league_history(api, league_id)

        # Filter by year range if specified
        if start_year or end_year:
            filtered_ids = []
            for lid, year in league_ids:
                if start_year and year < start_year:
                    continue
                if end_year and year > end_year:
                    continue
                filtered_ids.append((lid, year))
            league_ids = filtered_ids

            if not league_ids:
                raise ValueError(f"No seasons found in the specified year range ({start_year or 'any'} - {end_year or 'any'})")

        job.progress = 20
        years_found = [y for _, y in league_ids]
        if start_year or end_year:
            job.message = f"Processing {len(league_ids)} seasons ({min(years_found)}-{max(years_found)}) for '{league_name}'"
        else:
            job.message = f"Found {len(league_ids)} seasons for '{league_name}'"

        # Fetch all data
        generator = ReportGenerator(api)
        await generator.fetch_all_data(league_ids, job)

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
        print(f"Sleeper report generation error: {e}")
        import traceback
        traceback.print_exc()

        job = jobs[job_id]
        job.status = "failed"
        job.error = str(e)
        job.message = f"Error: {str(e)}"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
