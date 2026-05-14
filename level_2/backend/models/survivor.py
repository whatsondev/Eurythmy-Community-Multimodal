from pydantic import BaseModel
from typing import Optional, List

class Practitioner(BaseModel):
    id: str
    name: str
    role: str
    pillar: str
    bio: str
    notes: str
    venue: str
    status: str
    Specialisms: List[str] = []
    Seeks: List[str] = []
