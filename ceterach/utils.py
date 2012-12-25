#!/usr/bin/python3

import re
import sys

__author__ = 'Andrew'

# __all__ and friends are defined at the bottom

def recursion_depth():
    """
    This is an evil hack. Avoid using it whenever possible.
    """
    frame = sys._getframe()
    k = -2
    while True:
        try:
            frame = frame.f_back
        except AttributeError:
            return k
        k += 1
#    k = 0
#    while True:
#        try:
#            sys._getframe(k)
#        except ValueError:
#            # The very act of calling a function sends us one level deeper, so
#            # we have to return one_level_too_high - 1 - 1
#            return k - 2
#        k += 1

def flattened(nested: (list, tuple)) -> list:
    """
    For the sake of simplicity, `list` will refer to both lists and tuples.
    Convert a list of lists (which may possibly contain more lists) into a
    single one-dimensional list.

    This is comparable to the Perl process of putting an array in an array.
    """
    one_d = []
    for x in nested:
        if isinstance(x, (list, tuple)):
            one_d.extend(flattened(x))
        else:
            one_d.append(x)
    return one_d

# Regex to match IPv4 and IPv6 addresses
v4 = re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
                r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b")
v6 = re.compile(r"^\s*((([0-9A-Fa-f]{1,4}:){7}"
                r"(([0-9A-Fa-f]{1,4})|:))|(([0-9A-Fa-f]{1,4}:){6}"
                r"(:|((25[0-5]|2[0-4]\d|[01]?\d{1,2})"
                r"(\.(25[0-5]|2[0-4]\d|[01]?\d{1,2})){3})"
                r"|(:[0-9A-Fa-f]{1,4})))|(([0-9A-Fa-f]{1,4}:){5}"
                r"((:((25[0-5]|2[0-4]\d|[01]?\d{1,2})"
                r"(\.(25[0-5]|2[0-4]\d|[01]?\d{1,2})){3})?)"
                r"|((:[0-9A-Fa-f]{1,4}){1,2})))|(([0-9A-Fa-f]{1,4}:){4}"
                r"(:[0-9A-Fa-f]{1,4}){0,1}"
                r"((:((25[0-5]|2[0-4]\d|[01]?\d{1,2})"
                r"(\.(25[0-5]|2[0-4]\d|[01]?\d{1,2})){3})?)"
                r"|((:[0-9A-Fa-f]{1,4}){1,2})))|(([0-9A-Fa-f]{1,4}:){3}"
                r"(:[0-9A-Fa-f]{1,4}){0,2}"
                r"((:((25[0-5]|2[0-4]\d|[01]?\d{1,2})"
                r"(\.(25[0-5]|2[0-4]\d|[01]?\d{1,2})){3})?)"
                r"|((:[0-9A-Fa-f]{1,4}){1,2})))|(([0-9A-Fa-f]{1,4}:){2}"
                r"(:[0-9A-Fa-f]{1,4}){0,3}"
                r"((:((25[0-5]|2[0-4]\d|[01]?\d{1,2})"
                r"(\.(25[0-5]|2[0-4]\d|[01]?\d{1,2})){3})?)"
                r"|((:[0-9A-Fa-f]{1,4}){1,2})))|(([0-9A-Fa-f]{1,4}:)"
                r"(:[0-9A-Fa-f]{1,4}){0,4}"
                r"((:((25[0-5]|2[0-4]\d|[01]?\d{1,2})"
                r"(\.(25[0-5]|2[0-4]\d|[01]?\d{1,2})){3})?)"
                r"|((:[0-9A-Fa-f]{1,4}){1,2})))|(:(:[0-9A-Fa-f]{1,4}){0,5}"
                r"((:((25[0-5]|2[0-4]\d|[01]?\d{1,2})"
                r"(\.(25[0-5]|2[0-4]\d|[01]?\d{1,2})){3})?)"
                r"|((:[0-9A-Fa-f]{1,4}){1,2})))"
                r"|(((25[0-5]|2[0-4]\d|[01]?\d{1,2})"
                r"(\.(25[0-5]|2[0-4]\d|[01]?\d{1,2})){3})))(%.+)?\s*$")

class IPv4Address:
    """A fake class that represents an IPv4 address"""
    def __init__(self, address): pass

class IPv6Address:
    """A fake class that represents an IPv6 address"""
    def __init__(self, address): pass

def ip_address(address: str):
    err = "{0!r} does not appear to be an IPv4 or IPv6 address"
    if v4.match(address):
        return IPv4Address(address)
    elif v6.match(address):
        return IPv6Address(address)
    else:
        raise ValueError(err.format(address))

# The ultra-lazy way of making __all__ contain only functions
__all__ = [v.__name__ for v in vars().values() if hasattr(v, "__call__")]
