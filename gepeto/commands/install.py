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
from gepeto.transaction import Transaction, PolicyInstall, sortUpgrades
from gepeto.transaction import INSTALL, REINSTALL
from gepeto.matcher import MasterMatcher
from gepeto.option import OptionParser
from gepeto.channel import FileChannel
from gepeto import *
import string
import re
import os

USAGE="gpt install [options] package ..."

DESCRIPTION="""
This command will install one or more packages in the
system. If a new version of an already installed package
is available, it will be selected for installation.
"""

EXAMPLES="""
gpt install pkgname
gpt install '*kgna*'
gpt install pkgname-1.0
gpt install pkgname-1.0-1
gpt install pkgname1 pkgname2
gpt install ./somepackage.file
gpt install http://some.url/some/path/somepackage.file
"""

def parse_options(argv):
    parser = OptionParser(usage=USAGE,
                          description=DESCRIPTION,
                          examples=EXAMPLES)
    parser.add_option("--stepped", action="store_true",
                      help="split operation in steps")
    parser.add_option("--urls", action="store_true",
                      help="dump needed urls and don't commit operation")
    parser.add_option("--download", action="store_true",
                      help="download packages and don't commit operation")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts, ctrl):
    urls = []
    for arg in opts.args[:]:
        if '/' in arg:
            if os.path.isfile(arg):
                ctrl.addFileChannel(arg)
                opts.args.remove(arg)
            elif ":/" in arg:
                urls.append(arg)
    if urls:
        succ, fail = ctrl.downloadURLs(urls, "packages", targetdir=os.getcwd())
        if fail:
            raise Error, "Failed to download packages:\n" + \
                         "\n".join(["    %s: %s" % (url, fail[url])
                                    for url in fail])
        for url, file in succ.items():
            ctrl.addFileChannel(file)
            opts.args.remove(url)
    ctrl.updateCache()
    cache = ctrl.getCache()
    trans = Transaction(cache, PolicyInstall)
    for channel in ctrl.getFileChannels():
        for pkg in channel.getLoader().getPackages():
            if pkg.installed:
                raise Error, "%s is already installed" % pkg
            trans.enqueue(pkg, INSTALL)
    for arg in opts.args:
        matcher = MasterMatcher(arg)
        pkgs = matcher.filter(cache.getPackages())
        if not pkgs:
            raise Error, "'%s' matches no packages" % arg
        if len(pkgs) > 1:
            sortUpgrades(pkgs)
        if pkgs[0].installed:
            raise Error, "%s matches '%s' and is already installed" % \
                         (pkgs[0], arg)
        pkgs = [x for x in pkgs if not x.installed]
        if len(pkgs) > 1:
            iface.warning("'%s' matches multiple packages, selecting: %s" % \
                          (arg, pkgs[0]))
        trans.enqueue(pkgs[0], INSTALL)
    iface.showStatus("Computing transaction...")
    trans.run()
    iface.hideStatus()
    if trans:
        if opts.urls:
            ctrl.dumpTransactionURLs(trans)
        elif opts.download:
            ctrl.downloadTransaction(trans)
        elif opts.stepped:
            ctrl.commitTransactionStepped(trans)
        else:
            ctrl.commitTransaction(trans)

# vim:ts=4:sw=4:et
