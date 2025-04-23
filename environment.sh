BONDI_ENVIRONMENT_SH_PRE_FLIGHT_CHECKS_OK=true

if [ ! -f "environment.sh" ]; then
    echo "The environment.sh file must be sourced locally as '. ./environment.sh'."
    BONDI_ENVIRONMENT_SH_PRE_FLIGHT_CHECKS_OK=false
fi

if [ "$BONDI_ENVIRONMENT_SH_PRE_FLIGHT_CHECKS_OK" = true ]; then
    mkdir -p .pythonpath/yaybondi

    ln -sf ../../ffi-libarchive/lib/yaybondi/ffi    .pythonpath/yaybondi/
    ln -sf ../../distro-info/lib/yaybondi/distro    .pythonpath/yaybondi/
    ln -sf ../../misc/lib/yaybondi/error.py         .pythonpath/yaybondi/
    ln -sf ../../misc/lib/yaybondi/miscellaneous    .pythonpath/yaybondi/
    ln -sf ../../package/lib/yaybondi/package       .pythonpath/yaybondi/
    ln -sf ../../repository/lib/yaybondi/repository .pythonpath/yaybondi/
    ln -sf ../../image-gen/lib/yaybondi/osimage     .pythonpath/yaybondi/

    touch .pythonpath/yaybondi/__init__.py

    if [ "x$BONDI_LOCAL_PROJECT_SOURCED" = "x" ]; then
        export PYTHONPATH="$(pwd)/.pythonpath:$PYTHONPATH"

        PATH="$(pwd)/image-gen/bin:$PATH"
        PATH="$(pwd)/distro-info/bin:$PATH"
        PATH="$(pwd)/package/bin:$PATH"
        PATH="$(pwd)/repository/bin:$PATH"

        export PATH
        export PS1="(distro-tools)$PS1"
        export BONDI_LOCAL_PROJECT_SOURCED="yes"
    fi
fi

unset BONDI_ENVIRONMENT_SH_PRE_FLIGHT_CHECKS_OK
