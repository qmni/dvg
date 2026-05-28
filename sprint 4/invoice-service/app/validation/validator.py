from app.models.invoice import Invoice


def validate_invoice(invoice: Invoice) -> list[str]:
    errors = []

    if not invoice.invoice_number.strip():
        errors.append("Rechnungsnummer fehlt")

    if not invoice.supplier_name.strip():
        errors.append("Lieferant fehlt")

    if invoice.amount <= 0:
        errors.append("Betrag muss größer als 0 sein")

    if invoice.currency != "EUR":
        errors.append("Nur EUR wird unterstützt")

    if invoice.due_date < invoice.invoice_date:
        errors.append("Fälligkeitsdatum darf nicht vor Rechnungsdatum liegen")

    return errors