if [ "x$BOLT_DISTRO_TOOLS_SOURCED" = "x" ]; then
    mkdir -p .pythonpath/boltlinux

    ln -sf ../../ffi-libarchive/lib/boltlinux/ffi    .pythonpath/boltlinux/
    ln -sf ../../distro-info/lib/boltlinux/archive   .pythonpath/boltlinux/
    ln -sf ../../misc/lib/boltlinux/error.py         .pythonpath/boltlinux/
    ln -sf ../../misc/lib/boltlinux/miscellaneous    .pythonpath/boltlinux/
    ln -sf ../../package/lib/boltlinux/package       .pythonpath/boltlinux/
    ln -sf ../../repository/lib/boltlinux/repository .pythonpath/boltlinux/

    touch .pythonpath/boltlinux/__init__.py

    export PYTHONPATH="`pwd`/.pythonpath:$PYTHONPATH"
    export PATH="`pwd`/distro-info/bin:`pwd`/package/bin:`pwd`/repository/bin:$PATH"
    export PS1="(distro-tools)$PS1"
    export BOLT_DISTRO_TOOLS_SOURCED="yes"
fi
