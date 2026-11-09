#!/bin/sh
set -eu
cd /opt/astroall-qa036
mkdir -p /tmp/astroall-nav036/bin /tmp/astroall-nav036/home
cat > /tmp/astroall-nav036/bin/indi_astroall_oat <<'EOF'
#!/bin/sh
cd /opt/astroall-qa036
exec /usr/bin/python3 -m astroall.oat_driver
EOF
chmod 755 /tmp/astroall-nav036/bin/indi_astroall_oat
export PYTHONPATH=/opt/astroall-qa036
export HOME=/tmp/astroall-nav036/home
export PATH=/tmp/astroall-nav036/bin:$PATH
if [ "${1:-}" = workflow ]; then
    exec xvfb-run -a python3 tests/integration_workflow036.py
fi
exec xvfb-run -a python3 tests/integration_navigation036.py
