if [ ! -f environment.sh ] || [ ! -d distro-info  ]; then
    echo "The environment.sh file must be sourced locally as '. environment.sh'."
else
    mkdir -p .pythonpath/boltlinux

    ln -sf ../../ffi-libarchive/lib/boltlinux/ffi    .pythonpath/boltlinux/
    ln -sf ../../distro-info/lib/boltlinux/distro    .pythonpath/boltlinux/
    ln -sf ../../misc/lib/boltlinux/error.py         .pythonpath/boltlinux/
    ln -sf ../../misc/lib/boltlinux/miscellaneous    .pythonpath/boltlinux/
    ln -sf ../../package/lib/boltlinux/package       .pythonpath/boltlinux/
    ln -sf ../../repository/lib/boltlinux/repository .pythonpath/boltlinux/
    ln -sf ../../image-gen/lib/boltlinux/osimage     .pythonpath/boltlinux/

    if [ -d ../build-box-utils/lib/boltlinux/buildbox ]; then
        ln -sf ../../../build-box-utils/lib/boltlinux/buildbox .pythonpath/boltlinux/
    fi

    if [ -d ../build-system/lib/boltlinux ]; then
        ln -sf ../../../build-system/lib/boltlinux/packagedb .pythonpath/boltlinux/
        ln -sf ../../../build-system/lib/boltlinux/builder   .pythonpath/boltlinux/
        ln -sf ../../../build-system/lib/boltlinux/archive   .pythonpath/boltlinux/
    fi

    touch .pythonpath/boltlinux/__init__.py

    if [ "x$BOLT_DISTRO_TOOLS_SOURCED" = "x" ]; then
        export PYTHONPATH="$(pwd)/.pythonpath:$PYTHONPATH"

        PATH="$(pwd)/image-gen/bin:$PATH"
        PATH="$(pwd)/distro-info/bin:$PATH"
        PATH="$(pwd)/package/bin:$PATH"
        PATH="$(pwd)/repository/bin:$PATH"

        PATH="$(pwd)/../build-system/bin:$PATH"
        PATH="$(pwd)/../build-box-utils:$PATH"

        export PATH
        export PS1="(distro-tools)$PS1"
        export BOLT_DISTRO_TOOLS_SOURCED="yes"
    fi
fi
