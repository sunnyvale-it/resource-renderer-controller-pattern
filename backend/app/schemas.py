from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AppConfigBase(BaseModel):
    name: str
    repository_url: str
    branch: str
    environment: str

class AppConfigCreate(AppConfigBase):
    pass

class AppConfigUpdate(BaseModel):
    name: Optional[str] = None
    repository_url: Optional[str] = None
    branch: Optional[str] = None
    environment: Optional[str] = None

class AppConfig(AppConfigBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
