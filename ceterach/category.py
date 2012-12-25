#!/usr/bin/python3
#-------------------------------------------------------------------------------
# This file is part of Ceterach.
# Copyright (C) 2012 Riamse <riamse@protonmail.com>
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

from .page import Page

class Category(Page):

    def load_attributes(self, res=None):
        super().load_attributes(res)
        self._members = ()
        self._subcats = ()

    def populate(self, res=None):
        # Empty the members and subcats so we don't have duplicates
        self._members = ()
        self._subcats = ()
        d = {"prop": ('revisions', 'info'), "gcmtitle": self.title,
             "generator": "categorymembers", "rvprop": 'content'
        }
        res = res or self._api.iterator(**d)
        for r in res:
            if r['ns'] == 14:
                # Subcategories should be retrieved with the subcats property
                p = self._api.category(r['title'])
                self._subcats += (p,)
            else:
                p = self._api.page(r['title'])
                p._content = r['revisions'][0]["*"]
                p.load_attributes(r)
                self._members += (p,)

    @property
    def members(self):
        """
        Iterate over Pages in the category.
        """
        if not hasattr(self, "_members"):
            self.populate()
        return self._members

    @property
    def subcats(self):
        """
        Iterate over Categories in the category.
        """
        if not hasattr(self, "_subcats"):
            self.populate()
        return self._subcats
