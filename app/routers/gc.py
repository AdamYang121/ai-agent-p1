"""GC-facing routes: dashboard, estimate review/edit, send quote, download PDF."""

import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Project, Estimate
from app.services.estimator import build_line_items, calculate_totals
from app.services.claude_service import generate_cover_letter
from app.services.pdf_service import generate_quote_pdf
from app.config import settings

router = APIRouter(prefix="/gc", tags=["gc"])
templates = Jinja2Templates(directory="app/templates")

_sessions: set[str] = set()


def require_gc(request: Request):
    token = request.cookies.get("gc_session")
    if token not in _sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")


async def get_project(project_id: int, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.intake), selectinload(Project.estimate),
                 selectinload(Project.messages))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404)
    return project


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "gc/login.html")


@router.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password != settings.gc_password:
        return templates.TemplateResponse(request, "gc/login.html", {"error": "Incorrect password"})
    session_token = secrets.token_hex(32)
    _sessions.add(session_token)
    response = RedirectResponse(url="/gc/dashboard", status_code=302)
    response.set_cookie("gc_session", session_token, httponly=True)
    return response


@router.get("/logout")
async def logout(request: Request):
    _sessions.discard(request.cookies.get("gc_session"))
    response = RedirectResponse(url="/gc/login", status_code=302)
    response.delete_cookie("gc_session")
    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db), _=Depends(require_gc)):
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.estimate))
        .order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return templates.TemplateResponse(request, "gc/dashboard.html", {"projects": projects})


@router.post("/projects/new")
async def create_project(request: Request, db: AsyncSession = Depends(get_db), _=Depends(require_gc)):
    token = secrets.token_urlsafe(32)
    project = Project(token=token, status="intake")
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return JSONResponse({"token": token, "project_id": project.id,
                         "homeowner_url": f"/project/{token}"})


@router.get("/project/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: int,
                          db: AsyncSession = Depends(get_db), _=Depends(require_gc)):
    project = await get_project(project_id, db)
    return templates.TemplateResponse(request, "gc/project_detail.html",
                                      {"project": project, "estimate": project.estimate})


@router.post("/project/{project_id}/estimate")
async def generate_estimate(project_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_gc)):
    project = await get_project(project_id, db)
    if not project.intake:
        raise HTTPException(status_code=400, detail="No intake data")

    line_items = build_line_items(project.intake)
    totals = calculate_totals(line_items)

    estimate = project.estimate
    if estimate:
        estimate.line_items = line_items
        estimate.subtotal = totals["subtotal"]
        estimate.gc_markup = totals["gc_markup"]
        estimate.sales_tax = totals["sales_tax"]
        estimate.total = totals["total"]
    else:
        estimate = Estimate(project_id=project_id, line_items=line_items, **totals)
        db.add(estimate)

    project.status = "estimated"
    await db.commit()
    await db.refresh(estimate)
    return JSONResponse({"estimate_id": estimate.id, "total": estimate.total,
                         "line_items": estimate.line_items})


@router.post("/project/{project_id}/estimate/update")
async def update_estimate(project_id: int, request: Request,
                           db: AsyncSession = Depends(get_db), _=Depends(require_gc)):
    body = await request.json()
    result = await db.execute(select(Estimate).where(Estimate.project_id == project_id))
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404)

    if "line_items" in body:
        estimate.line_items = body["line_items"]
        totals = calculate_totals(estimate.line_items)
        estimate.subtotal = totals["subtotal"]
        estimate.gc_markup = totals["gc_markup"]
        estimate.sales_tax = totals["sales_tax"]
        estimate.total = totals["total"]

    if "gc_notes" in body:
        estimate.gc_notes = body["gc_notes"]

    await db.commit()
    return JSONResponse({"total": estimate.total, "subtotal": estimate.subtotal,
                         "gc_markup": estimate.gc_markup, "sales_tax": estimate.sales_tax})


@router.post("/project/{project_id}/send")
async def send_quote(project_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_gc)):
    project = await get_project(project_id, db)
    project.status = "sent"
    await db.commit()
    return JSONResponse({"status": "sent", "homeowner_url": f"/project/{project.token}/quote"})


@router.get("/project/{project_id}/pdf")
async def download_pdf(project_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_gc)):
    project = await get_project(project_id, db)
    estimate = project.estimate
    if not estimate:
        raise HTTPException(status_code=404, detail="No estimate yet")

    scope_summary = project.intake.ai_scope_summary if project.intake else ""
    cover_letter = await generate_cover_letter(
        project_name=project.homeowner_name or f"Project #{project_id}",
        scope_summary=scope_summary or "Full bathroom remodel",
        total=estimate.total,
    )

    pdf_bytes = generate_quote_pdf(project, estimate, cover_letter)
    filename = f"quote-{project_id}-{project.homeowner_name or 'client'}.pdf".replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
