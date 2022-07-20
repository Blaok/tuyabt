#!/usr/bin/sudo /bin/bash
set -e
cd "${0%/*}"
install tuyabt.py /srv/tuya/tuyabt
cp tuyabt.service /etc/systemd/system/
systemctl daemon-reload
systemctl restart tuyabt
