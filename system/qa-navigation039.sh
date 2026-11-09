#!/bin/sh
set -eu
cd /opt/astroall-qa039
mkdir -p /tmp/astroall-nav039/bin /tmp/astroall-nav039/home
cat > /tmp/astroall-nav039/bin/indi_astroall_oat <<'EOF'
#!/bin/sh
cd /opt/astroall-qa039
exec /usr/bin/python3 -m astroall.oat_driver
EOF
chmod 755 /tmp/astroall-nav039/bin/indi_astroall_oat
export PYTHONPATH=/opt/astroall-qa039
export HOME=/tmp/astroall-nav039/home
export PATH=/tmp/astroall-nav039/bin:$PATH
if [ "${1:-}" = workflow ]; then
    exec xvfb-run -a python3 tests/integration_workflow039.py
fi
exec xvfb-run -a python3 tests/integration_navigation039.py
