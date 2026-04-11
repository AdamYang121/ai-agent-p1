"""
Tests for app/services/claude_service.py

All tests mock the Anthropic client so no real API calls are made.
"""
import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


def _make_api_response(text: str):
    """Build a minimal fake Anthropic API response object."""
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    return response


# ---------------------------------------------------------------------------
# extract_scope_from_description
# ---------------------------------------------------------------------------

class TestExtractScopeFromDescription:

    @pytest.fixture(autouse=True)
    def patch_client(self):
        with patch("app.services.claude_service.client") as mock_client:
            self.mock_client = mock_client
            yield

    @pytest.mark.asyncio
    async def test_returns_parsed_json(self):
        payload = {
            "full_gut": True, "relocate_plumbing": False, "new_shower": True,
            "new_tub": False, "new_toilet": True, "new_vanity": True,
            "heated_floor": False, "has_tub": False,
            "finish_level": "mid", "notes": "open-concept walk-in shower",
        }
        self.mock_client.messages.create.return_value = _make_api_response(json.dumps(payload))

        from app.services.claude_service import extract_scope_from_description
        result = await extract_scope_from_description("gut the bathroom and add a walk-in shower")

        assert result["full_gut"] is True
        assert result["new_shower"] is True
        assert result["finish_level"] == "mid"

    @pytest.mark.asyncio
    async def test_strips_markdown_code_fence(self):
        payload = {"full_gut": False, "finish_level": "luxury"}
        fenced = f"```json\n{json.dumps(payload)}\n```"
        self.mock_client.messages.create.return_value = _make_api_response(fenced)

        from app.services.claude_service import extract_scope_from_description
        result = await extract_scope_from_description("high-end remodel")
        assert result["finish_level"] == "luxury"

    @pytest.mark.asyncio
    async def test_passes_description_to_api(self):
        payload = {"full_gut": True, "finish_level": "budget"}
        self.mock_client.messages.create.return_value = _make_api_response(json.dumps(payload))

        from app.services.claude_service import extract_scope_from_description
        description = "basic toilet and vanity swap"
        await extract_scope_from_description(description)

        call_args = self.mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        assert any(description in str(m) for m in messages)

    @pytest.mark.asyncio
    async def test_uses_correct_model(self):
        payload = {"full_gut": True, "finish_level": "mid"}
        self.mock_client.messages.create.return_value = _make_api_response(json.dumps(payload))

        from app.services.claude_service import extract_scope_from_description
        await extract_scope_from_description("remodel description")

        call_kwargs = self.mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_invalid_json_raises(self):
        self.mock_client.messages.create.return_value = _make_api_response("not valid json at all")

        from app.services.claude_service import extract_scope_from_description
        with pytest.raises(json.JSONDecodeError):
            await extract_scope_from_description("some description")


# ---------------------------------------------------------------------------
# answer_homeowner_question
# ---------------------------------------------------------------------------

class TestAnswerHomeownerQuestion:

    @pytest.fixture(autouse=True)
    def patch_client(self):
        with patch("app.services.claude_service.client") as mock_client:
            self.mock_client = mock_client
            yield

    @pytest.mark.asyncio
    async def test_returns_answer_and_topic(self):
        api_text = "The tile work will take about 3 days.\nTOPIC: timeline"
        self.mock_client.messages.create.return_value = _make_api_response(api_text)

        from app.services.claude_service import answer_homeowner_question
        answer, topic = await answer_homeowner_question("How long will tiling take?", "...")

        assert "3 days" in answer
        assert topic == "timeline"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("topic_tag,expected", [
        ("TOPIC: pricing", "pricing"),
        ("TOPIC: plumbing", "plumbing"),
        ("TOPIC: electrical", "electrical"),
        ("TOPIC: tile", "tile"),
        ("TOPIC: timeline", "timeline"),
        ("TOPIC: scope", "scope"),
        ("TOPIC: permits", "permits"),
        ("TOPIC: warranty", "warranty"),
        ("TOPIC: other", "other"),
    ])
    async def test_all_valid_topics_parsed(self, topic_tag, expected):
        api_text = f"Some answer.\n{topic_tag}"
        self.mock_client.messages.create.return_value = _make_api_response(api_text)

        from app.services.claude_service import answer_homeowner_question
        _, topic = await answer_homeowner_question("question?", "context")
        assert topic == expected

    @pytest.mark.asyncio
    async def test_unknown_topic_defaults_to_other(self):
        api_text = "Some answer.\nTOPIC: unicorn"
        self.mock_client.messages.create.return_value = _make_api_response(api_text)

        from app.services.claude_service import answer_homeowner_question
        _, topic = await answer_homeowner_question("question?", "context")
        assert topic == "other"

    @pytest.mark.asyncio
    async def test_missing_topic_tag_defaults_to_other(self):
        api_text = "Some answer with no topic tag at all."
        self.mock_client.messages.create.return_value = _make_api_response(api_text)

        from app.services.claude_service import answer_homeowner_question
        answer, topic = await answer_homeowner_question("question?", "context")
        assert topic == "other"
        assert answer == api_text

    @pytest.mark.asyncio
    async def test_answer_does_not_include_topic_line(self):
        api_text = "Your permit will be handled by the GC.\nTOPIC: permits"
        self.mock_client.messages.create.return_value = _make_api_response(api_text)

        from app.services.claude_service import answer_homeowner_question
        answer, _ = await answer_homeowner_question("Do I need a permit?", "context")
        assert "TOPIC:" not in answer

    @pytest.mark.asyncio
    async def test_estimate_context_passed_to_api(self):
        api_text = "Answer.\nTOPIC: pricing"
        self.mock_client.messages.create.return_value = _make_api_response(api_text)

        from app.services.claude_service import answer_homeowner_question
        context = "Line items: Floor Tile $1920"
        await answer_homeowner_question("Why is tile so expensive?", context)

        call_kwargs = self.mock_client.messages.create.call_args.kwargs
        messages_content = str(call_kwargs["messages"])
        assert context in messages_content


# ---------------------------------------------------------------------------
# generate_cover_letter
# ---------------------------------------------------------------------------

class TestGenerateCoverLetter:

    @pytest.fixture(autouse=True)
    def patch_client(self):
        with patch("app.services.claude_service.client") as mock_client:
            self.mock_client = mock_client
            yield

    @pytest.mark.asyncio
    async def test_returns_string(self):
        letter = "Dear Jane,\n\nThank you for choosing us...\n\nBest regards,\nNorthwest Remodel Co."
        self.mock_client.messages.create.return_value = _make_api_response(letter)

        from app.services.claude_service import generate_cover_letter
        result = await generate_cover_letter("Jane Smith", "Full gut remodel", 18500.0)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_strips_whitespace(self):
        self.mock_client.messages.create.return_value = _make_api_response("  Hello world.  ")

        from app.services.claude_service import generate_cover_letter
        result = await generate_cover_letter("Jane", "Scope", 10000.0)
        assert result == "Hello world."

    @pytest.mark.asyncio
    async def test_project_name_and_total_passed_to_api(self):
        self.mock_client.messages.create.return_value = _make_api_response("Letter text.")

        from app.services.claude_service import generate_cover_letter
        await generate_cover_letter("Smith Residence", "New shower", 22750.0)

        call_kwargs = self.mock_client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "Smith Residence" in user_content
        assert "22,750" in user_content

    @pytest.mark.asyncio
    async def test_uses_correct_model(self):
        self.mock_client.messages.create.return_value = _make_api_response("Letter.")

        from app.services.claude_service import generate_cover_letter
        await generate_cover_letter("Jane", "Scope", 15000.0)

        call_kwargs = self.mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-6"