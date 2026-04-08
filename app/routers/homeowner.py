"""Homeowner-facing routes: questionnaire + quote view."""

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Project, ProjectIntake
from app.services.claude_service import extract_scope_from_description

router = APIRouter(prefix="/project", tags=["homeowner"])
templates = Jinja2Templates(directory="app/templates")


async def get_project_by_token(token: str, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project)
        .where(Project.token == token)
        .options(selectinload(Project.intake), selectinload(Project.estimate),
                 selectinload(Project.messages))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{token}", response_class=HTMLResponse)
async def homeowner_landing(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    project = await get_project_by_token(token, db)

    if project.status in ("sent", "accepted", "rejected") and project.estimate:
        return templates.TemplateResponse(request, "homeowner/quote_view.html",
                                          {"project": project, "estimate": project.estimate})

    return templates.TemplateResponse(request, "homeowner/questionnaire.html", {"project": project})


@router.post("/{token}/submit", response_class=HTMLResponse)
async def submit_questionnaire(
    request: Request,
    token: str,
    homeowner_name: str = Form(...),
    homeowner_email: str = Form(""),
    homeowner_phone: str = Form(""),
    address: str = Form(""),
    bathroom_sqft: float = Form(...),
    shower_sqft: float = Form(0),
    tub_sqft: float = Form(0),
    has_tub: bool = Form(False),
    finish_level: str = Form("mid"),
    full_gut: bool = Form(True),
    relocate_plumbing: bool = Form(False),
    new_shower: bool = Form(False),
    new_tub: bool = Form(False),
    new_toilet: bool = Form(True),
    new_vanity: bool = Form(True),
    heated_floor: bool = Form(False),
    new_exhaust_fan: bool = Form(True),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project_by_token(token, db)

    project.homeowner_name = homeowner_name
    project.homeowner_email = homeowner_email
    project.homeowner_phone = homeowner_phone
    project.address = address

    ai_scope: dict = {}
    ai_summary = ""
    if description.strip():
        try:
            ai_scope = await extract_scope_from_description(description)
            ai_summary = ai_scope.pop("notes", "")
            if "finish_level" in ai_scope:
                finish_level = ai_scope["finish_level"]
        except Exception:
            pass

    intake = ProjectIntake(
        project_id=project.id,
        bathroom_sqft=bathroom_sqft,
        shower_sqft=shower_sqft if new_shower else 0,
        tub_sqft=tub_sqft if has_tub else 0,
        has_tub=has_tub,
        finish_level=finish_level,
        full_gut=full_gut,
        relocate_plumbing=ai_scope.get("relocate_plumbing", relocate_plumbing),
        new_shower=ai_scope.get("new_shower", new_shower),
        new_tub=ai_scope.get("new_tub", new_tub),
        new_toilet=ai_scope.get("new_toilet", new_toilet),
        new_vanity=ai_scope.get("new_vanity", new_vanity),
        heated_floor=ai_scope.get("heated_floor", heated_floor),
        new_exhaust_fan=new_exhaust_fan,
        description=description,
        ai_scope_summary=ai_summary,
    )
    db.add(intake)
    project.status = "intake"
    await db.commit()
    await db.refresh(project)

    return templates.TemplateResponse(request, "homeowner/submitted.html", {"project": project})


@router.get("/{token}/quote", response_class=HTMLResponse)
async def view_quote(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    project = await get_project_by_token(token, db)
    if project.status not in ("sent", "accepted", "rejected"):
        raise HTTPException(status_code=403, detail="Quote not yet available")

    return templates.TemplateResponse(request, "homeowner/quote_view.html",
                                      {"project": project, "estimate": project.estimate})


@router.post("/{token}/respond")
async def homeowner_respond(token: str, action: str = Form(...), db: AsyncSession = Depends(get_db)):
    project = await get_project_by_token(token, db)
    if action == "accept":
        project.status = "accepted"
    elif action == "reject":
        project.status = "rejected"
    await db.commit()
    return JSONResponse({"status": project.status})
