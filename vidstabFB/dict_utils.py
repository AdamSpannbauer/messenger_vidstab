"""
Utility functions for working with nested dict structures from AWS Lambda Event JSON
"""


def find_item(obj, key):
    """Extract contents of key from nested dict

    If key occurs multiple at different levels of dict then the contents
    of key will be returned at the highest level possible.  If key occurs
    multiple times in 2nd level dicts (or lower) then the output of this function
    will follow the order of the dictionaries top level keys.

    :param obj: Nested dictionary object
    :param key: String containing name of key to extract from obj
    :return: Contents of key in obj. If key is not in obj then None is returned.
    """
    if key in obj:
        return obj[key]
    for k, v in obj.items():
        if isinstance(v, dict):
            item = find_item(v, key)
            if item is not None:
                return item


def keys_exist(obj, keys):
    """Check if 1 or more keys are contained in a nested dict

    :param obj: Nested dictionary object
    :param keys: Iterable containing strings of keys to test if in obj
    :return: True if all keys are present in obj; otherwise False
    """
    for key in keys:
        if find_item(obj, key) is None:
            return False
    return True
