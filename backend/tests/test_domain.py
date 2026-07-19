import pytest
from decimal import Decimal
from app.domain.value_objects.money import Money, CurrencyMismatchException

def test_money_creation():
    m = Money("100.50", "INR")
    assert m.amount == Decimal("100.5000")
    assert m.currency == "INR"

def test_money_addition():
    m1 = Money("10.50", "INR")
    m2 = Money("5.25", "INR")
    res = m1 + m2
    assert res.amount == Decimal("15.7500")

def test_money_currency_mismatch():
    m1 = Money("10.00", "INR")
    m2 = Money("5.00", "USD")
    with pytest.raises(CurrencyMismatchException):
        _ = m1 + m2

def test_money_multiplication():
    m1 = Money("30.00", "INR")
    res = m1.multiply(Decimal("0.10"))
    assert res.amount == Decimal("3.0000")

def test_money_rounding():
    # half-up rounding to 4 decimal places
    m = Money("33.33335", "INR")
    assert m.amount == Decimal("33.3334")
