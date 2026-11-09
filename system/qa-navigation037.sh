#!/bin/sh
set -eu
cd /opt/astroall-qa037
mkdir -p /tmp/astroall-nav037/bin /tmp/astroall-nav037/home
cat > /tmp/astroall-nav037/bin/indi_astroall_oat <<'EOF'
#!/bin/sh
cd /opt/astroall-qa037
exec /usr/bin/python3 -m astroall.oat_driver
EOF
chmod 755 /tmp/astroall-nav037/bin/indi_astroall_oat
export PYTHONPATH=/opt/astroall-qa037
export HOME=/tmp/astroall-nav037/home
export PATH=/tmp/astroall-nav037/bin:$PATH
if [ "${1:-}" = workflow ]; then
    exec xvfb-run -a python3 tests/integration_workflow037.py
fi
exec xvfb-run -a python3 tests/integration_navigation037.py
