"""
Money module for IB Wallet.

Provides the Money class for handling monetary values with currency support.
Uses Decimal for precise arithmetic without floating-point errors.
"""

from decimal import Decimal, InvalidOperation
from typing import Dict, Union


class Money:
    """
    Represents a monetary value with currency support.
    
    Uses Decimal for precise arithmetic without floating-point errors.
    Supports INR (Indian Rupee) and CHF (Swiss Franc) currencies.
    
    Attributes:
        amount: The monetary amount as a Decimal
        currency: The currency code (INR or CHF)
    """
    
    SUPPORTED_CURRENCIES = {"INR", "CHF"}
    
    def __init__(self, amount: Union[str, int, float, Decimal], currency: str) -> None:
        """
        Initialize a Money object.
        
        Args:
            amount: The monetary amount (will be converted to Decimal for precision)
            currency: The currency code (must be INR or CHF)
            
        Raises:
            ValueError: If currency is not supported or amount is invalid
            TypeError: If amount cannot be converted to Decimal
        """
        if currency not in self.SUPPORTED_CURRENCIES:
            raise ValueError(
                f"Unsupported currency: {currency}. "
                f"Supported currencies: {', '.join(sorted(self.SUPPORTED_CURRENCIES))}"
            )
        
        try:
            self.amount: Decimal = Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError) as e:
            raise ValueError(f"Invalid amount: {amount}") from e

        self.currency: str = currency

    @classmethod
    def zero(cls, currency: str) -> "Money":
        """
        Create a Money object with zero amount.
        
        Args:
            currency: The currency code (must be INR or CHF)
            
        Returns:
            A Money object with amount 0 in the specified currency
            
        Raises:
            ValueError: If currency is not supported
            
        Example:
            >>> money = Money.zero("INR")
            >>> money.amount
            Decimal('0')
            >>> money.currency
            'INR'
        """
        return cls(Decimal("0"), currency)
    
    def __add__(self, other: "Money") -> "Money":
        """
        Add two Money objects.
        
        Args:
            other: Another Money object to add
            
        Returns:
            A new Money object with the sum
            
        Raises:
            TypeError: If other is not a Money object
            ValueError: If currencies don't match
        """
        if not isinstance(other, Money):
            raise TypeError(
                f"unsupported operand type(s) for +: 'Money' and '{type(other).__name__}'"
            )
        
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot add different currencies: {self.currency} and {other.currency}"
            )
        
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: "Money") -> "Money":
        """
        Subtract two Money objects.
        
        Args:
            other: Another Money object to subtract
            
        Returns:
            A new Money object with the difference
            
        Raises:
            TypeError: If other is not a Money object
            ValueError: If currencies don't match
        """
        if not isinstance(other, Money):
            raise TypeError(
                f"unsupported operand type(s) for -: 'Money' and '{type(other).__name__}'"
            )
        
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot subtract different currencies: {self.currency} and {other.currency}"
            )
        
        return Money(self.amount - other.amount, self.currency)
    
    def __eq__(self, other: object) -> bool:
        """
        Check equality of two Money objects.
        
        Two Money objects are equal if both their amount and currency are equal.
        
        Args:
            other: Another object to compare with
            
        Returns:
            True if both amount and currency are equal, False otherwise
        """
        if not isinstance(other, Money):
            return False
        
        return self.amount == other.amount and self.currency == other.currency
    
    def __lt__(self, other: "Money") -> bool:
        """
        Check if this Money object is less than another.
        
        Args:
            other: Another Money object to compare with
            
        Returns:
            True if this amount is less than the other
            
        Raises:
            TypeError: If other is not a Money object
            ValueError: If currencies don't match
        """
        if not isinstance(other, Money):
            raise TypeError(
                f"'<' not supported between instances of 'Money' and '{type(other).__name__}'"
            )
        
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot compare different currencies: {self.currency} and {other.currency}"
            )
        
        return self.amount < other.amount
    
    def __le__(self, other: "Money") -> bool:
        """
        Check if this Money object is less than or equal to another.
        
        Args:
            other: Another Money object to compare with
            
        Returns:
            True if this amount is less than or equal to the other
            
        Raises:
            TypeError: If other is not a Money object
            ValueError: If currencies don't match
        """
        if not isinstance(other, Money):
            raise TypeError(
                f"'<=' not supported between instances of 'Money' and '{type(other).__name__}'"
            )
        
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot compare different currencies: {self.currency} and {other.currency}"
            )
        
        return self.amount <= other.amount
    
    def __gt__(self, other: "Money") -> bool:
        """
        Check if this Money object is greater than another.
        
        Args:
            other: Another Money object to compare with
            
        Returns:
            True if this amount is greater than the other
            
        Raises:
            TypeError: If other is not a Money object
            ValueError: If currencies don't match
        """
        if not isinstance(other, Money):
            raise TypeError(
                f"'>' not supported between instances of 'Money' and '{type(other).__name__}'"
            )
        
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot compare different currencies: {self.currency} and {other.currency}"
            )
        
        return self.amount > other.amount
    
    def __ge__(self, other: "Money") -> bool:
        """
        Check if this Money object is greater than or equal to another.
        
        Args:
            other: Another Money object to compare with
            
        Returns:
            True if this amount is greater than or equal to the other
            
        Raises:
            TypeError: If other is not a Money object
            ValueError: If currencies don't match
        """
        if not isinstance(other, Money):
            raise TypeError(
                f"'>=' not supported between instances of 'Money' and '{type(other).__name__}'"
            )
        
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot compare different currencies: {self.currency} and {other.currency}"
            )
        
        return self.amount >= other.amount
    
    def is_zero(self) -> bool:
        """
        Check if the amount is zero.
        
        Returns:
            True if amount is zero, False otherwise
            
        Example:
            >>> Money("0", "INR").is_zero()
            True
            >>> Money("100", "INR").is_zero()
            False
        """
        return self.amount == Decimal("0")
    
    def is_negative(self) -> bool:
        """
        Check if the amount is negative.
        
        Returns:
            True if amount is negative, False otherwise
            
        Example:
            >>> Money("-50", "INR").is_negative()
            True
            >>> Money("50", "INR").is_negative()
            False
        """
        return self.amount < Decimal("0")
    
    def __repr__(self) -> str:
        """
        Return the official string representation of the Money object.
        
        Returns:
            A string representation in the format: Money(amount, 'currency')
        """
        return f"Money({self.amount}, '{self.currency}')"
    
    def __str__(self) -> str:
        """
        Return human-readable string representation of the Money object.
        
        Returns:
            A formatted string with amount and currency code
        """
        return f"{self.amount} {self.currency}"
    
    def to_dict(self) -> Dict[str, str]:
        """
        Convert Money object to dictionary representation.
        
        The amount is represented as a string to preserve decimal precision.
        
        Returns:
            A dictionary with 'amount' and 'currency' keys
            
        Example:
            >>> money = Money("100.50", "INR")
            >>> money.to_dict()
            {'amount': '100.50', 'currency': 'INR'}
        """
        return {
            "amount": str(self.amount),
            "currency": self.currency
        }
