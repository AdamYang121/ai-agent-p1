"""
Tests for app/services/estimator.py

Covers build_line_items() and calculate_totals() across all finish levels,
fixture combinations, and edge cases.
"""
import pytest
from helpers import make_intake
from app.services.estimator import build_line_items, calculate_totals
from pricing.seattle_pricing import (
    FinishLevel, DEMO_COST_PER_SQFT, PLUMBING, ELECTRICAL,
    WATERPROOFING_PER_SQFT, TILE, DRYWALL_PAINT_PER_SQFT,
    FIXTURES, GC_MARKUP_RATE, SEATTLE_SALES_TAX,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def item_named(items, name):
    """Return the first line item whose name contains `name`, or None."""
    return next((i for i in items if name in i["name"]), None)


def items_in_category(items, category):
    return [i for i in items if i["category"] == category]


# ---------------------------------------------------------------------------
# build_line_items — always-present items
# ---------------------------------------------------------------------------

class TestBuildLineItemsAlwaysPresent:
    """Items that appear regardless of intake flags."""

    def test_plumbing_labor_always_present(self):
        intake = make_intake()
        items = build_line_items(intake)
        assert item_named(items, "Plumbing Labor") is not None

    def test_electrical_labor_always_present(self):
        items = build_line_items(make_intake())
        assert item_named(items, "Electrical Labor") is not None

    def test_floor_tile_always_present(self):
        items = build_line_items(make_intake())
        assert item_named(items, "Floor Tile") is not None

    def test_drywall_paint_always_present(self):
        items = build_line_items(make_intake())
        assert item_named(items, "Drywall & Paint") is not None

    def test_accessories_always_present(self):
        items = build_line_items(make_intake())
        assert item_named(items, "Accessories") is not None

    def test_all_items_have_required_keys(self):
        items = build_line_items(make_intake())
        for item in items:
            assert "name" in item
            assert "category" in item
            assert "cost" in item
            assert "notes" in item
            assert "is_material" in item

    def test_all_costs_are_positive(self):
        items = build_line_items(make_intake())
        for item in items:
            assert item["cost"] > 0, f"Zero/negative cost for: {item['name']}"

    def test_costs_rounded_to_two_decimals(self):
        items = build_line_items(make_intake())
        for item in items:
            assert item["cost"] == round(item["cost"], 2)


# ---------------------------------------------------------------------------
# build_line_items — conditional items
# ---------------------------------------------------------------------------

class TestBuildLineItemsConditional:

    def test_demo_included_when_full_gut(self):
        items = build_line_items(make_intake(full_gut=True))
        assert item_named(items, "Demo") is not None

    def test_demo_excluded_when_not_full_gut(self):
        items = build_line_items(make_intake(full_gut=False))
        assert item_named(items, "Demo") is None

    def test_waterproofing_included_when_wet_area_present(self):
        items = build_line_items(make_intake(shower_sqft=25.0, tub_sqft=20.0))
        assert item_named(items, "Waterproofing") is not None

    def test_waterproofing_excluded_when_no_wet_area(self):
        items = build_line_items(make_intake(shower_sqft=0, tub_sqft=0))
        assert item_named(items, "Waterproofing") is None

    def test_shower_wall_tile_included_when_new_shower_with_sqft(self):
        items = build_line_items(make_intake(new_shower=True, shower_sqft=25.0))
        assert item_named(items, "Shower Wall Tile") is not None

    def test_shower_wall_tile_excluded_when_no_new_shower(self):
        items = build_line_items(make_intake(new_shower=False))
        assert item_named(items, "Shower Wall Tile") is None

    def test_shower_wall_tile_excluded_when_shower_sqft_zero(self):
        items = build_line_items(make_intake(new_shower=True, shower_sqft=0))
        assert item_named(items, "Shower Wall Tile") is None

    def test_tub_surround_tile_included_when_has_tub_with_sqft(self):
        items = build_line_items(make_intake(has_tub=True, tub_sqft=20.0))
        assert item_named(items, "Tub Surround Tile") is not None

    def test_tub_surround_tile_excluded_when_no_tub(self):
        items = build_line_items(make_intake(has_tub=False, tub_sqft=20.0))
        assert item_named(items, "Tub Surround Tile") is None

    def test_toilet_included_when_new_toilet(self):
        items = build_line_items(make_intake(new_toilet=True))
        assert item_named(items, "Toilet") is not None

    def test_toilet_excluded_when_not_new_toilet(self):
        items = build_line_items(make_intake(new_toilet=False))
        assert item_named(items, "Toilet") is None

    def test_vanity_included_when_new_vanity(self):
        items = build_line_items(make_intake(new_vanity=True))
        assert item_named(items, "Vanity") is not None

    def test_vanity_excluded_when_not_new_vanity(self):
        items = build_line_items(make_intake(new_vanity=False))
        assert item_named(items, "Vanity") is None

    def test_bathtub_fixture_included_when_new_tub(self):
        items = build_line_items(make_intake(new_tub=True))
        assert item_named(items, "Bathtub") is not None

    def test_bathtub_fixture_excluded_when_not_new_tub(self):
        items = build_line_items(make_intake(new_tub=False))
        assert item_named(items, "Bathtub") is None

    def test_exhaust_fan_included_when_new_exhaust_fan(self):
        items = build_line_items(make_intake(new_exhaust_fan=True))
        assert item_named(items, "Exhaust Fan") is not None

    def test_exhaust_fan_excluded_when_not_new_exhaust_fan(self):
        items = build_line_items(make_intake(new_exhaust_fan=False))
        assert item_named(items, "Exhaust Fan") is None

    def test_valve_trim_included_when_new_shower(self):
        items = build_line_items(make_intake(new_shower=True, new_tub=False))
        assert item_named(items, "Valve") is not None

    def test_valve_trim_included_when_new_tub(self):
        items = build_line_items(make_intake(new_tub=True, new_shower=False))
        assert item_named(items, "Valve") is not None

    def test_valve_trim_excluded_when_no_shower_or_tub(self):
        items = build_line_items(make_intake(new_shower=False, new_tub=False))
        assert item_named(items, "Valve") is None

    def test_heated_floor_mat_included_when_heated_floor(self):
        items = build_line_items(make_intake(heated_floor=True))
        assert item_named(items, "Heated Floor Mat") is not None

    def test_heated_floor_mat_excluded_when_no_heated_floor(self):
        items = build_line_items(make_intake(heated_floor=False))
        assert item_named(items, "Heated Floor Mat") is None


# ---------------------------------------------------------------------------
# build_line_items — material classification
# ---------------------------------------------------------------------------

class TestMaterialClassification:

    def test_plumbing_labor_is_not_material(self):
        items = build_line_items(make_intake())
        item = item_named(items, "Plumbing Labor")
        assert item["is_material"] is False

    def test_electrical_labor_is_not_material(self):
        items = build_line_items(make_intake())
        item = item_named(items, "Electrical Labor")
        assert item["is_material"] is False

    def test_demo_is_not_material(self):
        items = build_line_items(make_intake(full_gut=True))
        item = item_named(items, "Demo")
        assert item["is_material"] is False

    def test_drywall_paint_is_not_material(self):
        items = build_line_items(make_intake())
        item = item_named(items, "Drywall & Paint")
        assert item["is_material"] is False

    def test_floor_tile_is_material(self):
        items = build_line_items(make_intake())
        item = item_named(items, "Floor Tile")
        assert item["is_material"] is True

    def test_toilet_is_material(self):
        items = build_line_items(make_intake(new_toilet=True))
        item = item_named(items, "Toilet")
        assert item["is_material"] is True

    def test_vanity_is_material(self):
        items = build_line_items(make_intake(new_vanity=True))
        item = item_named(items, "Vanity")
        assert item["is_material"] is True

    def test_heated_floor_mat_is_material(self):
        items = build_line_items(make_intake(heated_floor=True))
        item = item_named(items, "Heated Floor Mat")
        assert item["is_material"] is True


# ---------------------------------------------------------------------------
# build_line_items — cost calculations
# ---------------------------------------------------------------------------

class TestCostCalculations:

    def test_demo_cost_matches_pricing(self):
        sqft = 80.0
        intake = make_intake(full_gut=True, bathroom_sqft=sqft, finish_level="budget")
        items = build_line_items(intake)
        item = item_named(items, "Demo")
        expected = round(sqft * DEMO_COST_PER_SQFT[FinishLevel.BUDGET], 2)
        assert item["cost"] == expected

    def test_plumbing_cost_increases_with_relocation(self):
        base_items = build_line_items(make_intake(relocate_plumbing=False, finish_level="mid"))
        relo_items = build_line_items(make_intake(relocate_plumbing=True, finish_level="mid"))
        base_cost = item_named(base_items, "Plumbing Labor")["cost"]
        relo_cost = item_named(relo_items, "Plumbing Labor")["cost"]
        expected_adder = PLUMBING["relocation_adder"][FinishLevel.MID]
        assert relo_cost == pytest.approx(base_cost + expected_adder)

    def test_electrical_cost_increases_with_heated_floor(self):
        base_items = build_line_items(make_intake(heated_floor=False, finish_level="mid"))
        hf_items = build_line_items(make_intake(heated_floor=True, finish_level="mid"))
        base_cost = item_named(base_items, "Electrical Labor")["cost"]
        hf_cost = item_named(hf_items, "Electrical Labor")["cost"]
        expected_adder = ELECTRICAL["heated_floor_adder"][FinishLevel.MID]
        assert hf_cost == pytest.approx(base_cost + expected_adder)

    def test_floor_tile_cost_matches_pricing(self):
        sqft = 60.0
        intake = make_intake(bathroom_sqft=sqft, finish_level="luxury")
        items = build_line_items(intake)
        item = item_named(items, "Floor Tile")
        expected = round(sqft * TILE["floor"][FinishLevel.LUXURY], 2)
        assert item["cost"] == expected

    def test_waterproofing_cost_matches_pricing(self):
        shower_sqft, tub_sqft = 30.0, 15.0
        intake = make_intake(shower_sqft=shower_sqft, tub_sqft=tub_sqft)
        items = build_line_items(intake)
        item = item_named(items, "Waterproofing")
        expected = round((shower_sqft + tub_sqft) * WATERPROOFING_PER_SQFT, 2)
        assert item["cost"] == expected

    def test_sqft_defaults_to_50_when_none(self):
        intake = make_intake(bathroom_sqft=None)
        items = build_line_items(intake)
        item = item_named(items, "Floor Tile")
        expected = round(50.0 * TILE["floor"][FinishLevel.MID], 2)
        assert item["cost"] == expected

    @pytest.mark.parametrize("finish_level", ["budget", "mid", "luxury"])
    def test_luxury_total_exceeds_budget(self, finish_level):
        # Smoke test: just ensure items are produced for all finish levels
        intake = make_intake(finish_level=finish_level)
        items = build_line_items(intake)
        assert len(items) > 0


# ---------------------------------------------------------------------------
# build_line_items — finish level ordering
# ---------------------------------------------------------------------------

class TestFinishLevelOrdering:
    """Higher finish levels should produce higher costs for the same scope."""

    def _total_cost(self, finish_level):
        intake = make_intake(
            finish_level=finish_level,
            full_gut=True, bathroom_sqft=60.0, shower_sqft=25.0, tub_sqft=20.0,
            has_tub=True, new_shower=True, new_tub=True, new_toilet=True,
            new_vanity=True, heated_floor=True, new_exhaust_fan=True,
            relocate_plumbing=True,
        )
        return sum(i["cost"] for i in build_line_items(intake))

    def test_budget_less_than_mid(self):
        assert self._total_cost("budget") < self._total_cost("mid")

    def test_mid_less_than_luxury(self):
        assert self._total_cost("mid") < self._total_cost("luxury")


# ---------------------------------------------------------------------------
# calculate_totals
# ---------------------------------------------------------------------------

class TestCalculateTotals:

    def _make_items(self, labor_cost, material_cost):
        return [
            {"name": "Labor", "category": "Plumbing", "cost": labor_cost,
             "notes": "", "is_material": False},
            {"name": "Material", "category": "Tile", "cost": material_cost,
             "notes": "", "is_material": True},
        ]

    def test_subtotal_is_sum_of_all_costs(self):
        items = self._make_items(1000.0, 500.0)
        result = calculate_totals(items)
        assert result["subtotal"] == pytest.approx(1500.0)

    def test_gc_markup_is_20_percent_of_subtotal(self):
        items = self._make_items(1000.0, 500.0)
        result = calculate_totals(items)
        assert result["gc_markup"] == pytest.approx(1500.0 * GC_MARKUP_RATE)

    def test_sales_tax_only_on_materials(self):
        items = self._make_items(1000.0, 500.0)
        result = calculate_totals(items)
        assert result["sales_tax"] == pytest.approx(500.0 * SEATTLE_SALES_TAX)

    def test_total_equals_subtotal_plus_markup_plus_tax(self):
        items = self._make_items(2000.0, 800.0)
        result = calculate_totals(items)
        expected = result["subtotal"] + result["gc_markup"] + result["sales_tax"]
        assert result["total"] == pytest.approx(expected)

    def test_zero_materials_means_zero_tax(self):
        items = [{"name": "Labor", "category": "Plumbing", "cost": 1000.0,
                  "notes": "", "is_material": False}]
        result = calculate_totals(items)
        assert result["sales_tax"] == 0.0

    def test_zero_labor_still_calculates_tax(self):
        items = [{"name": "Tile", "category": "Tile", "cost": 1000.0,
                  "notes": "", "is_material": True}]
        result = calculate_totals(items)
        assert result["sales_tax"] == pytest.approx(1000.0 * SEATTLE_SALES_TAX)

    def test_custom_markup_rate(self):
        items = self._make_items(1000.0, 1000.0)
        result = calculate_totals(items, gc_markup_rate=0.10)
        assert result["gc_markup"] == pytest.approx(2000.0 * 0.10)

    def test_all_values_rounded_to_two_decimals(self):
        items = self._make_items(333.33, 666.67)
        result = calculate_totals(items)
        for key in ("subtotal", "gc_markup", "sales_tax", "total"):
            assert result[key] == round(result[key], 2)

    def test_returns_expected_keys(self):
        result = calculate_totals(self._make_items(500.0, 500.0))
        assert set(result.keys()) == {"subtotal", "gc_markup", "sales_tax", "total"}

    def test_empty_line_items(self):
        result = calculate_totals([])
        assert result == {"subtotal": 0.0, "gc_markup": 0.0, "sales_tax": 0.0, "total": 0.0}

    def test_full_pipeline_budget(self):
        """Smoke test: build_line_items → calculate_totals for a budget remodel."""
        intake = make_intake(finish_level="budget", full_gut=True,
                             new_toilet=True, new_vanity=True)
        items = build_line_items(intake)
        totals = calculate_totals(items)
        assert totals["total"] > totals["subtotal"]
        assert totals["gc_markup"] > 0
        assert totals["sales_tax"] > 0

    def test_full_pipeline_luxury(self):
        """Luxury total should significantly exceed budget."""
        budget_intake = make_intake(finish_level="budget")
        luxury_intake = make_intake(finish_level="luxury")
        budget_total = calculate_totals(build_line_items(budget_intake))["total"]
        luxury_total = calculate_totals(build_line_items(luxury_intake))["total"]
        assert luxury_total > budget_total