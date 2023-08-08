BOLT_ENVIRONMENT_SH_PRE_FLIGHT_CHECKS_OK=true

if [ ! -f "environment.sh" ]; then
    echo "The environment.sh file must be sourced locally as '. ./environment.sh'."
    BOLT_ENVIRONMENT_SH_PRE_FLIGHT_CHECKS_OK=false
fi

if [ "$BOLT_ENVIRONMENT_SH_PRE_FLIGHT_CHECKS_OK" = true ]; then
    mkdir -p .pythonpath/boltlinux

    ln -sf ../../ffi-libarchive/lib/boltlinux/ffi    .pythonpath/boltlinux/
    ln -sf ../../distro-info/lib/boltlinux/distro    .pythonpath/boltlinux/
    ln -sf ../../misc/lib/boltlinux/error.py         .pythonpath/boltlinux/
    ln -sf ../../misc/lib/boltlinux/miscellaneous    .pythonpath/boltlinux/
    ln -sf ../../package/lib/boltlinux/package       .pythonpath/boltlinux/
    ln -sf ../../repository/lib/boltlinux/repository .pythonpath/boltlinux/
    ln -sf ../../image-gen/lib/boltlinux/osimage     .pythonpath/boltlinux/

    touch .pythonpath/boltlinux/__init__.py

    if [ "x$BOLT_LOCAL_PROJECT_SOURCED" = "x" ]; then
        export PYTHONPATH="$(pwd)/.pythonpath:$PYTHONPATH"

        PATH="$(pwd)/image-gen/bin:$PATH"
        PATH="$(pwd)/distro-info/bin:$PATH"
        PATH="$(pwd)/package/bin:$PATH"
        PATH="$(pwd)/repository/bin:$PATH"

        export PATH
        export PS1="(distro-tools)$PS1"
        export BOLT_LOCAL_PROJECT_SOURCED="yes"
    fi
fi

unset BOLT_ENVIRONMENT_SH_PRE_FLIGHT_CHECKS_OK
