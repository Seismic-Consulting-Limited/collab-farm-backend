import os
import asyncio
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


async def upload_kyc_document(file: UploadFile, folder_path: str) -> dict:
 
    file_bytes = await file.read()

    response = await asyncio.to_thread(
        cloudinary.uploader.upload,
        file_bytes,
        folder=folder_path,
        type="private",
        resource_type="auto"
    )

    return {
        "secure_url": response.get("secure_url"),
        "public_id": response.get("public_id")
    }
