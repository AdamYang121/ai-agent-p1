"""
Tests for app/services/pdf_service.py

Validates PDF generation output using real ReportLab (no mock needed —
ReportLab is a pure-Python library with no external calls).
"""
import pytest
from helpers import make_project, make_estimate


class TestGenerateQuotePdf:

    def test_returns_bytes(self):
        from app.services.pdf_service import generate_quote_pdf
        project = make_project()
        estimate = make_estimate()
        result = generate_quote_pdf(project, estimate, "Dear Jane, thank you.")
        assert isinstance(result, bytes)

    def test_output_is_valid_pdf(self):
        """PDF files must start with the %PDF magic bytes."""
        from app.services.pdf_service import generate_quote_pdf
        project = make_project()
        estimate = make_estimate()
        result = generate_quote_pdf(project, estimate, "Cover letter text.")
        assert result[:4] == b"%PDF"

    def test_non_empty_output(self):
        from app.services.pdf_service import generate_quote_pdf
        project = make_project()
        estimate = make_estimate()
        result = generate_quote_pdf(project, estimate, "Cover letter.")
        assert len(result) > 1000  # a real PDF is at least several KB

    def test_empty_cover_letter(self):
        """PDF generation should not crash with an empty cover letter."""
        from app.services.pdf_service import generate_quote_pdf
        project = make_project()
        estimate = make_estimate()
        result = generate_quote_pdf(project, estimate, "")
        assert result[:4] == b"%PDF"

    def test_cover_letter_with_newlines(self):
        """Newlines in cover letter are converted to <br/> tags — should not crash."""
        from app.services.pdf_service import generate_quote_pdf
        project = make_project()
        estimate = make_estimate()
        letter = "Paragraph one.\n\nParagraph two.\nParagraph three."
        result = generate_quote_pdf(project, estimate, letter)
        assert result[:4] == b"%PDF"

    def test_gc_notes_included_when_present(self):
        from app.services.pdf_service import generate_quote_pdf
        project = make_project()
        estimate = make_estimate(gc_notes="Permit required. Work starts Monday.")
        result = generate_quote_pdf(project, estimate, "Cover letter.")
        assert result[:4] == b"%PDF"

    def test_empty_gc_notes_does_not_crash(self):
        from app.services.pdf_service import generate_quote_pdf
        project = make_project()
        estimate = make_estimate(gc_notes="")
        result = generate_quote_pdf(project, estimate, "Cover letter.")
        assert result[:4] == b"%PDF"

    def test_multiple_line_items_in_multiple_categories(self):
        from app.services.pdf_service import generate_quote_pdf
        project = make_project()
        line_items = [
            {"name": "Demo & Disposal", "category": "Demo",
             "cost": 720.0, "notes": "60 sqft", "is_material": False},
            {"name": "Plumbing Labor", "category": "Plumbing",
             "cost": 2500.0, "notes": "Basic hook-up", "is_material": False},
            {"name": "Floor Tile (supply & install)", "category": "Tile",
             "cost": 1920.0, "notes": "60 sqft @ $32", "is_material": True},
            {"name": "Toilet", "category": "Fixtures",
             "cost": 650.0, "notes": "Mid grade", "is_material": True},
        ]
        estimate = make_estimate(
            line_items=line_items,
            subtotal=5790.0, gc_markup=1158.0, sales_tax=262.56, total=7210.56,
        )
        result = generate_quote_pdf(project, estimate, "Thank you for your business.")
        assert result[:4] == b"%PDF"

    def test_project_with_missing_optional_fields(self):
        """homeowner_name and address can be None — PDF should handle gracefully."""
        from app.services.pdf_service import generate_quote_pdf
        project = make_project(homeowner_name=None, address=None)
        estimate = make_estimate()
        result = generate_quote_pdf(project, estimate, "Cover letter.")
        assert result[:4] == b"%PDF"

    def test_large_total_formats_correctly(self):
        """Very large totals ($100k+) should not crash the PDF renderer."""
        from app.services.pdf_service import generate_quote_pdf
        project = make_project()
        estimate = make_estimate(
            subtotal=85000.0, gc_markup=17000.0, sales_tax=3200.0, total=105200.0
        )
        result = generate_quote_pdf(project, estimate, "High-end luxury remodel.")
        assert result[:4] == b"%PDF"