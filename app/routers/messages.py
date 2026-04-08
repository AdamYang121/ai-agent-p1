"""
Messaging routes — shared between homeowner and GC.

Homeowner:
  POST /project/{token}/ask          — ask a question (AI answers, saved to DB)

GC:
  GET  /gc/project/{id}/messages     — view all messages with filters
  POST /gc/project/{id}/messages/{msg_id}/answer   — write / override answer
  POST /gc/project/{id}/messages/{msg_id}/read     — mark question as read
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Project, Message, TOPICS
from app.services.claude_service import answer_homeowner_question
from app.routers.gc import require_gc

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def get_project_by_token(token: str, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project)
        .where(Project.token == token)
        .options(selectinload(Project.estimate), selectinload(Project.messages))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def get_project_by_id(project_id: int, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.messages))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404)
    return project


def build_estimate_context(project: Project) -> str:
    if not project.estimate:
        return "No estimate available yet."
    e = project.estimate
    ctx = f"Project address: {project.address or 'N/A'}\nTotal: ${e.total:,.0f}\n\nLine items:\n"
    ctx += "\n".join(f"- {i['name']}: ${i['cost']:,.0f}  ({i.get('notes','')})"
                     for i in e.line_items)
    if e.gc_notes:
        ctx += f"\n\nContractor notes: {e.gc_notes}"
    return ctx


# ---------------------------------------------------------------------------
# Homeowner — ask a question
# ---------------------------------------------------------------------------

@router.post("/project/{token}/ask")
async def homeowner_ask(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    project = await get_project_by_token(token, db)

    body = await request.json()
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    estimate_context = build_estimate_context(project)
    answer, topic = await answer_homeowner_question(question, estimate_context)

    msg = Message(
        project_id=project.id,
        question=question,
        answer=answer,
        answered_by="ai",
        topic=topic,
        gc_read=False,
        homeowner_read=True,
        answered_at=datetime.utcnow(),
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    return JSONResponse({
        "id": msg.id,
        "answer": answer,
        "topic": topic,
        "answered_by": "ai",
        "created_at": msg.created_at.strftime("%b %d, %Y %I:%M %p"),
    })


# ---------------------------------------------------------------------------
# Homeowner — fetch chat history
# ---------------------------------------------------------------------------

@router.get("/project/{token}/messages")
async def homeowner_messages(
    token: str,
    sort: str = "newest",
    topic: str = "all",
    db: AsyncSession = Depends(get_db),
):
    project = await get_project_by_token(token, db)
    msgs = project.messages

    if topic != "all":
        msgs = [m for m in msgs if m.topic == topic]

    msgs = sorted(msgs, key=lambda m: m.created_at, reverse=(sort == "newest"))

    return JSONResponse([{
        "id": m.id,
        "question": m.question,
        "answer": m.answer,
        "answered_by": m.answered_by,
        "topic": m.topic,
        "created_at": m.created_at.strftime("%b %d, %Y %I:%M %p"),
        "answered_at": m.answered_at.strftime("%b %d, %Y %I:%M %p") if m.answered_at else None,
    } for m in msgs])


# ---------------------------------------------------------------------------
# GC — messages dashboard for a project
# ---------------------------------------------------------------------------

@router.get("/gc/project/{project_id}/messages", response_class=HTMLResponse)
async def gc_messages(
    request: Request,
    project_id: int,
    sort: str = "newest",
    topic: str = "all",
    status: str = "all",
    db: AsyncSession = Depends(get_db),
    _=Depends(require_gc),
):
    project = await get_project_by_id(project_id, db)
    msgs = project.messages[:]

    # Mark all fetched questions as read
    unread = [m for m in msgs if not m.gc_read]
    for m in unread:
        m.gc_read = True
    if unread:
        await db.commit()

    # Filter
    if topic != "all":
        msgs = [m for m in msgs if m.topic == topic]
    if status == "unanswered":
        msgs = [m for m in msgs if not m.answered_by]
    elif status == "needs_review":
        msgs = [m for m in msgs if m.answered_by == "ai"]
    elif status == "gc_answered":
        msgs = [m for m in msgs if m.answered_by == "gc"]

    # Sort
    msgs = sorted(msgs, key=lambda m: m.created_at, reverse=(sort == "newest"))

    # Topic counts (for filter badges) — from full unfiltered list
    all_msgs = project.messages
    topic_counts = {t: sum(1 for m in all_msgs if m.topic == t) for t in TOPICS}
    status_counts = {
        "all": len(all_msgs),
        "unanswered": sum(1 for m in all_msgs if not m.answered_by),
        "needs_review": sum(1 for m in all_msgs if m.answered_by == "ai"),
        "gc_answered": sum(1 for m in all_msgs if m.answered_by == "gc"),
    }

    return templates.TemplateResponse(request, "gc/messages.html", {
        "project": project,
        "messages": msgs,
        "topics": TOPICS,
        "topic_counts": topic_counts,
        "status_counts": status_counts,
        "current_sort": sort,
        "current_topic": topic,
        "current_status": status,
    })


# ---------------------------------------------------------------------------
# GC — write or override an answer
# ---------------------------------------------------------------------------

@router.post("/gc/project/{project_id}/messages/{msg_id}/answer")
async def gc_answer(
    project_id: int,
    msg_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_gc),
):
    body = await request.json()
    answer_text = body.get("answer", "").strip()
    if not answer_text:
        raise HTTPException(status_code=400, detail="Answer cannot be empty")

    result = await db.execute(
        select(Message).where(Message.id == msg_id, Message.project_id == project_id)
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404)

    msg.answer = answer_text
    msg.answered_by = "gc"
    msg.answered_at = datetime.utcnow()
    msg.homeowner_read = False  # notify homeowner there's a new/updated answer
    await db.commit()

    return JSONResponse({
        "answer": msg.answer,
        "answered_by": "gc",
        "answered_at": msg.answered_at.strftime("%b %d, %Y %I:%M %p"),
    })


# ---------------------------------------------------------------------------
# GC — unread count (for dashboard badge)
# ---------------------------------------------------------------------------

@router.get("/gc/project/{project_id}/messages/unread-count")
async def unread_count(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_gc),
):
    result = await db.execute(
        select(func.count()).where(
            Message.project_id == project_id,
            Message.gc_read == False,
        )
    )
    count = result.scalar()
    return JSONResponse({"unread": count})
