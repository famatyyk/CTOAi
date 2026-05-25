#!/bin/bash
# Fix SSH authorized_keys for ctoa-vps-nopass key
set -e
NOPASS_KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOqq9dbJd6/NNQ71FpXLX1i0LGb1L3Hdw6JQqUW/FuRD ctoa-vps-nopass"
mkdir -p /home/ctoa/.ssh
grep -qF "$NOPASS_KEY" /home/ctoa/.ssh/authorized_keys 2>/dev/null || echo "$NOPASS_KEY" >> /home/ctoa/.ssh/authorized_keys
chmod 700 /home/ctoa/.ssh
chmod 600 /home/ctoa/.ssh/authorized_keys
chown -R ctoa:ctoa /home/ctoa/.ssh
echo "DONE - klucz dodany. Sprawdz: cat /home/ctoa/.ssh/authorized_keys"