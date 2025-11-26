from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Contraseña del usuario")

class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)