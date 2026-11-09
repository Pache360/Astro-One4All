#!/bin/sh
# Isolated build VM only. Uses emulated serial hardware and a private HOME.
set -eu
cd /opt/astroall-qa033
export PYTHONPATH=/opt/astroall-qa033
mkdir -p /tmp/astroall-qa033-bin /tmp/astroall-connections033
cat > /tmp/astroall-qa033-bin/indi_astroall_oat <<'EOF'
#!/bin/sh
exec /usr/bin/python3 -m astroall.oat_driver
EOF
chmod 755 /tmp/astroall-qa033-bin/indi_astroall_oat
export PATH=/tmp/astroall-qa033-bin:$PATH
HOME=/tmp/astroall-connections033 python3 tests/integration_connections033.py
python3 tests/integration_oat.py
xvfb-run -a python3 tests/render_ui03.py
