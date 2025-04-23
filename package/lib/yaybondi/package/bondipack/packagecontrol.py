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

import copy
import logging
import os
import shutil

from yaybondi.error import UnmetDependency, InvocationError, SkipBuild

from yaybondi.miscellaneous.platform import Platform
from yaybondi.miscellaneous.userinfo import UserInfo

from yaybondi.package.bondipack.basepackage import BasePackage
from yaybondi.package.bondipack.changelog import Changelog
from yaybondi.package.bondipack.debianpackage import DebianPackage
from yaybondi.package.bondipack.packagedesc import PackageDescription
from yaybondi.package.bondipack.shlibcache import ShlibCache
from yaybondi.package.bondipack.sourcecache import SourceCache
from yaybondi.package.bondipack.sourcepackage import SourcePackage
from yaybondi.package.bondipack.specfile import Specfile

LOGGER = logging.getLogger(__name__)

class PackageControl:

    def __init__(self, filename, cache_dir=None, **kwargs):
        self.parms = {
            "arch":
                Platform.target_machine(),
            "build_for":
                "target",
            "copy_archives":
                True,
            "debug_pkgs":
                True,
            "disable_packages":
                [],
            "enable_packages":
                [],
            "force_local":
                False,
            "ignore_deps":
                False,
            "libc_name":
                Platform.libc_name(),
            "outdir":
                None,
            "tools_arch":
                Platform.tools_machine()
        }
        self.parms.update(kwargs)

        build_for = self.parms["build_for"]
        pkg_arch  = self.parms["arch"] if build_for == "target" \
                        else self.parms["tools_arch"]

        specfile = Specfile(filename)
        specfile.validate()

        xml_doc = specfile.xml_doc

        if self.parms["enable_packages"]:
            for p in self.parms["enable_packages"]:
                if not xml_doc.xpath("/control/package[@name='%s']" % p):
                    raise InvocationError("unknown binary package '%s'." % p)
            #end for
        #end if

        if self.parms["disable_packages"]:
            for p in self.parms["disable_packages"]:
                if not xml_doc.xpath("/control/package[@name='%s']" % p):
                    raise InvocationError("unknown binary package '%s'." % p)
            #end for
        #end if

        specfile.preprocess(
            true_terms=[
                # Example: "target-build", "tools-x86_64", "riscv64", "glibc"
                "{}-build".format(build_for),
                "tools-{}".format(self.parms["tools_arch"]),
                self.parms["arch"],
                self.parms["libc_name"]
            ]
        )

        if not cache_dir:
            cache_dir = UserInfo.cache_dir()

        self._cache_dir = cache_dir

        # copy maintainer, email, version, revision to package sections
        for attr_name in ["maintainer", "email", "epoch",
                "version", "revision"]:
            xpath = "/control/changelog/release[1]/@%s" % attr_name
            try:
                attr_val = xml_doc.xpath(xpath)[0]
            except IndexError:
                continue
            xpath = "/control/*[name() = 'source' or name() = 'package']"
            for pkg_node in xml_doc.xpath(xpath):
                pkg_node.attrib[attr_name] = attr_val
        #end for

        xpath = "/control/source/@name"
        source_name = xml_doc.xpath(xpath)[0]

        xpath = "/control/source/@repo"
        repo_name = xml_doc.xpath(xpath)[0]

        xpath = "/control/source/@architecture-independent"
        try:
            is_arch_indep = xml_doc.xpath(xpath)[0].lower()
        except IndexError:
            is_arch_indep = "false"
        #end try

        if build_for in ["tools", "cross-tools"]:
            architecture = "tools"
        elif is_arch_indep.lower() == "true":
            architecture = "all"
        else:
            architecture = pkg_arch

        for pkg_node in xml_doc.xpath(
                "/control/*[name() = 'source' or name() = 'package']"):
            pkg_node.attrib["source"] = source_name

            if pkg_node.tag != "source":
                pkg_node.attrib["repo"] = repo_name

            pkg_node.attrib["architecture"] = architecture
        #end for

        xml_doc.xpath("/control/changelog")[0].attrib["source"] = source_name

        self.defines = {
            "BONDI_SOURCE_DIR": "sources",
            "BONDI_BUILD_DIR": "sources",
            "BONDI_INSTALL_DIR": "install",
            "BONDI_WORK_DIR": os.getcwd(),
            "BONDI_BUILD_TYPE": Platform.target_type(),
            "BONDI_TOOLS_TYPE": Platform.tools_type(),
            "BONDI_BUILD_FOR": build_for,
            "BONDI_LIBC_NAME": self.parms["libc_name"]
        }

        if build_for == "tools":
            self.defines["BONDI_HOST_TYPE"] = Platform.tools_type()
            self.defines["BONDI_TARGET_TYPE"] = Platform.tools_type()
            self.defines["BONDI_INSTALL_PREFIX"] = "/tools"
        elif build_for == "cross-tools":
            self.defines["BONDI_HOST_TYPE"] = Platform.tools_type()
            self.defines["BONDI_TARGET_TYPE"] = Platform.target_type()
            self.defines["BONDI_INSTALL_PREFIX"] = "/tools"
        else:
            self.defines["BONDI_HOST_TYPE"] = Platform.target_type()
            self.defines["BONDI_TARGET_TYPE"] = Platform.target_type()
            self.defines["BONDI_INSTALL_PREFIX"] = "/usr"
        #end if

        for node in xml_doc.xpath("/control/defines/def"):
            self.defines[node.get("name")] = node.get("value", "")

        # these *must* be absolute paths
        for s in ["SOURCE", "BUILD", "INSTALL"]:
            if os.path.isabs(self.defines["BONDI_%s_DIR" % s]):
                self.defines["BONDI_%s_DIR" % s] = os.path.realpath(
                        self.defines["BONDI_%s_DIR" % s])
            else:
                self.defines["BONDI_%s_DIR" % s] = os.path.realpath(
                    os.sep.join([self.defines["BONDI_WORK_DIR"],
                        self.defines["BONDI_%s_DIR" % s]])
                )
            #end if
        #end for

        source_pkg_node = xml_doc.xpath("/control/source")[0]

        self.src_pkg = SourcePackage(
            copy.deepcopy(source_pkg_node),
            copy_archives=self.parms["copy_archives"],
            build_for=build_for
        )
        self.src_pkg.basedir = os.path.realpath(os.path.dirname(filename))

        self.bin_pkgs = []

        if self.parms.get("action") == "would_build":
            pass
        elif self.parms.get("action") == "mk_build_deps":
            pkg = DebianPackage(
                copy.deepcopy(source_pkg_node),
                debug_pkgs=False,
                install_prefix=self.defines["BONDI_INSTALL_PREFIX"],
                host_type=self.defines["BONDI_HOST_TYPE"],
                build_for=build_for
            )

            pkg.name        += "-build-deps"
            pkg.architecture = "all"
            pkg.maintainer   = "Package Control"
            pkg.source       = "no-source"
            pkg.section      = "devel"
            pkg.description  = PackageDescription(
                """
                <description>
                    <summary>Build dependencies for {name} {version}</summary>
                    <p>
                    Install this package to pull in all build dependencies
                    required to build "{name}" version "{version}" for "{arch}".
                    </p>
                </description>
                """  # noqa
                .format(
                    name=self.src_pkg.name,
                    version=pkg.version,
                    arch=architecture
                )
            )

            # The source package duplicates all dependencies, requiring them
            # once for tools and once for target.
            pkg.relations["requires"] = self.src_pkg.relations["requires"]

            self.bin_pkgs.append(pkg)
        else:
            for node in xml_doc.xpath("/control/package"):
                pkg = DebianPackage(
                    node,
                    debug_pkgs=self.parms["debug_pkgs"],
                    install_prefix=self.defines["BONDI_INSTALL_PREFIX"],
                    host_type=self.defines["BONDI_HOST_TYPE"],
                    build_for=build_for
                )

                if self.parms["enable_packages"]:
                    if pkg.name not in self.parms["enable_packages"]:
                        continue
                if self.parms["disable_packages"]:
                    if pkg.name in self.parms["disable_packages"]:
                        continue

                pkg.basedir = self.defines["BONDI_INSTALL_DIR"]

                if self.parms.get("outdir"):
                    pkg.output_dir = os.path.realpath(self.parms["outdir"])

                self.bin_pkgs.append(pkg)
            #end for
        #end if

        for pkg in self.bin_pkgs:
            if build_for == "tools":
                pkg.name = "tools-" + pkg.name
            elif build_for == "cross-tools":
                pkg.name = "tools-target-" + pkg.name
            #end if
        #end function

        self.changelog = Changelog(xml_doc.xpath('/control/changelog')[0])
    #end function

    def __call__(self, action):
        if action not in {"list_deps", "mk_build_deps", "unpack", "clean"}:
            if self.src_pkg.skip:
                raise SkipBuild(
                    'package is marked to be skipped unless "{}".'
                    .format(self.src_pkg.skip)
                )
            #end if

            # Nothing else to do, we return and the app exits with 0, now.
            if action == "would_build":
                return

            if not self.parms.get("ignore_deps"):
                missing_deps = self._missing_build_dependencies()
                if missing_deps.list:
                    msg = "missing dependencies: {}".format(missing_deps)
                    raise UnmetDependency(msg)
                #end if
            #end if
        #end if

        getattr(self, action)()
    #end function

    def mk_build_deps(self):
        pkg = self.bin_pkgs[0]
        pkg.do_pack()

        bondi_build_deps_symlink = "bondi-build-deps.bondi"

        if os.path.islink(bondi_build_deps_symlink):
            os.unlink(bondi_build_deps_symlink)
        if os.path.exists(bondi_build_deps_symlink):
            return

        try:
            os.symlink(pkg.pkg_filename(), bondi_build_deps_symlink)
        except OSError:
            pass
    #end function

    def list_deps(self):
        print(self.src_pkg.build_dependencies())

    def unpack(self):
        directory = self.defines["BONDI_WORK_DIR"]
        if not os.path.exists(directory):
            os.makedirs(directory)

        source_cache = SourceCache(self._cache_dir, self.parms["release"],
                force_local=self.parms["force_local"])

        self.src_pkg \
            .unpack(directory, source_cache=source_cache) \
            .patch(directory)
    #end function

    def prepare(self):
        directory = self.defines["BONDI_BUILD_DIR"]
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.src_pkg.run_action("prepare", self.defines)
    #end function

    def build(self):
        directory = self.defines["BONDI_BUILD_DIR"]
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.src_pkg.run_action("build", self.defines)
    #end function

    def install(self):
        install_dir = self.defines["BONDI_INSTALL_DIR"]

        if os.path.exists(install_dir):
            shutil.rmtree(install_dir)
        os.makedirs(install_dir)

        self.src_pkg.run_action("install", self.defines)
    #end function

    def package(self):
        shlib_cache = ShlibCache(prefix=self.defines["BONDI_INSTALL_PREFIX"])
        for pkg in self.bin_pkgs:
            pkg.prepare()
        for pkg in self.bin_pkgs:
            pkg.strip_debug_symbols_and_unarm_rpath()
        for pkg in self.bin_pkgs:
            shlib_cache.overlay_package(pkg)
        for pkg in self.bin_pkgs:
            pkg.pack(shlib_cache, self.bin_pkgs)
    #end function

    def repackage(self):
        self.install()
        self.package()
    #end function

    def clean(self):
        self.src_pkg.run_action("clean", self.defines)

    def default(self):
        self.unpack()
        self.prepare()
        self.build()
        self.install()
        self.package()
    #end function

    # PRIVATE

    def _missing_build_dependencies(self):
        unfulfilled_dependency_spec = BasePackage.DependencySpecification()

        for alternatives in self.src_pkg.relations["requires"].list:
            fulfilled = False

            for dep in alternatives:
                if dep.is_fulfilled:
                    fulfilled = True
                    break
            #end for

            if not fulfilled:
                for dep in alternatives:
                    unfulfilled_dependency_spec.index[dep.name] = dep
                unfulfilled_dependency_spec.list.append(alternatives)
            #end if
        #end for

        return unfulfilled_dependency_spec
    #end function

#end class
