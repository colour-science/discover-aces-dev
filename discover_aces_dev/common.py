# -*- coding: utf-8 -*-

import os
from collections import defaultdict

__all__ = ['first_item', 'common_ancestor', 'paths_common_ancestor']


def first_item(iterable, default=None):
    """
    Returns the first item of given iterable.
    :param iterable: Iterable.
    :type iterable: object
    :param default: Default value.
    :type default: object
    :return: First iterable item.
    :rtype: object
    """

    if not iterable:
        return default

    for item in iterable:
        return item


def common_ancestor(*args):
    """
    Gets common ancestor of given iterables.
    Usage::
        >>> common_ancestor(("1", "2", "3"), ("1", "2", "0"), ("1", "2", "3", "4"))
        (u'1', u'2')
        >>> common_ancestor("azerty", "azetty", "azello")
        u'aze'
    :param \*args: Iterables to retrieve common ancestor from.
    :type \*args: [iterable]
    :return: Common ancestor.
    :rtype: iterable
    """

    array = list(map(set, zip(*args)))
    divergence = filter(lambda i: len(i) > 1, array)
    if divergence:
        ancestor = first_item(args)[:array.index(first_item(divergence))]
    else:
        ancestor = min(args)
    return ancestor


def paths_common_ancestor(*args):
    """
    Gets common paths ancestor of given paths.
    Usage::
        >>> paths_common_ancestor("/Users/JohnDoe/Documents", "/Users/JohnDoe/Documents/Test.txt")
        u'/Users/JohnDoe/Documents'
    :param \*args: Paths to retrieve common ancestor from.
    :type \*args: [unicode]
    :return: Common path ancestor.
    :rtype: unicode
    """

    path_ancestor = os.sep.join(
        common_ancestor(*[path.split(os.sep) for path in args]))

    return path_ancestor


def vivification():
    return defaultdict(vivification)


def vivified_to_dict(vivified):
    if isinstance(vivified, defaultdict):
        vivified = {
            key: vivified_to_dict(value)
            for key, value in vivified.items()
        }
    return vivified
