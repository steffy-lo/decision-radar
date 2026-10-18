"""Short, rate-limited access to the fixed connected sample workspace."""

from datetime import datetime, timedelta

from fastapi import HTTPException
from google.cloud import firestore

SESSION_LENGTH = timedelta(hours=1)
NEW_SESSIONS_PER_MINUTE = 10


async def admit_demo_session(client, project_id: str, folder_id: str, uid: str, created_at: datetime, now: datetime) -> datetime:
    expires_at = created_at + SESSION_LENGTH
    if created_at > now + timedelta(seconds=30) or expires_at <= now:
        raise HTTPException(status_code=403, detail="This demo session expired. Start a new demo session.")
    project = client.collection("projects").document(project_id)
    member_ref = project.collection("members").document(uid)
    connection_ref = project.collection("connections").document("google-drive")
    limit_ref = project.collection("demoAdmissions").document("current")

    @firestore.async_transactional
    async def admit(tx):
        member = (await member_ref.get(transaction=tx)).to_dict() or {}
        connection = (await connection_ref.get(transaction=tx)).to_dict() or {}
        if connection.get("selected_folder_id") != folder_id:
            raise HTTPException(status_code=503, detail="The sample folder is unavailable. Please try again later.")
        if member:
            if not member.get("demo_session") or member.get("role") != "editor" or member.get("refresh_folder_id") != folder_id or member.get("expires_at") != expires_at:
                raise HTTPException(status_code=403, detail="This account cannot start a public demo session.")
            return expires_at
        limit = (await limit_ref.get(transaction=tx)).to_dict() or {}
        window = now.strftime("%Y%m%d%H%M")
        count = limit.get("count", 0) if limit.get("window") == window else 0
        if count >= NEW_SESSIONS_PER_MINUTE:
            raise HTTPException(status_code=429, detail="The demo is busy. Please try again in a minute.", headers={"Retry-After": "60"})
        tx.set(limit_ref, {"window": window, "count": count + 1})
        tx.set(member_ref, {"role": "editor", "refresh_folder_id": folder_id, "demo_session": True, "expires_at": expires_at})
        return expires_at

    return await admit(client.transaction())
