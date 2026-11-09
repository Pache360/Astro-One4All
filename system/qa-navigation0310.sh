#!/bin/sh
set -eu
cd /opt/astroall-qa0310
mkdir -p /tmp/astroall-nav0310/bin /tmp/astroall-nav0310/home
cat > /tmp/astroall-nav0310/bin/indi_astroall_oat <<'EOF'
#!/bin/sh
cd /opt/astroall-qa0310
exec /usr/bin/python3 -m astroall.oat_driver
EOF
chmod 755 /tmp/astroall-nav0310/bin/indi_astroall_oat
export PYTHONPATH=/opt/astroall-qa0310
export HOME=/tmp/astroall-nav0310/home
export PATH=/tmp/astroall-nav0310/bin:$PATH
if [ "${1:-}" = workflow ]; then
    exec xvfb-run -a python3 tests/integration_workflow0310.py
fi
exec xvfb-run -a python3 tests/integration_navigation0310.py
