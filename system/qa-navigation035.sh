#!/bin/sh
set -eu
cd /opt/astroall-qa035
mkdir -p /tmp/astroall-nav035/bin /tmp/astroall-nav035/home
cat > /tmp/astroall-nav035/bin/indi_astroall_oat <<'EOF'
#!/bin/sh
cd /opt/astroall-qa035
exec /usr/bin/python3 -m astroall.oat_driver
EOF
chmod 755 /tmp/astroall-nav035/bin/indi_astroall_oat
export PYTHONPATH=/opt/astroall-qa035
export HOME=/tmp/astroall-nav035/home
export PATH=/tmp/astroall-nav035/bin:$PATH
if [ "${1:-}" = workflow ]; then
    exec xvfb-run -a python3 tests/integration_workflow035.py
fi
exec xvfb-run -a python3 tests/integration_navigation035.py
