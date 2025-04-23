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

import textwrap

from copy import deepcopy
from html2text import HTML2Text
from lxml import etree

class SpecfileSerializer:

    BOOLS = {
        "architecture-independent": 1,
    }

    def serialize(self, specfile):
        root_node = specfile.xml_doc.getroot()

        element = {}
        element["source"] = self.apply_templates(root_node.xpath("source")[0])

        element["source"].update({
            "name":
                specfile.source_name,
            "version":
                specfile.latest_version,
            "source_version":
                specfile.source_version,
            "maintainer":
                specfile.maintainer,
            "date":
                specfile.date
        })

        if specfile.upstream_version:
            element["source"]["upstream_version"] = specfile.upstream_version

        packages = []
        for item in root_node.xpath("package"):
            pkg  = self.apply_templates(item)
            desc = item.xpath("description/summary")[0]

            pkg.update(self.fetch_attributes(item))
            pkg["summary"] = desc.text

            packages.append(pkg)
        #end for

        element["packages"] = packages
        return element
    #end function

    def fetch_attributes(self, node):
        attributes = {}

        for name, value in node.items():
            if name in self.BOOLS:
                attributes[name] = True if value == "true" else False
            else:
                attributes[name] = value
        #end for

        return attributes
    #end function

    def apply_templates(self, node):
        element = {}

        for child in node:
            if not isinstance(child.tag, str):
                continue

            try:
                method = getattr(self, "_" + child.tag)
                result = method(child)

                element[child.tag] = result
            except AttributeError:
                pass
        #end for

        return element
    #end function

    # TEMPLATES

    def _description(self, node):
        desc = deepcopy(node)

        desc.tag = "div"
        desc.xpath("summary")[0].tag = "h1"

        html_to_text = HTML2Text()
        html_to_text.escape_snob = True
        html_to_text.body_width = 0

        html = etree.tostring(desc, encoding="unicode")
        md   = html_to_text.handle(html).strip()

        return md
    #end function

    def _sources(self, node):
        elements = []

        for item in node.xpath("file"):
            elements.append(self.fetch_attributes(item))

        return elements
    #end function

    def _requires(self, node):
        elements = []

        for item in node.xpath("package|choice"):
            if item.tag == "package":
                elements.append(self.fetch_attributes(item))
            elif item.tag == "choice":
                choices = []

                for sub_item in item.xpath("package"):
                    choices.append(self.fetch_attributes(sub_item))

                elements.append(choices)
            #end if
        #end for

        return elements
    #end function

    def _rules(self, node):
        element = {}

        for item in node.xpath("prepare|build|install"):
            element[item.tag] = textwrap.dedent(item.text).strip()

        return element
    #end function

#end class
