from typing import Optional, List, Dict

from pydantic import BaseModel


class HealthEntryModel(BaseModel):
    data: Optional[dict] | None
    description: Optional[str] = None
    duration: str
    exception: Optional[str]= None
    status: str
    tags: List[str]

class HealthReportModel(BaseModel):
    status: str
    totalDuration: str
    entries: Dict[str, HealthEntryModel]