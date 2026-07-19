class DomainException(Exception):
    """Base exception for all domain logic violations."""
    pass

class EntityNotFoundException(DomainException):
    """Raised when a requested database row does not exist."""
    pass

class InsufficientFundsException(DomainException):
    """Raised when a user attempts to withdraw more than their withdrawable balance."""
    pass

class CooldownActiveException(DomainException):
    """Raised when a user attempts to initiate a second withdrawal within 24 hours."""
    pass

class InvalidSaleStatusException(DomainException):
    """Raised when attempting an operation on a sale with an invalid state."""
    pass

class InvalidWithdrawalStatusException(DomainException):
    """Raised when transitioning a withdrawal into an incompatible status."""
    pass

class IdempotencyConflictException(DomainException):
    """Raised when an idempotency key is reused but with modified parameters."""
    pass

class UnauthorizedException(DomainException):
    """Raised when authentication credentials are missing or invalid."""
    pass

class ForbiddenException(DomainException):
    """Raised when a user lacks the required RBAC role permissions."""
    pass

class ConcurrentModificationException(DomainException):
    """Raised when an optimistic lock version mismatch is encountered."""
    pass
