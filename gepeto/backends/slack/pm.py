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
from gepeto.const import INSTALL, REMOVE
from gepeto.pm import PackageManager
from gepeto import *
import commands

class SlackPackageManager(PackageManager):

    def commit(self, changeset, pkgpaths):

        prog = iface.getProgress(self, True)
        prog.start()
        prog.setTopic("Committing transaction...")
        prog.show()

        install = {}
        remove = {}
        for pkg in changeset:
            if changeset[pkg] is INSTALL:
                install[pkg] = True
            else:
                remove[pkg] = True
        upgrade = {}
        for pkg in install:
            for upg in pkg.upgrades:
                for prv in upg.providedby:
                    for prvpkg in prv.packages:
                        if prvpkg.installed:
                            if prvpkg in remove:
                                del remove[prvpkg]
                            if pkg in install:
                                del install[pkg]
                            upgrade[pkg] = True

        total = len(install)+len(upgrade)+len(remove)
        prog.set(0, total)

        for pkg in install:
            prog.setSubTopic(pkg, "Installing %s" % pkg.name)
            prog.setSub(pkg, 0, 1, 1)
            prog.show()
            status, output = commands.getstatusoutput("installpkg %s" %
                                                      pkgpaths[pkg][0])
            prog.setSubDone(pkg)
            prog.show()
            if status != 0:
                iface.warning("Got status %d installing %s:" % (status, pkg))
                iface.warning(output)
            else:
                iface.debug("Installing %s:" % pkg)
                iface.debug(output)
        for pkg in upgrade:
            prog.setSubTopic(pkg, "Upgrading %s" % pkg.name)
            prog.setSub(pkg, 0, 1, 1)
            prog.show()
            status, output = commands.getstatusoutput("upgradepkg %s" %
                                                      pkgpaths[pkg][0])
            prog.setSubDone(pkg)
            prog.show()
            if status != 0:
                iface.warning("Got status %d upgrading %s:" % (status, pkg))
                iface.warning(output)
            else:
                iface.debug("Upgrading %s:" % pkg)
                iface.debug(output)
        for pkg in remove:
            prog.setSubTopic(pkg, "Removing %s" % pkg.name)
            prog.setSub(pkg, 0, 1, 1)
            prog.show()
            status, output = commands.getstatusoutput("removepkg %s" %
                                                      pkg.name)
            prog.setSubDone(pkg)
            prog.show()
            if status != 0:
                iface.warning("Got status %d removing %s:" % (status, pkg))
                iface.warning(output)
            else:
                iface.debug("Removing %s:" % pkg)
                iface.debug(output)

        prog.setDone()
        prog.stop()

# vim:ts=4:sw=4:et
