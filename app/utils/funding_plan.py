from typing import Iterable, Optional


_FUNDING_PLANS = {
    "CROP_FARMING": [
        ("T1 Project preparation", 30, "Approved land preparation, supplier deposits and initial farming inputs", ["Cooperative accountability agreement signed", "Supplier quotations verified", "Farmer participation agreements signed"]),
        ("T2 Planting", 30, "Released after evidence confirms preparation and input delivery milestones", ["Input delivery receipts uploaded", "Land preparation inspection report approved"]),
        ("T3 Crop maintenance", 25, "Released after relevant farming activities are verified", ["Planting report with photos and GPS", "Field inspection completed"]),
        ("T4 Harvest", 15, "Harvesting, storage and other agreed expenses", ["Crop maintenance report approved", "Storage arrangements confirmed"]),
    ],
    "FISHERY": [
        ("T1 Pond preparation", 25, "Prepare ponds, water systems and initial supplies before stocking", ["Cooperative accountability agreement signed", "Pond inspection approved", "Water quality test recorded"]),
        ("T2 Stocking and feed", 35, "Purchase fingerlings and deliver the first feed allocation", ["Fingerling supplier verified", "Stocking quantities and receipts recorded", "Farmer participation agreements signed"]),
        ("T3 Fish growth and care", 25, "Support feed, water quality management and fish health during the cycle", ["Growth and mortality report submitted", "Water quality and pond inspection approved"]),
        ("T4 Harvest and sale", 15, "Fund harvest, handling, storage and market delivery", ["Harvest weights verified", "Sales or buyer delivery records submitted"]),
    ],
    "MIXED_FARMING": [
        ("T1 Farm setup", 25, "Prepare land, animal housing and shared farm infrastructure", ["Cooperative accountability agreement signed", "Land and housing inspection approved", "Supplier quotations verified"]),
        ("T2 Crops and livestock inputs", 30, "Deliver seeds, young stock, feed and other initial inputs", ["Input delivery receipts uploaded", "Stock and seed quantities recorded", "Farmer participation agreements signed"]),
        ("T3 Growing and husbandry", 25, "Support crop care, animal health and ongoing farm operations", ["Crop and livestock progress report submitted", "Field or animal health inspection approved"]),
        ("T4 Harvest and processing", 20, "Support crop harvest, animal sale, storage and agreed processing", ["Harvest or sales quantities verified", "Storage or processing records submitted"]),
    ],
    "LIVESTOCK": [
        ("T1 Housing and stock preparation", 30, "Prepare animal housing, fencing, water and purchase approved stock", ["Cooperative accountability agreement signed", "Housing and fencing inspection approved", "Stock supplier verified"]),
        ("T2 Feed and animal health", 25, "Provide initial feed, vaccinations and veterinary support", ["Stock delivery and count recorded", "Veterinary and vaccination plan approved", "Farmer participation agreements signed"]),
        ("T3 Rearing and monitoring", 25, "Support feed and care while animals grow to the agreed target", ["Weight or herd progress report submitted", "Animal health inspection approved"]),
        ("T4 Sale and closeout", 20, "Prepare animals for sale and record proceeds and final costs", ["Sale weights and buyer records verified", "Final livestock and cost reconciliation submitted"]),
    ],
    "POULTRY": [
        ("T1 Housing and brooding setup", 30, "Prepare poultry housing, biosecurity and approved chicks", ["Cooperative accountability agreement signed", "Poultry house and biosecurity inspection approved", "Chick supplier verified"]),
        ("T2 Brooding and early care", 30, "Provide starter feed, heat, vaccines and early veterinary care", ["Chick delivery count recorded", "Feed and vaccination receipts uploaded", "Farmer participation agreements signed"]),
        ("T3 Growing and flock care", 25, "Support feed and flock health through the grow-out period", ["Flock mortality and growth report submitted", "Veterinary or farm inspection approved"]),
        ("T4 Processing and sale", 15, "Support agreed processing, transport and market delivery", ["Sale or processing quantities verified", "Buyer and delivery records submitted"]),
    ],
}


def build_funding_plan(amount: float, category=None) -> list[dict]:
    """Build the platform-fixed funding plan for a farming category."""
    category_value = getattr(category, "value", category)
    category_key = str(category_value or "CROP_FARMING").upper()
    tranches = _FUNDING_PLANS.get(category_key, _FUNDING_PLANS["CROP_FARMING"])
    plan = [
        {
            "tranche": title,
            "share_percentage": share,
            "amount": round(amount * share / 100, 2),
            "description": description,
            "released_after": conditions,
        }
        for title, share, description, conditions in tranches
    ]
    if plan:
        plan[-1]["amount"] = round(
            amount - sum(item["amount"] for item in plan[:-1]), 2
        )
    return plan


def calculate_funding_progress(
    amount: float,
    total_released: float,
    release_events: Optional[Iterable[dict]] = None,
    category=None,
) -> dict:
    """Allocate released package funds across fixed tranches and find crossing dates."""
    plan = build_funding_plan(amount, category)
    capped_released = min(max(float(total_released or 0), 0.0), max(amount, 0.0))
    events = [
        event for event in (release_events or []) if event.get("released_at") is not None
    ]
    events.sort(key=lambda event: event["released_at"].timestamp())
    crossing_dates = {}
    cumulative_event_amount = 0.0
    cumulative_threshold = 0.0
    event_index = 0
    for tranche in plan:
        cumulative_threshold += tranche["amount"]
        while event_index < len(events) and cumulative_event_amount < cumulative_threshold:
            event = events[event_index]
            cumulative_event_amount += float(event.get("amount", 0) or 0)
            event_index += 1
            if cumulative_event_amount >= cumulative_threshold:
                crossing_dates[tranche["tranche"]] = event["released_at"]
                break

    tranches = []
    cumulative_start = 0.0
    current_stage = "All tranches released"
    for tranche in plan:
        tranche_amount = float(tranche["amount"])
        cumulative_end = cumulative_start + tranche_amount
        tranche_released = min(
            max(capped_released - cumulative_start, 0.0), tranche_amount
        )
        passed = capped_released >= cumulative_end
        if passed:
            tranche_status = "completed"
        elif tranche_released > 0:
            tranche_status = "in_progress"
            if current_stage == "All tranches released":
                current_stage = tranche["tranche"]
        else:
            tranche_status = "pending"
            if current_stage == "All tranches released":
                current_stage = tranche["tranche"]

        tranches.append(
            {
                **tranche,
                "released_amount": round(tranche_released, 2),
                "status": tranche_status,
                "passed": passed,
                "passed_at": crossing_dates.get(tranche["tranche"]),
            }
        )
        cumulative_start = cumulative_end

    return {
        "total_released": round(float(total_released or 0), 2),
        "release_percentage": (
            round(capped_released / amount * 100, 2) if amount > 0 else 0.0
        ),
        "current_stage": current_stage,
        "tranches": [
            {**tranche, "is_current": tranche["tranche"] == current_stage}
            for tranche in tranches
        ],
    }
