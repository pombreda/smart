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
from gepeto.backends.rpm.pm import RPMPackageManager
#from rpmver import checkdep, vercmp, splitarch
from crpmver import checkdep, vercmp, splitarch
from gepeto.util.strtools import isRegEx
from gepeto.matcher import Matcher
from gepeto.cache import *
import string
import os, re

from rpm import archscore

__all__ = ["RPMPackage", "RPMProvides", "RPMNameProvides", "RPMPreRequires",
           "RPMRequires", "RPMUpgrades", "RPMConflicts", "RPMObsoletes"]

class RPMMatcher(Matcher):

    def __init__(self, str):
        Matcher.__init__(self, str)
        self._options = [] # (name, version)
        # First, try to match the whole thing against the name.
        if isRegEx(str):
            name = re.compile(str)
        else:
            name = str
        self._options.append((name, None))
        tokens = str.split("-")
        if len(tokens) > 1:
            # Then, consider the last section as the version.
            name = "-".join(tokens[:-1])
            if isRegEx(name):
                name = re.compile(name)
            version = tokens[-1]
            if isRegEx(version):
                if ":" not in version and version[0].isdigit():
                    version = "(?:\d+:)?"+version
                version = re.compile(version)
            self._options.append((name, version))
            # Finally, consider last two sections as the version.
            if len(tokens) > 2:
                name = "-".join(tokens[:-2])
                if isRegEx(name):
                    name = re.compile(name)
                version = "-".join(tokens[-2:])
                if isRegEx(version):
                    if ":" not in version and version[0].isdigit():
                        version = "(?:\d+:)?"+version
                    version = re.compile(version)
                self._options.append((name, version))

    def matches(self, obj):
        for name, version in self._options:
            if type(name) is str:
                if name != obj.name:
                    continue
            else:
                if not name.match(obj.name):
                    continue
            if version:
                if type(version) is str:
                    if ":" not in version and ":" in obj.version:
                        ov = obj.version
                        version = ov[:ov.find(":")+1]+version
                    objver, objarch = splitarch(obj.version)
                    if vercmp(version, objver) != 0:
                        ver, arch = splitarch(version)
                        if arch != objarch or vercmp(ver, objver) != 0:
                            continue
                elif not version.match(obj.version):
                    continue
            return True

class RPMPackage(Package):

    packagemanager = RPMPackageManager
    matcher = RPMMatcher

    ignoreprereq = False

    def equals(self, other):
        if not self.ignoreprereq:
            return Package.equals(self, other)
        fk = dict.fromkeys
        if (self.name != other.name or
            self.version != other.version or
            len(self.provides) != len(other.provides) or
            len(self.upgrades) != len(other.upgrades) or
            len(self.conflicts) != len(other.conflicts) or
            fk(self.provides) != fk(other.provides) or
            fk(self.upgrades) != fk(other.upgrades) or
            fk(self.conflicts) != fk(other.conflicts)):
            return False
        sreqs = fk(self.requires)
        oreqs = fk(other.requires)
        if sreqs != oreqs:
            for sreq in sreqs:
                if sreq in oreqs:
                    continue
                for oreq in oreqs:
                    if (sreq.name == oreq.name and
                        sreq.relation == oreq.relation and
                        sreq.version == oreq.version):
                        break
                else:
                    return False
            for oreq in oreqs:
                if oreq in sreqs:
                    continue
                for sreq in sreqs:
                    if (sreq.name == oreq.name and
                        sreq.relation == oreq.relation and
                        sreq.version == oreq.version):
                        break
                else:
                    return False
        return True

    def coexists(self, other):
        if not isinstance(other, RPMPackage):
            return True
        if sysconf.testFlag("multi-arch", self):
            return True
        if not sysconf.testFlag("multi-version", self):
            return False
        selfver, selfarch = splitarch(self.version)
        otherver, otherarch = splitarch(other.version)
        return selfver != otherver

    def matches(self, relation, version):
        if not relation:
            return True
        selfver, selfarch = splitarch(self.version)
        ver, arch = splitarch(version)
        return checkdep(selfver, relation, ver)

    def __cmp__(self, other):
        rc = -1
        if type(other) is RPMPackage:
            rc = cmp(self.name, other.name)
            if rc == 0 and self.version != other.version:
                selfver, selfarch = splitarch(self.version)
                otherver, otherarch = splitarch(other.version)
                if selfver != otherver:
                    rc = vercmp(self.version, other.version)
                if rc == 0:
                    rc = -cmp(archscore(selfarch), archscore(otherarch))
        return rc

class RPMProvides(Provides): pass
class RPMNameProvides(RPMProvides): pass

class RPMDepends(Depends):

    def matches(self, prv):
        if self.name != prv.name or not isinstance(prv, RPMProvides):
            return False
        if not self.version or not prv.version:
            return True
        return checkdep(prv.version, self.relation, self.version)

class RPMPreRequires(RPMDepends,PreRequires): pass
class RPMRequires(RPMDepends,Requires): pass
class RPMUpgrades(RPMDepends,Upgrades): pass
class RPMConflicts(RPMDepends,Conflicts): pass

class RPMObsoletes(Depends):

    def matches(self, prv):
        if prv.__class__ != RPMNameProvides:
            return False
        if self.name != prv.name:
            return False
        if self.version and not prv.version:
            return False
        if not self.version and prv.version:
            return True
        return checkdep(prv.version, self.relation, self.version)

# vim:ts=4:sw=4:et