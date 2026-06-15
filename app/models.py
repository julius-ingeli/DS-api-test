from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class RouteRequest(BaseModel):
    symptom_source: str
    symptom_value: str


class RouteResponse(BaseModel):
    user_id: Optional[str] = None

    category: Optional[str]
    clinic_1: Optional[str]
    clinic_2: Optional[str]
    benefit: Optional[str]

    matched_rules: List[str]
    selected_rule: Optional[str]

    fallback_used: bool
    version: str
    trace: Dict[str, Any]
