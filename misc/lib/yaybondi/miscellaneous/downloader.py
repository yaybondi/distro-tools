# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2019 Tobias Koch <tobias.koch@gmail.com>
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

import hashlib
import os
import random
import string
import tempfile
import urllib.request

from yaybondi.error import BondiError

class DownloadError(BondiError):
    pass

class Downloader:

    def __init__(self, progress_bar_class=None):
        self._progress_bar_class = progress_bar_class

    def get(self, url, digest=None, connection_timeout=30):
        progress_bar = None
        bytes_read   = 0

        try:
            with urllib.request.urlopen(url, timeout=connection_timeout)\
                    as response:
                if self._progress_bar_class and response.length:
                    progress_bar = self._progress_bar_class(response.length)
                    progress_bar(0)
                #end if

                for chunk in iter(lambda: response.read(8192), b""):
                    bytes_read += len(chunk)

                    if digest is not None:
                        digest.update(chunk)
                    yield chunk

                    if progress_bar:
                        progress_bar(bytes_read)
                #end for
            #end with
        except Exception as e:
            raise DownloadError(
                'error retrieving "{}": {}'.format(url, str(e))
            )
    #end function

    def source_changed(self, url, old_tag, connection_timeout=30):
        new_tag = self.tag(
            url, connection_timeout=connection_timeout
        )
        return old_tag != new_tag
    #end function

    def download_tagged_file(self, url, filename, connection_timeout=30,
            permissions=None):
        old_blob = ""
        old_tag  = ""

        if os.path.islink(filename):
            old_blob = os.path.realpath(filename)
            old_tag  = os.path.basename(old_blob)

        new_tag = self.tag(url)

        if old_tag != new_tag:
            self.download_named_tag(
                url,
                filename,
                new_tag,
                connection_timeout=connection_timeout,
                permissions=permissions
            )

            if old_blob:
                try:
                    os.unlink(old_blob)
                except OSError:
                    pass
            #end if
        #end if
    #end function

    def download_named_tag(self, url, symlink, tag, digest=None,
            connection_timeout=30, permissions=None):
        directory = os.path.dirname(os.path.realpath(symlink))
        blob_file = os.path.join(directory, tag)

        with tempfile.NamedTemporaryFile(prefix=".download-", dir=directory,
                delete=False) as f:
            try:
                it = self.get(
                    url,
                    digest=digest,
                    connection_timeout=connection_timeout
                )

                for chunk in it:
                    f.write(chunk)

                # Fix permissions
                if permissions is not None:
                    os.fchmod(f.fileno(), permissions)
                # Atomically rename blob.
                os.rename(f.name, blob_file)
                # Create temporary symlink to new blob reusing tempfile name.
                os.symlink(os.path.basename(blob_file), f.name)
                # Atomically rename symlink (hopefully).
                os.rename(f.name, symlink)
            except Exception as e:
                if os.path.exists(f.name) or os.path.islink(f.name):
                    os.unlink(f.name)
                if os.path.exists(blob_file):
                    if os.path.islink(symlink) and \
                            os.path.basename(os.readlink(symlink)) != tag:
                        os.unlink(blob_file)
                raise DownloadError(
                    'error retrieving "{}": {}'.format(url, str(e))
                )
            #end try
        #end with
    #end function

    def tag(self, url, connection_timeout=30):
        alphabet = \
            string.ascii_uppercase + \
            string.ascii_lowercase + \
            string.digits

        try:
            request = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(request, timeout=connection_timeout)\
                    as response:
                identifier1 = response.getheader("ETag", "")
                identifier2 = response.getheader(
                    "Last-Modified",
                    "".join([random.choice(alphabet) for i in range(16)])
                )
        except Exception as e:
            raise DownloadError(
                "error generating etag for '{}': {}".format(url, str(e))
            )

        sha256 = hashlib.sha256()
        sha256.update(identifier1.encode("utf-8"))
        sha256.update(identifier2.encode("utf-8"))

        return sha256.hexdigest()[:16]
    #end function

#end class
