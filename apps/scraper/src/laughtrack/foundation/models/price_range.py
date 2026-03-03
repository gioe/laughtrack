from enum import IntEnum


class PriceRange(IntEnum):
    FREE = 9
    LOW = 11  # $1-20
    MEDIUM = 12  # $21-50
    HIGH = 13  # $51-100
    PREMIUM = 14  # >$100
