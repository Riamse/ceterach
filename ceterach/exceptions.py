#!/usr/bin/python3
#-------------------------------------------------------------------------------
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
#-------------------------------------------------------------------------------


class CeterachError(Exception):
    """This is the base exception class for exceptions in Ceterach."""
    code = "py"

if True:
    class NonexistentPageError(CeterachError):
        """Attempted to get information about a page that does not exist."""

    class NonexistentUserError(CeterachError):
        """Attempted to get information about a user that does not exist."""

    class NonexistentRevisionError(CeterachError):
        """Attempted to get information about a revision that does not exist."""

    class InvalidPageError(CeterachError):
        """Attempted to get information about a page whose title is invalid."""

    class ApiError(CeterachError):
        """
        Could not connect to the API and process the response correctly.
        Perhaps the URL was malformed, the site does not exist, the API does not
        support format=json, or the internet connection died.
        """

    class RedirectError(CeterachError):
        """
        Attempted to do something to the page under the assumption that it was
        a redirect, but it is not a redirect, so it didn't work.
        """

    class EditError(CeterachError):
        """An error occurred while editing or doing something else that 'wrote'
        to the API."""

    if True:
        class PermissionsError(EditError):
            """
            Attempted to do something that requires rights you don't have.
            For instance, a non-admin tried to edit a full-protected page.
            """

        class EditConflictError(EditError):
            """
            You got an edit conflict while editing a page.

            This exception will also be raised in the case of delete/recreate conflicts.
            """

        class FilterError(EditError):
            """Base class for edits that are blocked by filters and blacklists."""

        if True:
            class SpamFilterError(FilterError):
                """MediaWiki spam filter blocked the edit."""

            class EditFilterError(FilterError):
                """MediaWiki edit filter blocked the edit."""

__all__ = [x.__name__ for x in vars().values() if isinstance(x, Exception)]
