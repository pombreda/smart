#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# This file is part of Gepeto.
#
# Gepeto is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Gepeto is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gepeto; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from cpm.backends.rpm.header import RPMHeaderListLoader
from cpm.repository import Repository
from cpm import *
import posixpath

class RPMHeaderListRepository(Repository):

    def __init__(self, type, name, hdlurl, baseurl):
        Repository.__init__(self, type, name)
        
        self._hdlurl = hdlurl
        self._baseurl = baseurl

    def fetch(self, fetcher):
        fetcher.reset()
        fetcher.enqueue(self._hdlurl)
        fetcher.setInfo(self._hdlurl, uncomp=True)
        fetcher.run("header list for '%s'" % self._name)
        failed = fetcher.getFailedSet()
        if failed:
            iface.warning("failed acquiring header list for '%s': %s" %
                          (self._name, failed[self._hdlurl]))
            iface.debug("%s: %s" % (self._hdlurl, failed[self._hdlurl]))
        else:
            localpath = fetcher.getSucceeded(self._hdlurl)
            self._loader = RPMHeaderListLoader(localpath, self._baseurl)
            self._loader.setRepository(self)

def create(reptype, data):
    name = None
    hdlurl = None
    baseurl = None
    if type(data) is dict:
        name = data.get("name")
        hdlurl = data.get("hdlurl")
        baseurl = data.get("baseurl")
    elif hasattr(data, "tag") and data.tag == "repository":
        node = data
        name = node.get("name")
        for n in node.getchildren():
            if n.tag == "hdlurl":
                hdlurl = n.text
            elif n.tag == "baseurl":
                baseurl = n.text
    else:
        raise RepositoryDataError
    if not name:
        raise Error, "repository of type '%s' has no name" % reptype
    if not hdlurl:
        raise Error, "repository '%s' has no hdlurl" % name
    if not baseurl:
        raise Error, "repository '%s' has no baseurl" % name
    return RPMHeaderListRepository(reptype, name, hdlurl, baseurl)

# vim:ts=4:sw=4:et
