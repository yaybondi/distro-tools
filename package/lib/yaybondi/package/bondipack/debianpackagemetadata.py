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

import re

from xml.sax.saxutils import escape as xml_escape

from yaybondi.error import BondiError
from yaybondi.miscellaneous.xpkg import BaseXpkg
from yaybondi.package.deb2bondi.packageutils import PackageUtilsMixin

class DebianPackageVersion:

    def __init__(self, version):
        self.full = version

        m = re.match(
            r"^(?:(\d+):)?([-+:~.a-zA-Z0-9]+?)(?:-([^-]+))?$",
            version
        )

        if not m:
            raise ValueError(
                "Failed to parse Debian package version '{}'"
                    .format(version)
            )
        #end if

        self.epoch, self.version, self.revision = \
            m.groups(default="")
    #end function

    def __str__(self):
        return self.full

    def __lt__(self, other):
        return BaseXpkg.compare_versions(self.full, other.full) == -1

#end class

class DebianPackageMetaData(PackageUtilsMixin):

    RELEVANT_KEYS = [
        "Package",
        "Source",
        "Version",
        "Installed-Size",
        "Maintainer",
        "Architecture",
        "Depends",
        "Build-Depends",
        "Build-Conflicts",
        "Pre-Depends",
        "Recommends",
        "Suggests",
        "Breaks",
        "Conflicts",
        "Provides",
        "Replaces",
        "Enhances",
        "Description",
        "Section",
        "Filename",
        "Size",
        "SHA256",
        "Checksums-Sha256",
    ]

    def __init__(self, string="", base_url=""):
        self._string = string
        self._fields = {}
        self._fully_parsed = False
        self._minimally_parsed = False
        self.base_url = base_url

        self._parse_meta_data_minimal()
    #end function

    def __getitem__(self, key):
        self._parse_meta_data_full()
        return self._fields[key]

    def __setitem__(self, key, value):
        self._parse_meta_data_full()
        self._fields[key] = value

    def __len__(self):
        self._parse_meta_data_full()
        return len(self._fields)

    def __bool__(self):
        self._parse_meta_data_full()
        return len(self._fields) != 0

    def __contains__(self, key):
        return key in self._fields

    def __str__(self):
        self._parse_meta_data_full()
        result = ""

        for k in DebianPackageMetaData.RELEVANT_KEYS:
            if k in self._fields:
                result += "{key}: {value}\n"\
                    .format(key=k, value=self._fields[k])
            #end if
        #end for

        return result
    #end function

    def keys(self):
        self._parse_meta_data_full()
        return self._fields.keys()

    def items(self):
        self._parse_meta_data_full()
        return self._fields.items()

    def values(self):
        self._parse_meta_data_full()
        return self._fields.values()

    @property
    def name(self):
        self._parse_meta_data_minimal()
        for field_name in ["Package", "Source"]:
            if field_name in self._fields:
                return self._fields[field_name]
        raise AttributeError("Package meta data missing naming information.")

    @property
    def url(self):
        self._parse_meta_data_full()
        return self.base_url + "/" + self._fields["Filename"]

    def get(self, key, default=None):
        self._parse_meta_data_full()
        return self._fields.get(key, default)

    def setdefault(self, key, default):
        return self._fields.setdefault(key, default)

    def to_bondi(self):
        self._parse_meta_data_full()
        fields = {}

        for k in DebianPackageMetaData.RELEVANT_KEYS:
            if k in self._fields:
                fields[k] = self._fields[k]

        # Lots of twisted transforms on dependency fields.

        dependency_types = [
            "Pre-Depends", "Depends",  "Build-Depends",
            "Suggests",    "Provides", "Breaks",
            "Conflicts",   "Replaces", "Build-Conflicts"
        ]

        for dep_type in dependency_types:
            val = fields.get(dep_type)

            if not val:
                fields[dep_type] = []
                continue

            # Remove all whitespace
            val = re.sub(r"\s+", "", val)
            # Remove everything in square brackets.
            val = re.sub(r"\[[^\]]+\]", "", val)
            # Insert a space after any number of <, > or = chars.
            val = re.sub(r"(\([<=>]+)", r"\1 ", val)
            # Replace binary:Version with Bondi == syntax.
            val = re.sub(r"= \$\{binary:Version\}", "==", val)
            # Replace source:Version with Bondi == syntax.
            val = re.sub(r"= \$\{source:Version\}", "==", val)
            # Split at comma separator.
            val = val.split(",")
            # Remove $variables.
            val = filter(lambda x: not x.startswith("$"), val)
            # Remove empty entries.
            val = filter(lambda x: x, val)

            # Split "name (> spec)" into (name, spec).
            val = map(
                lambda x: re.match(r"([^(]+)(?:\(([^)]+)\))?", x)
                    .groups(default=""), val
            )

            # If the name part lists alternatives, grep the first.
            val = map(
                lambda x: (
                    x[0].split("|")[0] if "|" in x[0] else x[0], x[1]
                ),
                val
            )

            # Remove Debian multi-stage build dep stuff.
            val = map(
                lambda x: (re.sub(r"<!?stage\d+>$", "", x[0]), x[1]), val
            )

            def _filter_irrelevant_pkgs(dep_name):
                if self.is_pkg_name_debian_specific(dep_name):
                    return False
                if self.is_pkg_name_implicit(dep_name):
                    return False
                return True
            #end inline function

            # Remove irrelevant entries.
            val = filter(lambda x: _filter_irrelevant_pkgs(x[0]), val)

            fields[dep_type] = list(val)
        #end for

        # Turn package description into crude XML.

        if "Description" in fields:
            if "\n" in fields["Description"]:
                summary, desc = re.split(r"\n", fields["Description"], 1)
            else:
                summary, desc = fields["Description"], ""

            summary, desc = summary.strip(), desc.strip()
            summary, desc = xml_escape(summary), xml_escape(desc)

            desc = re.sub(r"^\s*\.\s*$", r"</p>\n<p>", desc, flags=re.M)
            desc = re.sub(r" +", r" ", desc)
            desc = re.sub(r"^\s*", r" " * 8, desc, flags=re.M)

            fields["Summary"], fields["Description"] = summary, desc
        #end if

        return fields
    #end function

    # PRIVATE

    def _parse_meta_data_minimal(self):
        if self._minimally_parsed or self._fully_parsed:
            return

        for line in self._string.splitlines():
            try:
                key, val = line.split(":", 1)
            except ValueError:
                continue

            if key in ["Package", "Version", "Source"]:
                if key not in self._fields:
                    self._fields[key] = val.strip()
        #end for

        # The binary version may differ slightly from the source version, e.g.
        # the build system may have appended a build counter. For all practical
        # purposes, we always want to work with the source version.
        if "Source" in self._fields:
            m = re.match(
                r".*?\((?P<version>.*?)\)\s*$", self._fields.get("Source")
            )
            if m:
                self._fields["Version"] = m.group("version")
        #end if
    #end function

    def _parse_meta_data_full(self):
        if self._fully_parsed:
            return

        fields = {}

        key = None
        val = None

        for line in self._string.strip().splitlines():
            if line.startswith("#"):
                continue

            if re.match(r"^\s+.*?$", line):
                if key is None:
                    raise BondiError("invalid control file syntax.")
                fields.setdefault(key, []).append(line.strip())
            else:
                if ":" not in line:
                    raise BondiError("invalid control file syntax.")
                key, val = [item.strip() for item in line.split(":", 1)]
                val_list = fields.setdefault(key, [])
                if val:
                    val_list.append(val)
            #end if
        #end for

        for key in fields.keys():
            fields[key] = "\n    ".join(fields[key])

        # The binary version may differ slightly from the source version, e.g.
        # the build system may have appended a build counter. For all practical
        # purposes, we always want to work with the source version.
        if "Source" in fields:
            m = re.match(r".*?\((?P<version>.*?)\)\s*$", fields.get("Source"))
            if m:
                fields["Version"] = m.group("version")
        #end if

        self._fields.update(fields)
        self._fully_parsed = True
    #end function

#end class
