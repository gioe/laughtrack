"""Pure list manipulation utilities with no domain dependencies."""

from typing import Any, Callable, Dict, List, Optional

from laughtrack.foundation.models.types import JSONDict, T


class ListUtils:
    """Pure list manipulation utilities."""

    @staticmethod
    def contains_any(source: List[Any], target: List[Any]) -> bool:
        """Check if any element from target list exists in source list."""
        return any(item in target for item in source)

    @staticmethod
    def deduplicate_by_key(items: List[JSONDict], key: str) -> List[JSONDict]:
        """Deduplicate a list of dictionaries by a specific key."""
        seen = set()
        result = []

        for item in items:
            if item.get(key) not in seen:
                seen.add(item.get(key))
                result.append(item)

        return result

    @staticmethod
    def deduplicate_by_function(items: List[T], key_func: Callable[[T], Any]) -> List[T]:
        """
        Deduplicate a list using a key function.

        Args:
            items: List of items to deduplicate
            key_func: Function that returns a unique key for each item

        Returns:
            List with duplicates removed, preserving original order
        """
        seen = set()
        result = []

        for item in items:
            key = key_func(item)
            if key not in seen:
                seen.add(key)
                result.append(item)

        return result

    @staticmethod
    def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
        """Split a list into chunks of specified size."""
        return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]

    @staticmethod
    def flatten(nested_list: Optional[List[List[Any]]]) -> List[Any]:
        """Flatten a nested list structure."""
        if not nested_list:
            return []
        return [item for sublist in nested_list for item in sublist]

    @staticmethod
    def flatten_deep(nested_list: List[Any]) -> List[Any]:
        """Recursively flatten a deeply nested list structure."""
        result = []
        for item in nested_list:
            if isinstance(item, list):
                result.extend(ListUtils.flatten_deep(item))
            else:
                result.append(item)
        return result

    @staticmethod
    def partition(items: List[T], predicate: Callable[[T], bool]) -> tuple[List[T], List[T]]:
        """
        Partition a list into two lists based on a predicate.

        Args:
            items: List to partition
            predicate: Function that returns True for items to include in first list

        Returns:
            Tuple of (items matching predicate, items not matching predicate)
        """
        true_items = []
        false_items = []

        for item in items:
            if predicate(item):
                true_items.append(item)
            else:
                false_items.append(item)

        return true_items, false_items

    @staticmethod
    def group_by(items: List[T], key_func: Callable[[T], Any]) -> Dict[Any, List[T]]:
        """
        Group items by a key function.

        Args:
            items: List of items to group
            key_func: Function that returns a grouping key for each item

        Returns:
            Dictionary mapping keys to lists of items
        """
        groups: Dict[Any, List[T]] = {}

        for item in items:
            key = key_func(item)
            if key not in groups:
                groups[key] = []
            groups[key].append(item)

        return groups

    @staticmethod
    def find_first(items: List[T], predicate: Callable[[T], bool]) -> Optional[T]:
        """
        Find the first item matching a predicate.

        Args:
            items: List to search
            predicate: Function that returns True for the desired item

        Returns:
            First matching item or None if not found
        """
        for item in items:
            if predicate(item):
                return item
        return None

    @staticmethod
    def find_all(items: List[T], predicate: Callable[[T], bool]) -> List[T]:
        """
        Find all items matching a predicate.

        Args:
            items: List to search
            predicate: Function that returns True for desired items

        Returns:
            List of all matching items
        """
        return [item for item in items if predicate(item)]

    @staticmethod
    def safe_get(lst: List[T], index: int, default: Optional[T] = None) -> Optional[T]:
        """
        Safely get an item from a list by index.

        Args:
            lst: List to access
            index: Index to retrieve
            default: Default value if index is out of bounds

        Returns:
            Item at index or default value
        """
        try:
            return lst[index]
        except (IndexError, TypeError):
            return default

    @staticmethod
    def batch_process(items: List[T], batch_size: int, processor: Callable[[List[T]], List[Any]]) -> List[Any]:
        """
        Process a list in batches.

        Args:
            items: Items to process
            batch_size: Size of each batch
            processor: Function to process each batch

        Returns:
            Flattened list of all batch results
        """
        results = []
        chunks = ListUtils.chunk_list(items, batch_size)

        for chunk in chunks:
            batch_result = processor(chunk)
            if isinstance(batch_result, list):
                results.extend(batch_result)
            else:
                results.append(batch_result)

        return results
