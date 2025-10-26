from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from app.utils.auth import rs
from app.schemas.crypto import HandshakeRequest,HandshakeResponse

router = APIRouter(prefix="/crypto", tags=["crypto"])


@router.post("/handshake", description="",response_model=HandshakeResponse)
async def get_room_users(
    handshake: HandshakeRequest,
    request: Request,
    
):
    token_room = request.cookies.get("token_room")
    if not token_room:
        raise HTTPException(status_code=403, detail="")

    public_key_server = await rs.generate(handshake.public_key_user)
    return public_key_server