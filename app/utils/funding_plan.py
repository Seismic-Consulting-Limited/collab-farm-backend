from typing import Iterable, Optional


def build_funding_plan(amount: float) -> list[dict]:
    """Build the platform-fixed release plan for a package amount."""
    tranches = [
        (
            "T1 Project preparation",
            30,
            "Approved land preparation, supplier deposits and initial farming inputs",
            [
                "Cooperative accountability agreement signed",
                "Supplier quotations verified",
                "Farmer participation agreements signed",
            ],
        ),
        (
            "T2 Planting",
            30,
            "Released after evidence confirms preparation and input delivery milestones",
            [
                "Input delivery receipts uploaded",
                "Land preparation inspection report approved",
            ],
        ),
        (
            "T3 Crop maintenance",
            25,
            "Released after relevant farming activities are verified",
            ["Planting report with photos and GPS", "Field inspection completed"],
        ),
        (
            "T4 Harvest",
            15,
            "Harvesting, storage and other agreed expenses",
            ["Crop maintenance report approved", "Storage arrangements confirmed"],
        ),
    ]
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
) -> dict:
    """Allocate released package funds across fixed tranches and find crossing dates."""
    plan = build_funding_plan(amount)
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
        "tranches": tranches,
    }
