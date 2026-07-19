from decimal import Decimal, ROUND_HALF_UP
from typing import Any

class CurrencyMismatchException(Exception):
    pass

class Money:
    def __init__(self, amount: Decimal | str | float | int, currency: str = "INR"):
        if isinstance(amount, (str, float, int)):
            self.amount = Decimal(str(amount))
        elif isinstance(amount, Decimal):
            self.amount = amount
        else:
            raise TypeError("Amount must be Decimal, str, float, or int")
            
        self.currency = currency.upper()
        self.round()

    def round(self) -> "Money":
        self.amount = self.amount.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        return self

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise CurrencyMismatchException(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise CurrencyMismatchException(f"Cannot subtract {self.currency} and {other.currency}")
        return Money(self.amount - other.amount, self.currency)

    def multiply(self, multiplier: Decimal | int | float | str) -> "Money":
        mult_dec = Decimal(str(multiplier))
        return Money(self.amount * mult_dec, self.currency)

    def __add__(self, other: "Money") -> "Money":
        return self.add(other)

    def __sub__(self, other: "Money") -> "Money":
        return self.subtract(other)

    def __mul__(self, other: Decimal | int | float | str) -> "Money":
        return self.multiply(other)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency

    def __lt__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise CurrencyMismatchException(f"Cannot compare {self.currency} and {other.currency}")
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise CurrencyMismatchException(f"Cannot compare {self.currency} and {other.currency}")
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise CurrencyMismatchException(f"Cannot compare {self.currency} and {other.currency}")
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise CurrencyMismatchException(f"Cannot compare {self.currency} and {other.currency}")
        return self.amount >= other.amount

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"

    def __repr__(self) -> str:
        return f"Money(amount={self.amount}, currency='{self.currency}')"
