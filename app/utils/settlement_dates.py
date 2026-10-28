import calendar
from datetime import date, datetime
from typing import Iterable, Optional

from app.models.disbursement_model import DisbursementStatus


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def package_settlement_date(
    package,
    disbursements: Optional[Iterable] = None,
    farmer_id=None,
) -> Optional[date]:
    """Use package payback date until disbursement, then add package tenure."""
    package_date = getattr(package, "expected_payback_date", None)
    if isinstance(package_date, datetime):
        package_date = package_date.date()

    package_disbursements = (
        disbursements
        if disbursements is not None
        else getattr(package, "disbursements", [])
    ) or []
    qualifying = [
        disbursement
        for disbursement in package_disbursements
        if disbursement.status == DisbursementStatus.DISBURSED
        and disbursement.disbursement_date is not None
        and (farmer_id is None or disbursement.farmer_id == farmer_id)
    ]
    if not qualifying:
        return package_date

    latest = max(qualifying, key=lambda item: item.disbursement_date)
    disbursed_on = latest.disbursement_date
    if isinstance(disbursed_on, datetime):
        disbursed_on = disbursed_on.date()

    return _add_months(disbursed_on, int(getattr(package, "tenure_months", 0) or 0))
