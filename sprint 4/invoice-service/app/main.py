from fastapi import FastAPI

from app.models.invoice import Invoice
from app.service.invoice_check_service import check_invoice

app = FastAPI()


@app.post("/check-invoice")
def check_invoice_endpoint(invoice: Invoice):
    result = check_invoice(invoice)
    return result