"""
Core estimation engine.
Takes a ProjectIntake and returns a list of line items with costs.
"""

from pricing.seattle_pricing import (
    FinishLevel, DEMO_COST_PER_SQFT, PLUMBING, ELECTRICAL,
    WATERPROOFING_PER_SQFT, TILE, DRYWALL_PAINT_PER_SQFT,
    FIXTURES, GC_MARKUP_RATE, SEATTLE_SALES_TAX,
)


def build_line_items(intake) -> list[dict]:
    fl = FinishLevel(intake.finish_level)
    sqft = intake.bathroom_sqft or 50.0
    items = []

    def add(name: str, category: str, cost: float, notes: str = ""):
        items.append({
            "name": name,
            "category": category,
            "cost": round(cost, 2),
            "notes": notes,
            "is_material": False,   # True = sales tax applies
        })

    def add_material(name: str, category: str, cost: float, notes: str = ""):
        items.append({
            "name": name,
            "category": category,
            "cost": round(cost, 2),
            "notes": notes,
            "is_material": True,
        })

    # 1. Demo & Disposal
    if intake.full_gut:
        demo_cost = sqft * DEMO_COST_PER_SQFT[fl]
        add("Demo & Disposal", "Demo", demo_cost, f"{sqft} sqft @ ${DEMO_COST_PER_SQFT[fl]}/sqft")

    # 2. Waterproofing / Cement Board
    wet_area = (intake.shower_sqft or 0) + (intake.tub_sqft or 0)
    if wet_area > 0:
        wp_cost = wet_area * WATERPROOFING_PER_SQFT
        add("Waterproofing & Cement Board", "Framing & Substrate", wp_cost,
            f"{wet_area} sqft @ ${WATERPROOFING_PER_SQFT}/sqft")

    # 3. Plumbing labor
    plumbing_cost = PLUMBING["base_labor"][fl]
    notes = "Basic fixture hook-up"
    if intake.relocate_plumbing:
        plumbing_cost += PLUMBING["relocation_adder"][fl]
        notes += " + drain/supply relocation"
    add("Plumbing Labor", "Plumbing", plumbing_cost, notes)

    # 4. Electrical labor
    elec_cost = ELECTRICAL["base"][fl]
    elec_notes = "GFCI outlets, exhaust fan circuit, lighting"
    if intake.heated_floor:
        elec_cost += ELECTRICAL["heated_floor_adder"][fl]
        elec_notes += ", heated floor thermostat"
    add("Electrical Labor", "Electrical", elec_cost, elec_notes)

    # 5. Tile — floor
    floor_tile_cost = sqft * TILE["floor"][fl]
    add_material("Floor Tile (supply & install)", "Tile", floor_tile_cost,
                 f"{sqft} sqft @ ${TILE['floor'][fl]}/sqft ({fl.value})")

    # 6. Tile — shower walls
    if intake.new_shower and (intake.shower_sqft or 0) > 0:
        shower_tile_cost = intake.shower_sqft * TILE["shower_walls"][fl]
        add_material("Shower Wall Tile (supply & install)", "Tile", shower_tile_cost,
                     f"{intake.shower_sqft} sqft @ ${TILE['shower_walls'][fl]}/sqft ({fl.value})")

    # 7. Tile — tub surround
    if intake.has_tub and (intake.tub_sqft or 0) > 0:
        tub_tile_cost = intake.tub_sqft * TILE["tub_surround"][fl]
        add_material("Tub Surround Tile (supply & install)", "Tile", tub_tile_cost,
                     f"{intake.tub_sqft} sqft @ ${TILE['tub_surround'][fl]}/sqft ({fl.value})")

    # 8. Drywall & Paint
    dp_cost = sqft * DRYWALL_PAINT_PER_SQFT[fl]
    add("Drywall & Paint", "Drywall & Paint", dp_cost, f"{sqft} sqft @ ${DRYWALL_PAINT_PER_SQFT[fl]}/sqft")

    # 9. Fixtures (materials)
    if intake.new_toilet:
        add_material("Toilet", "Fixtures", FIXTURES["toilet"][fl], f"{fl.value.capitalize()} grade")

    if intake.new_vanity:
        add_material("Vanity with Sink & Faucet", "Fixtures", FIXTURES["vanity_with_sink"][fl],
                     f"{fl.value.capitalize()} grade, includes faucet")

    if intake.new_tub:
        add_material("Bathtub", "Fixtures", FIXTURES["tub"][fl], f"{fl.value.capitalize()} grade")

    if intake.new_shower:
        add_material("Shower Pan & Door/Enclosure", "Fixtures",
                     FIXTURES["shower_pan_and_door"][fl], f"{fl.value.capitalize()} grade")

    if intake.new_exhaust_fan:
        add_material("Exhaust Fan", "Fixtures", FIXTURES["exhaust_fan"][fl], f"{fl.value.capitalize()} grade")

    if intake.new_shower or intake.new_tub:
        add_material("Shower/Tub Valve & Trim", "Fixtures",
                     FIXTURES["shower_valve_trim"][fl], f"{fl.value.capitalize()} grade")

    # 10. Accessories
    add_material("Accessories & Hardware", "Fixtures", FIXTURES["accessories"][fl],
                 "Mirror, towel bars, TP holder, robe hook")

    # 11. Heated floor mat (material)
    if intake.heated_floor:
        heated_mat_cost = sqft * (8 if fl == FinishLevel.BUDGET else 12 if fl == FinishLevel.MID else 18)
        add_material("Heated Floor Mat", "Electrical", heated_mat_cost, f"{sqft} sqft")

    return items


def calculate_totals(line_items: list[dict], gc_markup_rate: float = GC_MARKUP_RATE) -> dict:
    labor_total = sum(i["cost"] for i in line_items if not i["is_material"])
    material_total = sum(i["cost"] for i in line_items if i["is_material"])
    subtotal = labor_total + material_total
    gc_markup = subtotal * gc_markup_rate
    sales_tax = material_total * SEATTLE_SALES_TAX
    total = subtotal + gc_markup + sales_tax

    return {
        "subtotal": round(subtotal, 2),
        "gc_markup": round(gc_markup, 2),
        "sales_tax": round(sales_tax, 2),
        "total": round(total, 2),
    }
