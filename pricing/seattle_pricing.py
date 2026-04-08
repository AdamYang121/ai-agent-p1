"""
Seattle, WA bathroom remodel unit pricing.
Sources: HomeAdvisor, RSMeans 2024, local contractor data.
All prices in USD. Labor + materials unless noted.
"""

from enum import Enum


class FinishLevel(str, Enum):
    BUDGET = "budget"
    MID = "mid"
    LUXURY = "luxury"


# --- Demo & Disposal ---
# Per sq ft of bathroom floor area
DEMO_COST_PER_SQFT = {
    FinishLevel.BUDGET: 10.0,
    FinishLevel.MID: 12.0,
    FinishLevel.LUXURY: 15.0,
}

# --- Plumbing ---
PLUMBING = {
    "base_labor": {          # Basic hook-up, no relocation
        FinishLevel.BUDGET: 1_800,
        FinishLevel.MID:    2_500,
        FinishLevel.LUXURY: 3_500,
    },
    "relocation_adder": {    # Added if moving drain/supply lines
        FinishLevel.BUDGET: 2_500,
        FinishLevel.MID:    4_000,
        FinishLevel.LUXURY: 6_500,
    },
}

# --- Electrical ---
ELECTRICAL = {
    "base": {                # GFCI outlets, exhaust fan rough-in
        FinishLevel.BUDGET: 900,
        FinishLevel.MID:   1_400,
        FinishLevel.LUXURY: 2_200,
    },
    "heated_floor_adder": {
        FinishLevel.BUDGET: 800,
        FinishLevel.MID:   1_200,
        FinishLevel.LUXURY: 1_800,
    },
}

# --- Waterproofing / Cement Board ---
# Per sq ft of wet area (shower walls + floor)
WATERPROOFING_PER_SQFT = 4.50

# --- Tile ---
# Per sq ft, includes labor + materials
TILE = {
    "floor": {
        FinishLevel.BUDGET: 18.0,
        FinishLevel.MID:    32.0,
        FinishLevel.LUXURY: 65.0,
    },
    "shower_walls": {
        FinishLevel.BUDGET: 25.0,
        FinishLevel.MID:    45.0,
        FinishLevel.LUXURY: 90.0,
    },
    "tub_surround": {
        FinishLevel.BUDGET: 22.0,
        FinishLevel.MID:    38.0,
        FinishLevel.LUXURY: 75.0,
    },
}

# --- Drywall & Paint ---
# Per sq ft of bathroom floor area (proxy for wall surface)
DRYWALL_PAINT_PER_SQFT = {
    FinishLevel.BUDGET: 5.0,
    FinishLevel.MID:    6.5,
    FinishLevel.LUXURY: 9.0,
}

# --- Fixtures (unit cost, supply only — labor in plumbing) ---
FIXTURES = {
    "toilet": {
        FinishLevel.BUDGET: 350,
        FinishLevel.MID:    650,
        FinishLevel.LUXURY: 1_800,
    },
    "vanity_with_sink": {    # Includes faucet
        FinishLevel.BUDGET: 600,
        FinishLevel.MID:   1_400,
        FinishLevel.LUXURY: 4_500,
    },
    "tub": {
        FinishLevel.BUDGET: 700,
        FinishLevel.MID:   1_800,
        FinishLevel.LUXURY: 6_000,
    },
    "shower_pan_and_door": {
        FinishLevel.BUDGET: 900,
        FinishLevel.MID:   2_200,
        FinishLevel.LUXURY: 7_000,
    },
    "exhaust_fan": {
        FinishLevel.BUDGET: 120,
        FinishLevel.MID:    220,
        FinishLevel.LUXURY: 450,
    },
    "shower_valve_trim": {
        FinishLevel.BUDGET: 250,
        FinishLevel.MID:    500,
        FinishLevel.LUXURY: 1_200,
    },
    "accessories": {         # TP holder, towel bar, mirror, etc.
        FinishLevel.BUDGET: 300,
        FinishLevel.MID:    700,
        FinishLevel.LUXURY: 2_000,
    },
}

# --- GC Overhead & Profit ---
GC_MARKUP_RATE = 0.20        # 20% on all line items

# --- Seattle Sales Tax (materials only) ---
SEATTLE_SALES_TAX = 0.1025   # 10.25% as of 2024
