from typing import Optional
from fastapi import Header, HTTPException, status


async def verify_firebase_token(authorization: Optional[str] = Header(None)) -> dict:
    """Stub dependency for Firebase JWT authentication.

    Will be implemented in KAN-2.
    """
    if not authorization:
        # For public/unauthenticated dev endpoints or health check, allow bypass if needed.
        return {"uid": "anonymous_dev_user", "email": "dev@example.com"}
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Must be 'Bearer <token>'.",
        )

    token = authorization.split("Bearer ")[1]
    # Stub payload verification
    return {"uid": f"user_from_{token[:8]}", "token": token}
