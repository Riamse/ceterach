#!/usr/bin/python3
# ------------------------------------------------------------------------------
# This file is part of Ceterach.
# Copyright (C) 2013 Andrew Wang <andrewwang43@gmail.com>
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
# ------------------------------------------------------------------------------

from urllib.parse import quote
import re

from .page import Page
from . import exceptions as exc
from .utils import blah_decorate

__all__ = ["File"]

def decorate(meth):
    msg = "File {0!r} does not exist"
    attr = "title"
    err = exc.NonexistentPageError
    return blah_decorate(meth, msg, attr, err)

class File(Page):

    def load_attributes(self, res=None):
        i = self._api.iterator
        prop = 'info', 'revisions', 'categories', 'imageinfo'
        rvprop = 'user', 'content'
        iiprop = 'size', 'mime', 'sha1', 'url', 'user'
        res = res or next(i(use_defaults=False,
                            prop=prop, iiprop=iiprop, rvprop=rvprop,
                            rvlimit=1, rvdir="older", titles=self._title))
        super().load_attributes(res=res)
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
        """Upload an arbitrary file object to this file page.

        :type fileobj: file
        :param fileobj: The file that will be uploaded.
        :type text: str
        :param text: The description page for the file page.
        :type summary: str
        :param summary: The upload summary to be used.
        :type watch: bool
        :param watch: Set this to True in order to put this page on the
                      watchlist when this file is uploaded, otherwise False.
        :type key: str
        :param key: Session key returned by a previous upload that failed due to warnings.
        """
        contents = fileobj.read()
        post_params = {
            "filename": self.title,
            "text": text,
            "comment": summary,
            "watch": watch,
            "ignorewarnings": True,
            "file": contents,
            "token": self._api.tokens['edit']
        }
        if key:
            post_params['sessionkey'] = key
        res = self._api.call(post_params)
        if 'upload' in res and res['upload']['result'] == "Success":
            # Some attributes are now out of date
            del self._dimensions, self._uploader, self._hash
            self._exists = True
        return res

    def url(self, width=None, height=None) -> str:
        """Returns a direct link to the file.

        You may specify either the width or the height, but not both.

        :type width: int
        :param width: The desired width of the image.
        :type height: int
        :param height: The desired height of the image.
        """
        if not self.exists:
            err = "File {0!r} does not exist"
            raise exc.NonexistentPageError(err.format(self.title))
        if width and height:
            raise TypeError("Cannot specify both width and height")
        t = quote(self.title.replace(" ", "_"), safe=":/")[5:]
        url = self._url
        url = re.sub(r"(/[a-z0-9]/[a-z0-9]{2}/)",
                     r"/thumb\1", url[::-1].replace('/' + t[::-1], '')[::-1])
        if width:
            url += "/" + str(width) + "px-" + t
        elif height:
            #  width                 X
            # -------    =     -------------
            # height           param(height)
            d = self.dimensions
            width = int(d[0] * height / d[1] + 0.5)
            url += "/" + str(width) + "px-" + t
        return url

    @property
    @decorate
    def mime(self) -> str:
        """The mime type of the file."""
        return "_mime"

    @property
    @decorate
    def hash(self) -> str:
        """The SHA1 hash of the file content."""
        return "_hash"

    @property
    @decorate
    def size(self) -> int:
        """The file size in bytes."""
        return "_size"

    @property
    @decorate
    def dimensions(self) -> tuple:
        """A tuple of integers, in the format of ``(width, height)``."""
        return "_dimensions"

    @property
    @decorate
    def uploader(self):
        """
        :returns: A User object representing the user who uploaded the most
                  recent revision of the file.
        """
        return "_uploader"
