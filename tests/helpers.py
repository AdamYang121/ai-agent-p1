"""Shared test helper factories (not pytest fixtures)."""
from unittest.mock import MagicMock
from datetime import datetime


def make_intake(**overrides):
    """Return a mock ProjectIntake with sensible mid-grade defaults."""
    defaults = dict(
        bathroom_sqft=60.0,
        shower_sqft=25.0,
        tub_sqft=20.0,
        has_tub=True,
        finish_level="mid",
        full_gut=True,
        relocate_plumbing=False,
        new_shower=True,
        new_tub=False,
        new_toilet=True,
        new_vanity=True,
        heated_floor=False,
        new_exhaust_fan=True,
        description="Full gut remodel with new shower and toilet",
        ai_scope_summary=None,
    )
    defaults.update(overrides)
    intake = MagicMock()
    for k, v in defaults.items():
        setattr(intake, k, v)
    return intake


def make_project(**overrides):
    """Return a mock Project."""
    defaults = dict(
        id=1,
        token="abc123token",
        homeowner_name="Jane Smith",
        homeowner_email="jane@example.com",
        homeowner_phone="206-555-0100",
        address="123 Main St, Seattle, WA 98101",
        status="sent",
        created_at=datetime(2026, 4, 1, 12, 0, 0),
    )
    defaults.update(overrides)
    project = MagicMock()
    for k, v in defaults.items():
        setattr(project, k, v)
    return project


def make_estimate(line_items=None, **overrides):
    """Return a mock Estimate."""
    if line_items is None:
        line_items = [
            {"name": "Plumbing Labor", "category": "Plumbing",
             "cost": 2500.0, "notes": "Basic fixture hook-up", "is_material": False},
            {"name": "Floor Tile (supply & install)", "category": "Tile",
             "cost": 1920.0, "notes": "60 sqft @ $32/sqft (mid)", "is_material": True},
        ]
    defaults = dict(
        id=1,
        project_id=1,
        line_items=line_items,
        subtotal=4420.0,
        gc_markup=884.0,
        sales_tax=196.8,
        total=5500.8,
        gc_notes="Permit required. Lead time 4-6 weeks.",
        valid_days=30,
        created_at=datetime(2026, 4, 1, 12, 0, 0),
    )
    defaults.update(overrides)
    estimate = MagicMock()
    for k, v in defaults.items():
        setattr(estimate, k, v)
    return estimate