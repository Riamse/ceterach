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

import functools

from .page import Page
from . import exceptions as exc

__all__ = ["File"]

def blah(obj, attr):
    if not hasattr(obj, attr):
        obj.load_attributes()
    return getattr(obj, attr)

def blah_with_exc(obj, attr):
    if obj.exists:
        return getattr(obj, attr)
    else:
        err = "File {0!r} does not exist".format(obj.title)
        raise exc.NonexistentPageError(err)

def decorate(meth):
    attr = meth(0) # The method should be returning the attribute to get
    @functools.wraps(meth)
    def wrapped(self):
        if not hasattr(self, attr): self.load_attributes()
        try:
            return getattr(self, attr)
        except AttributeError:
            err = "User {0!r} does not exist".format(self.name)
        raise exc.NonexistentUserError(err)
    return wrapped

class File(Page):

    def load_attributes(self, res=None):
        i = self._api.iterator
        prop = ('info', 'revisions', 'categories', 'imageinfo')
        rvprop = ('user', 'content')
        iiprop = ('size', 'mime', 'sha1', 'url', 'user')
        res = res or list(i(1, prop=prop, iiprop=iiprop, rvprop=rvprop,
                            rvlimit=1, rvdir="older", titles=self._title))[0]
        super().load_attributes(res=res)
        self.repository = res['imagerepository']
        try:
            imageinfo = res['imageinfo'][0]
        except KeyError:
            # This file doesn't exist
            return
        self._url = imageinfo['url']
        self._mime = imageinfo['mime']
        self._hash = imageinfo['sha1']
        self._size = imageinfo['size']
        self._uploader = self._api.user(imageinfo['user'])
        self._dimensions = imageinfo['width'], imageinfo['height']

    def upload(self, fileobj, text, summary, watch=False, key=''):
        fileobj.seek(0)
        contents = fileobj.read()
        post_params = {"filename": self.title, "text": text,
                       "comment": summary, "watch": watch,
                       "ignorewarnings": True, "file": contents,
                       "token": self._api.tokens['edit']
        }
        if key:
            post_params['sessionkey'] = key
        res = self._api.call(**post_params)
        if 'upload' in res and res['upload']['result'] == "Success":
            # Some attributes are now out of date
            del self._dimensions, self._uploader, self._hash
            self._exists = True
        return res

    def download(self, fileobj=None, width=None, height=None):
        # TODO: Width and height
        if not self.exists:
            err = "File {0!r} does not exist"
            raise exc.NonexistentPageError(err.format(self.title))
        if width and height:
            raise TypeError("Cannot specify both width and height")
        res = self._api.opener.get(self.url)
        with fileobj or open(self.title.partition(":")[-1], "wb") as fileobj:
            fileobj.write(res.content)

    @property
    @decorate
    def url(self) -> str:
        return "_url"

    @property
    @decorate
    def mime(self) -> str:
        return "_mime"

    @property
    @decorate
    def hash(self) -> str:
        return "_hash"

    @property
    @decorate
    def size(self) -> int:
        return "_size"

    @property
    @decorate
    def dimensions(self) -> tuple:
        """
        :returns: (width, height)
        """
        return "_dimensions"

    @property
    @decorate
    def uploader(self):
        """
        :returns: A User object representing the user who uploaded the most
        recent revision of the file.
        """
        return "_uploader"
