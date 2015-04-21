#!/usr/bin/python3
#-------------------------------------------------------------------------------
# This file is part of Ceterach.
# Copyright (C) 2013 Riamse <riamse@protonmail.com>
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
        self._members = []
        self._subcats = []

    def populate(self, res=None):
        """
        Get the pages that are contained by this category, and subcategories.
        This data is stored in ``._members`` and ``._subcats``.

        If the *res* parameter was supplied, the method will pretend that
        was what the query returned.

        :type res: list
        :param res: The result of an earlier API request (optional). If you
                    are planning to set this parameter to a value
                    other than None, the minimal API request parameters to
                    correctly form this are: ``{"prop": ('revisions', 'info'),
                    "gcmtitle": category_title,
                    "generator": "categorymembers",
                    "rvprop": 'content'}``

        """
        # Empty the members and subcats so we don't have duplicates
        self._members = []
        self._subcats = []
        d = {"prop": ('revisions', 'info'), "gcmtitle": self.title,
             "generator": "categorymembers", "rvprop": 'content'
        }
        res = res or self._api.iterator(use_defaults=False, **d)
        for r in res:
            if r['ns'] == 14:
                # Subcategories should be retrieved with the subcats property
                p = self._api.category(r['title'])
                self._subcats.append(p)
            else:
                p = self._api.page(r['title'])
                p._content = r['revisions'][0]["*"]
                p.load_attributes(r)
                self._members.append(p)

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
