#!/usr/bin/python3
#-------------------------------------------------------------------------------
# This file is part of Ceterach.
# Copyright (C) 2012 Andrew Wang <andrewwang43@gmail.com>
#
# Ceterach is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# Ceterach is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Ceterach.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

import re
import datetime
import functools

# __all__ and friends are defined at the bottom

class DictThatReturnsNoneInsteadOfRaisingKeyError(dict):
    def __getitem__(self, item):
        return super().get(item, None)


#def decorate(attr):
#    def wrapped(self):
#        return "getattr({!r}, {!r})".format(self, attr)
#        if not hasattr(self, attr): self.load_attributes()
#        return getattr(self, attr)
#    return lambda the_func: wrapped

def blah_decorate(meth, message, message_attr, error):
    attr = meth(0) # The method should be returning the attribute to get
    @functools.wraps(meth)
    def wrapped(self):
        if not hasattr(self, attr): self.load_attributes()
        try:
            return getattr(self, attr)
        except AttributeError:
            err = message.format(getattr(self, message_attr))
        raise error(err)
    return wrapped

def addprop(inst, name, method): # http://stackoverflow.com/a/2954373/1133718
    cls = type(inst)
    if not hasattr(cls, '__perinstance'):
        cls = type(cls.__name__, (cls,), {})
        cls.__perinstance = True
        inst.__class__ = cls
    setattr(cls, name, property(method))

def isostrptime(stamp):
    """I'm lazy, and can never remember the format string"""
    return datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")

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
