import os
import uuid
import httpx
from fastapi import HTTPException, status

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
MOCK_PAYSTACK = os.getenv("MOCK_PAYSTACK_TRANSFERS", "true").lower() == "true"
PAYSTACK_BASE_URL = "https://api.paystack.co"

HEADERS = {
    "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    "Content-Type": "application/json"
}


async def create_transfer_recipient(name: str, account_number: str, bank_code: str) -> str:
    if MOCK_PAYSTACK:
        return f"RCP_mock_{uuid.uuid4().hex[:8]}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{PAYSTACK_BASE_URL}/transferrecipient",
            headers=HEADERS,
            json={"type": "nuban", "name": name, "account_number": account_number,
                  "bank_code": bank_code, "currency": "NGN"}
        )
        res_data = response.json()
        if not response.is_success or not res_data.get("status"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=res_data.get("message"))
        return res_data["data"]["recipient_code"]


async def initiate_paystack_transfer(amount_kobo: int, recipient_code: str, reason: str = "Investor Wallet Withdrawal") -> dict:
    if MOCK_PAYSTACK:
        return {
            "status": "success",
            "transfer_code": f"TRF_mock_{uuid.uuid4().hex[:10]}",
            "amount": amount_kobo
        }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{PAYSTACK_BASE_URL}/transfer",
            headers=HEADERS,
            json={"source": "balance", "amount": amount_kobo,
                  "recipient": recipient_code, "reason": reason}
        )
        res_data = response.json()
        if not response.is_success or not res_data.get("status"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=res_data.get("message"))
        return res_data["data"]
