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

import contextlib
import fcntl
import os
import json
import base64

from boltlinux.error import BoltError
from boltlinux.miscellaneous.userinfo import UserInfo

class AppConfig:

    DEFAULT_CONFIG = """\
{
    "apps": {
        "packagedb": {
            "appconfig": {
                "APPLICATION_ROOT": null,
                "DEBUG": false,
                "JSON_AS_ASCII": false
            }
        }
    }
}"""  # noqa

    def __init__(self):
        self.config = self.load_user_config()

    def __getitem__(self, key):
        return self.config[key]

    @contextlib.contextmanager
    def _lock_file(self, file_):
        try:
            fcntl.flock(file_.fileno(), fcntl.LOCK_EX)
            yield file_
        finally:
            try:
                fcntl.flock(file_.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
    #end function

    def get(self, key, default=None):
        return self.config.get(key, default)

    def load_user_config(self):
        config = None

        user_config_file = os.path.join(
            UserInfo.config_folder(), "config.json"
        )

        if os.path.exists(user_config_file):
            with open(user_config_file, "r", encoding="utf-8") as f, \
                    self._lock_file(f) as f:
                config = json.load(f)
        else:
            config = self.create_default_user_config()

        return config
    #end function

    def create_default_user_config(self):
        user_config_dir  = UserInfo.config_folder()
        user_config_file = os.path.join(user_config_dir, "config.json")

        default_config = json.loads(AppConfig.DEFAULT_CONFIG)
        default_config["maintainer-info"] = UserInfo.maintainer_info()

        for app in default_config.get("apps", {}).values():
            secret_key = base64.encodebytes(os.urandom(32)).decode("utf-8")
            app\
                .setdefault("appconfig", {})\
                .setdefault("SECRET_KEY", secret_key)
        #end for

        try:
            os.makedirs(user_config_dir, exist_ok=True)
            with open(user_config_file, "w", encoding="utf-8") as f, \
                    self._lock_file(f) as f:
                os.fchmod(f.fileno(), 0o0600)
                json.dump(default_config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            raise BoltError(
                "failed to store '{}': {}".format(user_config_file, str(e))
            )

        return default_config
    #end function

#end class
