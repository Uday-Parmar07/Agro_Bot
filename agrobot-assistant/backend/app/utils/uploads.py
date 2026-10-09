from fastapi import HTTPException, UploadFile, status


async def read_upload_limited(upload: UploadFile, max_bytes: int) -> bytes:
    """Read an upload into memory, refusing anything larger than max_bytes."""
    too_large = HTTPException(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        detail=f"File is too large. Maximum size is {max_bytes // (1024 * 1024)} MB.",
    )
    if upload.size is not None and upload.size > max_bytes:
        raise too_large
    content = await upload.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise too_large
    return content
