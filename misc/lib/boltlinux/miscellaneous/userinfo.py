# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2021 Tobias Koch <tobias.koch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import os
import pwd
import socket

class UserInfo:

    @staticmethod
    def homedir():
        home = None

        pw = pwd.getpwuid(os.getuid())
        if pw:
            home = pw.pw_dir
        if not home:
            return None

        return os.path.normpath(os.path.realpath(home))
    #end function

    @staticmethod
    def config_folder():
        home = UserInfo.homedir()
        if not home:
            return None
        return os.path.join(home, ".bolt")
    #end function

    @staticmethod
    def cache_dir():
        home = UserInfo.homedir()
        if not home:
            return None
        return os.path.join(home, ".bolt", "cache")
    #end function

    @staticmethod
    def maintainer_info():
        hostname = socket.gethostname()
        useruid  = os.getuid()
        username = pwd.getpwuid(useruid).pw_name
        realname = pwd.getpwuid(useruid).pw_gecos.split(',')[0]
        usermail = username + "@" + hostname

        return {
            "name":  realname,
            "email": usermail
        }
    #end function

#end class
