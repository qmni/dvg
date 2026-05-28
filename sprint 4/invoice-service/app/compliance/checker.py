from app.models.invoice import Invoice


BLOCKED_SUPPLIERS = ["Fake Supplier GmbH", "Blocked Supplier AG"]
MANAGER_APPROVAL_LIMIT = 10000


def check_compliance(invoice: Invoice) -> tuple[list[str], list[str], bool]:
    errors = []
    warnings = []
    requires_manager_approval = False

    if invoice.supplier_name in BLOCKED_SUPPLIERS:
        errors.append("Lieferant ist gesperrt")

    if invoice.amount > MANAGER_APPROVAL_LIMIT:
        requires_manager_approval = True
        warnings.append("Betrag überschreitet Freigabegrenze")

    return errors, warnings, requires_manager_approval