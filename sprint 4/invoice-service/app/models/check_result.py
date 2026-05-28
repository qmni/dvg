from pydantic import BaseModel
from typing import List

class CheckResult(BaseModel):
    validation_passed: bool
    compliance_passed: bool
    requires_manager_approval: bool
    errors: List[str] = []
    warnings: List[str] = []