import re

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


def to_lower_camel_case(x):
    """
    转小驼峰法命名, 首单词首字母小写, 其他单词首字母大写, userLoginCount
    :param x:
    :return:
    """
    s = re.sub("_([a-zA-Z])", lambda m: (m.group(1).upper()), x)
    return s[0].lower() + s[1:]
