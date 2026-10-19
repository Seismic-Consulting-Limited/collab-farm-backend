import os
from typing import Dict
import httpx
from fastapi import HTTPException, status

PAYSTACK_BASE_URL = "https://api.paystack.co"


def _get_headers() -> Dict[str, str]:
    mode = os.getenv("PAYSTACK_MODE", "test").lower()

    if mode == "live":
        secret_key = os.getenv("PAYSTACK_LIVE_SECRET_KEY") or os.getenv("PAYSTACK_SECRET_KEY", "")
    else:
        secret_key = os.getenv("PAYSTACK_SECRET_KEY") or os.getenv("PAYSTACK_LIVE_SECRET_KEY", "")

    if not secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Paystack secret key is missing in environment configuration.",
        )

    return {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }


async def resolve_account_number(account_number: str, bank_code: str) -> dict:
    """Verifies a 10-digit NUBAN account number against Paystack's lookup API."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{PAYSTACK_BASE_URL}/bank/resolve",
            headers=_get_headers(),
            params={"account_number": account_number, "bank_code": bank_code},
        )
        res_data = response.json()
        if not response.is_success or not res_data.get("status"):
            detail = res_data.get("message", "Could not resolve bank account details.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=detail
            )
        return res_data["data"]


async def create_transfer_recipient(
    name: str, account_number: str, bank_code: str
) -> str:
    """Creates a Paystack transfer recipient and returns recipient_code."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{PAYSTACK_BASE_URL}/transferrecipient",
            headers=_get_headers(),
            json={
                "type": "nuban",
                "name": name,
                "account_number": account_number,
                "bank_code": bank_code,
                "currency": "NGN",
            },
        )
        res_data = response.json()
        if not response.is_success or not res_data.get("status"):
            detail = res_data.get("message", "Failed to create transfer recipient.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=detail
            )
        return res_data["data"]["recipient_code"]


async def initiate_paystack_transfer(
    amount_kobo: int,
    recipient_code: str,
    reason: str = "Investor Wallet Withdrawal",
) -> dict:
    """Triggers an actual bank payout via Paystack balance."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{PAYSTACK_BASE_URL}/transfer",
            headers=_get_headers(),
            json={
                "source": "balance",
                "amount": amount_kobo,
                "recipient": recipient_code,
                "reason": reason,
            },
        )
        res_data = response.json()
        if not response.is_success or not res_data.get("status"):
            detail = res_data.get("message", "Transfer initiation failed.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=detail
            )
        return res_data["data"]