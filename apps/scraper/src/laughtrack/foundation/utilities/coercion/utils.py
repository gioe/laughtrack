"""Reusable coercion helpers for safe type conversion across the codebase."""

from typing import Any, Optional, List


class CoercionUtils:
    @staticmethod
    def to_int(value: Any, default: int = 0) -> int:
        try:
            if value is None:
                return default
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def to_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "y"}
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    @staticmethod
    def str_or_default(value: Any, default: str = "") -> str:
        return str(value) if value is not None else default

    @staticmethod
    def str_or_none(value: Any) -> Optional[str]:
        if value is None:
            return None
        s = str(value)
        return s if s.strip() != "" else None

    @staticmethod
    def to_str_list(value: Any) -> List[str]:
        """Coerce a value into a list of strings.

        - None -> []
        - list -> [str_or_default(v) for v in list]
        - str -> [value]
        - anything else -> []
        """
        if value is None:
            return []
        if isinstance(value, list):
            return [CoercionUtils.str_or_default(v) for v in value]
        if isinstance(value, str):
            return [CoercionUtils.str_or_default(value)]
        return []
