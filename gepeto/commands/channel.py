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
from gepeto.option import OptionParser, append_all
from gepeto.channel import *
from gepeto import *
import os

USAGE="gpt channel [options]"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    parser.defaults["add"] = []
    parser.defaults["set"] = []
    parser.defaults["remove"] = []
    parser.defaults["enable"] = []
    parser.defaults["disable"] = []
    parser.defaults["show"] = None
    parser.add_option("--add", action="callback", callback=append_all,
                      help="arguments are key=value pairs defining a "
                           "channel, or a filename/url pointing to "
                           "a channel description")
    parser.add_option("--set", action="callback", callback=append_all,
                      help="argument is an alias, and one or more key=value "
                           "pair modifying a channel")
    parser.add_option("--remove", action="callback", callback=append_all,
                      help="arguments are channel aliases to be removed")
    parser.add_option("--show", action="callback", callback=append_all,
                      help="show channels with aliases given as arguments "
                           "or all channels, if no argument was given")
    parser.add_option("--enable", action="callback", callback=append_all,
                      help="arguments are channel aliases to be enabled")
    parser.add_option("--disable", action="callback", callback=append_all,
                      help="arguments are channel aliases to be disabled")
    parser.add_option("--force", action="store_true",
                      help="execute without asking")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts, ctrl):

    channels = sysconf.get("channels", setdefault={})
    
    if opts.add:

        if len(opts.add) == 1:
            arg = opts.add[0]
            if os.path.isfile(arg):
                data = open(arg).read()
                newchannels = parseChannelDescription(data)
            elif ":/" in arg:
                succ, fail = ctrl.fetchFiles([arg], "channel description")
                if fail:
                    raise Error, "Unable to fetch channel description: %s" \
                                 % fail[arg]
                data = open(succ[arg]).read()
                newchannels = parseChannelDescription(data)
                os.unlink(succ[arg])
            else:
                raise Error, "Don't know what to do with: %s" % arg
        else:
            newchannels = {}
            channel = {}
            alias = None
            for arg in opts.add:
                if "=" not in arg:
                    raise Error, "Argument '%s' has no '='" % arg
                key, value = arg.split("=")
                key = key.strip()
                value = value.strip()
                if key == "alias":
                    alias = value
                else:
                    channel[key] = value
            if not alias:
                raise Error, "Channel has no alias"
            if "type" not in channel:
                raise Error, "Channel has no type"

            newchannels[alias] = channel

        for alias in newchannels:
            channel = newchannels[alias]
            type = channel.get("type")
            desc = createChannelDescription(type, alias, channel)
            if not desc:
                continue
            if not opts.force:
                print
                print desc
                print
                res = raw_input("Include this channel (y/N)? ").strip()
            if opts.force or res and res[0].lower() == "y":
                try:
                    createChannel(type, alias, channel)
                except Error, e:
                    iface.error("Invalid channel: %s" % e)
                else:
                    while alias in channels:
                        iface.info("Channel alias '%s' is already in use."
                                   % alias)
                        res = raw_input("Choose another one: ").strip()
                        if res:
                            alias = res
                    channels[alias] = channel

    if opts.set:

        if not opts.set:
            raise Error, "Invalid arguments"

        alias = opts.set.pop(0)
        if "=" in alias:
            raise Error, "First argument must be the channel alias"
        if alias not in channels:
            raise Error, "Channel with alias '%s' not found" % alias
        oldchannel = channels[alias]

        channel = {}
        for arg in opts.set:
            if "=" not in arg:
                raise Error, "Argument '%s' has no '='" % arg
            key, value = arg.split("=")
            key = key.strip()
            if key == "type":
                raise Error, "Can't change the channel type"
            if key == "alias":
                raise Error, "Can't change the channel alias"
            channel[key] = value.strip()

        newchannel = oldchannel.copy()
        newchannel.update(channel)
        for key in newchannel.keys():
            if not newchannel[key]:
                del newchannel[key]
        try:
            createChannel(newchannel.get("type"), alias, newchannel)
        except Error, e:
            raise Error, "Invalid channel: %s" % e

        oldchannel.update(channel)
        for key in oldchannel.keys():
            if not oldchannel[key]:
                del oldchannel[key]

    if opts.remove:

        for alias in opts.remove:
            if alias not in channels:
                continue
            if opts.force or iface.askYesNo("Remove channel '%s'" % alias):
                del channels[alias]

    if opts.enable:

        for alias in opts.enable:
            if alias not in channels:
                continue
            channel = channels[alias]
            if "disabled" in channel:
                del channel["disabled"]

    if opts.disable:

        for alias in opts.disable:
            if alias not in channels:
                continue
            channels[alias]["disabled"] = "yes"

    if opts.show is not None:

        for alias in opts.show or channels:
            if alias not in channels:
                continue
            channel = channels[alias]
            desc = createChannelDescription(channel.get("type"),
                                            alias, channel)
            if desc:
                print desc
                print

# vim:ts=4:sw=4:et