from app.models.invoice import Invoice
from app.models.check_result import CheckResult

from app.validation.validator import validate_invoice
from app.compliance.checker import check_compliance


def check_invoice(invoice: Invoice) -> CheckResult:
    validation_errors = validate_invoice(invoice)

    validation_passed = len(validation_errors) == 0

    compliance_errors = []
    warnings = []
    requires_manager_approval = False

    compliance_passed = True

    # Compliance nur prüfen wenn Validierung erfolgreich
    if validation_passed:
        (
            compliance_errors,
            warnings,
            requires_manager_approval
        ) = check_compliance(invoice)

        compliance_passed = len(compliance_errors) == 0

    all_errors = validation_errors + compliance_errors

    return CheckResult(
        validation_passed=validation_passed,
        compliance_passed=compliance_passed,
        requires_manager_approval=requires_manager_approval,
        errors=all_errors,
        warnings=warnings
    )