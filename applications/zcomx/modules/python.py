#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
python.py

Classes that subclass or augment python builtins.

"""


class List(list):
    """Class representing a list with extras."""

    def reshape(self, shape):
        """Reshape the list.

        Args:
            shape: tuple, (rows, cols) The dimensions of the reshaped list.
                If both rows and cols are None, the list is returned unchanged.
                If one is None but not the other, the value of the other is
                determined by the number of elements in the list. For example,
                if the list has 20 elements, and shape = (None, 4), then rows
                is calculated as 5.
                If both are not None, then a list with the desired shape is
                returned, unless there are not enough items in the list to fill
                the shape, in which case rows are filled one column at a time.
                Some rows may be empty if there are not enough items.
                If the list contains more items than the shape requires, extra
                items are ignored and not included in the returned list.

        Returns:
            list of lists
        """
        rows, columns = shape

        def incomplete(items):
            """Determine the number of incomplete rows or columns"""
            return 0 if len(self) % items == 0 else 1

        if rows is None and columns is None:
            return self
        elif rows is None:
            rows = len(self) / columns + incomplete(columns)
        elif columns is None:
            columns = len(self) / rows + incomplete(rows)
        reshaped = []
        for count, item in enumerate(self):
            row = int(count / columns)
            if row >= rows:
                continue
            col = count % columns
            if col >= columns:
                continue
            if len(reshaped) <= row:
                reshaped.append([])
            reshaped[row].append(item)
        return reshaped


def from_dict_by_keys(data_dict, map_list):
    """Get a value from a dict by following map list of keys.
    Example:
        dict = {'a': {'aa': {'aaa': 111, 'aab': 112}}}
        from_dict_by_keys(dict, ['a', 'aa', 'aaa'])    # Returns 111
        from_dict_by_keys(dict, ['a', 'aa', 'aab'])    # Returns 112

    Args:
        data_dict: dict
        map_list: list of keys of dict
    Returns:
        mixed: value of dict element.
    """
    data = dict(data_dict)
    for k in map_list:
        data = data[k]
    return data
