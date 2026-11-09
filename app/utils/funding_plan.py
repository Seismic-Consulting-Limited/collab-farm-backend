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
