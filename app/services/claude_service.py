"""
Claude API integration for:
1. Parsing homeowner natural language description → structured scope
2. Answering homeowner questions (with topic auto-tagging)
3. Generating GC cover letter for the quote PDF
"""

import json
import anthropic
from app.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

SCOPE_EXTRACTION_SYSTEM = """You are an expert bathroom remodel estimator in Seattle, WA.
Extract project scope from a homeowner's description and return ONLY valid JSON.
Map their words to these boolean flags and values:
- full_gut: complete tear-down to studs (default true if unclear)
- relocate_plumbing: moving drain or supply lines to new locations
- new_shower: installing/replacing a shower
- new_tub: installing/replacing a bathtub
- new_toilet: replacing toilet
- new_vanity: replacing vanity/sink
- heated_floor: radiant heated floor
- has_tub: bathroom has/will have a tub
- finish_level: "budget" | "mid" | "luxury"
- notes: brief summary of anything notable not captured by flags

Return JSON only, no explanation."""


async def extract_scope_from_description(description: str) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SCOPE_EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": description}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


TOPICS = ["pricing", "plumbing", "electrical", "tile", "timeline",
          "scope", "permits", "warranty", "other"]

QA_SYSTEM = """You are a friendly, knowledgeable general contractor assistant in Seattle, WA.
Answer the homeowner's question about their bathroom remodel quote clearly and concisely.
Keep answers under 200 words. Be transparent and honest. Avoid jargon.
At the end of your answer, on a new line, output exactly:
TOPIC: <one of: pricing, plumbing, electrical, tile, timeline, scope, permits, warranty, other>"""


async def answer_homeowner_question(question: str, estimate_context: str) -> tuple[str, str]:
    """
    Returns (answer_text, topic).
    """
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=QA_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Estimate context:\n{estimate_context}\n\nHomeowner question: {question}"
        }],
    )
    full = response.content[0].text.strip()

    # Extract topic tag from the last line
    topic = "other"
    lines = full.rsplit("\n", 1)
    if len(lines) == 2 and lines[1].startswith("TOPIC:"):
        topic_raw = lines[1].replace("TOPIC:", "").strip().lower()
        topic = topic_raw if topic_raw in TOPICS else "other"
        answer = lines[0].strip()
    else:
        answer = full

    return answer, topic


async def generate_cover_letter(project_name: str, scope_summary: str, total: float) -> str:
    system = """You are writing a professional cover letter for a bathroom remodel quote in Seattle, WA.
Keep it to 3 short paragraphs: (1) thank the client and summarize the project,
(2) briefly describe what's included, (3) next steps / call to action.
Tone: professional but warm. Do NOT invent specific numbers not provided."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=system,
        messages=[{
            "role": "user",
            "content": f"Project: {project_name}\nScope: {scope_summary}\nTotal estimate: ${total:,.0f}"
        }],
    )
    return response.content[0].text.strip()
