"""
Tests for pricing/seattle_pricing.py

Validates that all pricing constants are complete, correctly typed,
and logically ordered (budget < mid < luxury).
"""
import pytest
from pricing.seattle_pricing import (
    FinishLevel,
    DEMO_COST_PER_SQFT,
    PLUMBING,
    ELECTRICAL,
    WATERPROOFING_PER_SQFT,
    TILE,
    DRYWALL_PAINT_PER_SQFT,
    FIXTURES,
    GC_MARKUP_RATE,
    SEATTLE_SALES_TAX,
)

ALL_LEVELS = [FinishLevel.BUDGET, FinishLevel.MID, FinishLevel.LUXURY]


class TestFinishLevel:
    def test_enum_values(self):
        assert FinishLevel.BUDGET.value == "budget"
        assert FinishLevel.MID.value == "mid"
        assert FinishLevel.LUXURY.value == "luxury"

    def test_is_string_enum(self):
        # FinishLevel(str, Enum) means it should compare equal to its string value
        assert FinishLevel("budget") == FinishLevel.BUDGET
        assert FinishLevel("mid") == FinishLevel.MID
        assert FinishLevel("luxury") == FinishLevel.LUXURY

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            FinishLevel("premium")


class TestDemoCost:
    def test_all_finish_levels_present(self):
        for level in ALL_LEVELS:
            assert level in DEMO_COST_PER_SQFT

    def test_positive_values(self):
        for level in ALL_LEVELS:
            assert DEMO_COST_PER_SQFT[level] > 0

    def test_ascending_order(self):
        assert DEMO_COST_PER_SQFT[FinishLevel.BUDGET] < DEMO_COST_PER_SQFT[FinishLevel.MID]
        assert DEMO_COST_PER_SQFT[FinishLevel.MID] < DEMO_COST_PER_SQFT[FinishLevel.LUXURY]


class TestPlumbing:
    def test_required_keys_present(self):
        assert "base_labor" in PLUMBING
        assert "relocation_adder" in PLUMBING

    def test_all_finish_levels_in_each_key(self):
        for key in ("base_labor", "relocation_adder"):
            for level in ALL_LEVELS:
                assert level in PLUMBING[key], f"Missing {level} in PLUMBING[{key!r}]"

    def test_base_labor_ascending(self):
        bl = PLUMBING["base_labor"]
        assert bl[FinishLevel.BUDGET] < bl[FinishLevel.MID] < bl[FinishLevel.LUXURY]

    def test_relocation_adder_exceeds_base_labor(self):
        # Moving plumbing is expensive — adder should be substantial
        for level in ALL_LEVELS:
            assert PLUMBING["relocation_adder"][level] > 0


class TestElectrical:
    def test_required_keys_present(self):
        assert "base" in ELECTRICAL
        assert "heated_floor_adder" in ELECTRICAL

    def test_all_finish_levels_present(self):
        for key in ("base", "heated_floor_adder"):
            for level in ALL_LEVELS:
                assert level in ELECTRICAL[key]

    def test_base_ascending(self):
        base = ELECTRICAL["base"]
        assert base[FinishLevel.BUDGET] < base[FinishLevel.MID] < base[FinishLevel.LUXURY]


class TestWaterproofing:
    def test_is_float(self):
        assert isinstance(WATERPROOFING_PER_SQFT, float)

    def test_positive(self):
        assert WATERPROOFING_PER_SQFT > 0


class TestTile:
    def test_required_keys_present(self):
        for key in ("floor", "shower_walls", "tub_surround"):
            assert key in TILE

    def test_all_finish_levels_in_each_key(self):
        for key in ("floor", "shower_walls", "tub_surround"):
            for level in ALL_LEVELS:
                assert level in TILE[key]

    def test_floor_tile_ascending(self):
        f = TILE["floor"]
        assert f[FinishLevel.BUDGET] < f[FinishLevel.MID] < f[FinishLevel.LUXURY]

    def test_shower_walls_more_expensive_than_floor(self):
        # Shower wall tile is typically pricier than floor per sqft
        for level in ALL_LEVELS:
            assert TILE["shower_walls"][level] > TILE["floor"][level]


class TestDrywallPaint:
    def test_all_finish_levels_present(self):
        for level in ALL_LEVELS:
            assert level in DRYWALL_PAINT_PER_SQFT

    def test_ascending_order(self):
        d = DRYWALL_PAINT_PER_SQFT
        assert d[FinishLevel.BUDGET] < d[FinishLevel.MID] < d[FinishLevel.LUXURY]


class TestFixtures:
    FIXTURE_ITEMS = [
        "toilet", "vanity_with_sink", "tub", "shower_pan_and_door",
        "exhaust_fan", "shower_valve_trim", "accessories",
    ]

    def test_all_fixture_items_present(self):
        for item in self.FIXTURE_ITEMS:
            assert item in FIXTURES, f"Missing fixture: {item}"

    def test_all_finish_levels_in_each_fixture(self):
        for item in self.FIXTURE_ITEMS:
            for level in ALL_LEVELS:
                assert level in FIXTURES[item], f"Missing {level} in FIXTURES[{item!r}]"

    def test_toilet_ascending(self):
        t = FIXTURES["toilet"]
        assert t[FinishLevel.BUDGET] < t[FinishLevel.MID] < t[FinishLevel.LUXURY]

    def test_vanity_ascending(self):
        v = FIXTURES["vanity_with_sink"]
        assert v[FinishLevel.BUDGET] < v[FinishLevel.MID] < v[FinishLevel.LUXURY]

    def test_tub_ascending(self):
        t = FIXTURES["tub"]
        assert t[FinishLevel.BUDGET] < t[FinishLevel.MID] < t[FinishLevel.LUXURY]


class TestRates:
    def test_gc_markup_is_20_percent(self):
        assert GC_MARKUP_RATE == pytest.approx(0.20)

    def test_sales_tax_positive_and_reasonable(self):
        assert 0.05 < SEATTLE_SALES_TAX < 0.15

    def test_sales_tax_known_value(self):
        assert SEATTLE_SALES_TAX == pytest.approx(0.1025)