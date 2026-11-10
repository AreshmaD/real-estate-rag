import math


def calculate_ownership_cost(
    *,
    purchase_price: float,
    down_payment: float,
    annual_interest_rate_percent: float,
    loan_term_years: int,
    annual_property_tax: float | None,
    annual_insurance: float | None,
    monthly_hoa: float | None,
    monthly_mortgage_insurance: float | None,
    monthly_maintenance_reserve: float = 0,
) -> dict:
    """Calculate a monthly scenario in USD.

    Missing recurring costs remain unknown, not zero.
    Maintenance is reported separately from housing costs.
    """
    values = {
        "purchase_price": purchase_price,
        "down_payment": down_payment,
        "annual_interest_rate_percent": annual_interest_rate_percent,
        "annual_property_tax": annual_property_tax,
        "annual_insurance": annual_insurance,
        "monthly_hoa": monthly_hoa,
        "monthly_mortgage_insurance": monthly_mortgage_insurance,
        "monthly_maintenance_reserve": monthly_maintenance_reserve,
    }

    for name, value in values.items():
        if value is not None and (
            not math.isfinite(value) or value < 0
        ):
            raise ValueError(f"{name} must be finite and nonnegative.")

    if purchase_price <= 0:
        raise ValueError("purchase_price must be greater than zero.")

    if down_payment > purchase_price:
        raise ValueError("down_payment cannot exceed purchase_price.")

    if (
        isinstance(loan_term_years, bool)
        or not isinstance(loan_term_years, int)
        or loan_term_years <= 0
    ):
        raise ValueError("loan_term_years must be a positive integer.")

    loan_amount = purchase_price - down_payment
    months = loan_term_years * 12
    monthly_rate = annual_interest_rate_percent / 100 / 12

    if loan_amount == 0:
        principal_and_interest = 0.0
    elif monthly_rate == 0:
        principal_and_interest = loan_amount / months
    else:
        denominator = -math.expm1(
            -months * math.log1p(monthly_rate)
        )
        principal_and_interest = (
            loan_amount * monthly_rate / denominator
        )

    components = {
        "principal_and_interest": principal_and_interest,
        "property_tax": (
            None if annual_property_tax is None
            else annual_property_tax / 12
        ),
        "homeowners_insurance": (
            None if annual_insurance is None
            else annual_insurance / 12
        ),
        "hoa": monthly_hoa,
        "mortgage_insurance": monthly_mortgage_insurance,
    }

    missing = [
        name for name, value in components.items()
        if value is None
    ]

    known_subtotal = sum(
        value for value in components.values()
        if value is not None
    )

    total = None if missing else known_subtotal

    return {
        "loan_amount": round(loan_amount, 2),
        "monthly_components": {
            name: None if value is None else round(value, 2)
            for name, value in components.items()
        },
        "known_monthly_subtotal": round(known_subtotal, 2),
        "monthly_housing_cost": (
            None if total is None else round(total, 2)
        ),
        "monthly_maintenance_reserve": round(
            monthly_maintenance_reserve, 2
        ),
        "monthly_cost_with_reserve": (
            None if total is None
            else round(total + monthly_maintenance_reserve, 2)
        ),
        "missing_inputs": missing,
        "complete": not missing,
    }