# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2016-2018 Tobias Koch <tobias.koch@gmail.com>
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

import magic
import os
import re
import stat
import time

try:
    from magic import FileMagic
except ImportError:
    from magic.compat import FileMagic

from collections import namedtuple

class FileStats:

    @staticmethod
    def default_dir_stats():
        magic_obj = {
            "name":      "directory",
            "mime_type": "inode/directory",
            "encoding":  "binary"
        }

        timestamp = int(time.time())

        stats_obj = {
            "st_mode":  stat.S_IFDIR | 0o0755,
            "st_ino":   0,
            "st_dev":   0,
            "st_nlink": 3,
            "st_uid":   0,
            "st_gid":   0,
            "st_size":  0,
            "st_atime": timestamp,
            "st_mtime": timestamp,
            "st_ctime": timestamp
        }

        return FileStats(
            namedtuple("Magic", magic_obj.keys())(**magic_obj),
            namedtuple("Stats", stats_obj.keys())(**stats_obj)
        )
    #end function

    @staticmethod
    def default_file_stats():
        magic_obj = {
            "name":      "data",
            "mime_type": "application/octet-stream",
            "encoding":  "binary"
        }

        timestamp = int(time.time())

        stats_obj = {
            "st_mode":  stat.S_IFREG | 0o0644,
            "st_ino":   0,
            "st_dev":   0,
            "st_nlink": 1,
            "st_uid":   0,
            "st_gid":   0,
            "st_size":  0,
            "st_atime": timestamp,
            "st_mtime": timestamp,
            "st_ctime": timestamp
        }

        return FileStats(
            namedtuple("Magic", magic_obj.keys())(**magic_obj),
            namedtuple("Stats", stats_obj.keys())(**stats_obj)
        )
    #end function

    @staticmethod
    def detect_from_filename(filename):
        if os.path.islink(filename):
            link_target = os.readlink(filename)
            magic_obj = FileMagic(
                    mime_type='inode/symlink', encoding='binary',
                    name='symbolic link to ' + link_target)
        else:
            if not os.path.exists(filename):
                raise ValueError("no such file '%s'" % filename)
            magic_obj = magic.detect_from_filename(filename)
        #end if

        stats_obj = os.lstat(filename)
        filestats = FileStats(magic_obj, stats_obj)

        if filestats.is_symbolic_link:
            filestats.link_target = link_target

        return filestats
    #end function

    def __init__(self, magic_obj, stats_obj):
        self._magic_obj = magic_obj
        self._stats_obj = stats_obj
        self.link_target = ""
    #end function

    def restat(self, filename):
        self._stats_obj = os.lstat(filename)
    #end function

    @property
    def mode(self):
        return stat.S_IMODE(self._stats_obj.st_mode)
    #end function

    @property
    def device(self):
        return self._stats_obj.st_dev
    #end function

    @property
    def inode(self):
        return self._stats_obj.st_ino
    #end function

    @property
    def num_links(self):
        return self._stats_obj.st_nlink
    #end function

    @property
    def build_id(self):
        regexp_build_id = \
            r"ELF \d+-bit .SB .*, BuildID\[sha1\]=([0-9a-fA-F]+).*"
        m = re.match(regexp_build_id, self._magic_obj.name)
        if m:
            return m.group(1)
        return None
    #end function

    @property
    def is_elf_binary(self):
        regexp = r"ELF \d+-bit .SB .*"
        if re.match(regexp, self._magic_obj.name):
            return True
        return False
    #end function

    @property
    def is_stripped(self):
        regexp = r"ELF \d+-bit .SB .*, .* linked.*, .*not stripped"
        if re.match(regexp, self._magic_obj.name):
            return False
        return True
    #end function

    @property
    def is_dynamically_linked(self):
        regexp_bin = \
            r"ELF \d+-bit .SB .*?executable.*, dynamically linked.*"
        regexp_lib = \
            r"ELF \d+-bit .SB .*?shared object.*, dynamically linked.*"

        magic = self._magic_obj.name
        if re.match(regexp_bin, magic) or re.match(regexp_lib, magic):
            return True

        return False
    #end function

    @property
    def machine(self):
        regexp_machine = r"ELF \d+-bit .SB .*?, ([^,]+), .*"
        m = re.match(regexp_machine, self._magic_obj.name)
        if m:
            return m.group(1)
        return None
    #end function

    @property
    def arch_word_size(self):
        regexp_elf = r"ELF (\d+)-bit .SB.*"
        m = re.match(regexp_elf, self._magic_obj.name)
        if m:
            return m.group(1)
        return None
    #end function

    @property
    def is_file(self):
        return stat.S_ISREG(self._stats_obj.st_mode) != 0
    #end function

    @property
    def is_directory(self):
        return stat.S_ISDIR(self._stats_obj.st_mode) != 0
    #end function

    @property
    def is_symbolic_link(self):
        return stat.S_ISLNK(self._stats_obj.st_mode) != 0
    #end function

    @property
    def is_block_device(self):
        return stat.S_ISBLK(self._stats_obj.st_mode) != 0
    #end function

    @property
    def is_char_device(self):
        return stat.S_ISCHR(self._stats_obj.st_mode) != 0
    #end function

    @property
    def is_fifo(self):
        return stat.S_ISFIFO(self._stats_obj.st_mode) != 0
    #end function

    @property
    def is_socket(self):
        return stat.S_ISSOCK(self._stats_obj.st_mode) != 0
    #end function

    def __getattr__(self, name):
        stat_attributes = [
            "st_mode",
            "st_ino",
            "st_dev",
            "st_nlink",
            "st_uid",
            "st_gid",
            "st_size",
            "st_atime",
            "st_mtime",
            "st_ctime"
        ]

        if name in stat_attributes:
            return self._stats_obj.__getattribute__(name)
        else:
            return self._magic_obj.__getattribute__(name)
    #end function

#end class
