from pydantic import BaseModel

class HandshakeRequest(BaseModel):
    public_key_user: str
    
class HandshakeResponse(BaseModel):
    public_key_server: str
   
