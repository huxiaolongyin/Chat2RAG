from humps import camelize


def camelize_dict(obj):
    """
    Convert the key names in the dictionary to camel case naming
    """
    if isinstance(obj, dict):
        return {camelize(k): camelize_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [camelize_dict(i) for i in list(obj)]
    return obj
