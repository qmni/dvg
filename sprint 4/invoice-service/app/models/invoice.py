from pydantic import BaseModel
from datetime import date
from typing import Optional

class Invoice(BaseModel):
    invoice_number: str
    supplier_name: str
    amount: float
    currency: str
    invoice_date: date
    due_date: date
    iban: Optional[str] = None