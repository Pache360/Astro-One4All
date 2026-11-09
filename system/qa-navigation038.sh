#!/bin/sh
set -eu
cd /opt/astroall-qa038
mkdir -p /tmp/astroall-nav038/bin /tmp/astroall-nav038/home
cat > /tmp/astroall-nav038/bin/indi_astroall_oat <<'EOF'
#!/bin/sh
cd /opt/astroall-qa038
exec /usr/bin/python3 -m astroall.oat_driver
EOF
chmod 755 /tmp/astroall-nav038/bin/indi_astroall_oat
export PYTHONPATH=/opt/astroall-qa038
export HOME=/tmp/astroall-nav038/home
export PATH=/tmp/astroall-nav038/bin:$PATH
if [ "${1:-}" = workflow ]; then
    exec xvfb-run -a python3 tests/integration_workflow038.py
fi
exec xvfb-run -a python3 tests/integration_navigation038.py
