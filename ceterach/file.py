#!/usr/bin/python3
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# This file is part of Ceterach.
# Copyright (C) 2012 Andrew Wang <andrewwang43@gmail.com>
#
# Ceterach is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
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

from .page import Page
from . import exceptions as exc

class File(Page):

    def load_attributes(self, res=None):
        i = self._api.iterator
        prop = ('info', 'revisions', 'categories', 'imageinfo')
        rvprop = ('user', 'content')
        iiprop = ('size', 'mime', 'sha1', 'url', 'user')
        res = res or list(i(1, prop=prop, iiprop=iiprop, rvprop=rvprop,
                            rvlimit=1, rvdir="older", titles=self._title))[0]
        imageinfo = res['imageinfo'][0]
        self.repository = res['imagerepository']
        self._url = imageinfo['url']
        self._mime = imageinfo['mime']
        self._hash = imageinfo['sha1']
        self._size = imageinfo['size']
        self._uploader = self._api.user(imageinfo['user'])
        self._dimensions = imageinfo['width'], imageinfo['height']
        super().load_attributes(res=res)

    def upload(self, fileobj, text, summary, watch=False, key=''):
        if not 'r' in fileobj.mode:
            raise ValueError("The file object must be readable")
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
            del self._dimensions, self._uploader, self._hash
            self._exists = True
        return res

    def download(self, fileobj=None, width=None, height=None):
        if width and height:
            raise TypeError("Cannot specify both width and height")
        res = self._api.opener.get(self.url)
        with fileobj or open(self.title.partition(":")[-1], "wb") as fileobj:
            fileobj.write(res.content)

    @property
    def url(self):
        if not hasattr(self, "_url"):
            self.load_attributes()
        return self._url

    @property
    def mime(self):
        if not hasattr(self, "_mime"):
            self.load_attributes()
        return self._mime

    @property
    def hash(self):
        if not hasattr(self, "_hash"):
            self.load_attributes()
        return self._hash

    @property
    def size(self):
        if not hasattr(self, "_size"):
            self.load_attributes()
        return self._size

    @property
    def dimensions(self):
        if not hasattr(self, "_dimensions"):
            self.load_attributes()
        return self._dimensions

    @property
    def uploader(self):
        if not hasattr(self, "_uploader"):
            self.load_attributes()
        return self._uploader
