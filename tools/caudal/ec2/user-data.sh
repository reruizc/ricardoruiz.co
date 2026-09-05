#!/bin/bash
# user-data para la instancia de Caudal · Amazon Linux 2023 · arm64 (t4g).
# Lo ejecuta cloud-init UNA vez al primer arranque, como root. Idempotente a
# medias: si algo falla, `sudo bash /var/lib/cloud/instance/user-data.txt`.
#
# Qué deja: python3.12 + pypdf/boto3/requests/openpyxl, aws CLI v2, git, rsync,
# zona horaria de Bogotá (el crontab está en hora local), 4 GB de swap (los
# builds del dataset parsean JSON de 40 MB y t4g.small tiene 2 GB), el clon del
# repo público en /srv/caudal/ricardoruiz.co y el crontab de tools/caudal/ec2/.
# El ESTADO (Bases de datos/leyes-senado, ~8 GB) NO lo baja: lo manda la Mac con
# tools/caudal/ec2/sync-estado.sh. Los secretos tampoco: van por scp.
set -euxo pipefail
exec > >(tee -a /var/log/caudal-user-data.log) 2>&1

dnf -y update
dnf -y install python3.12 python3.12-pip git rsync tar gzip unzip cronie
systemctl enable --now crond

# python3 → 3.12 para los cron, sin tocar el python3 del sistema (dnf lo usa)
ln -sf /usr/bin/python3.12 /usr/local/bin/python3
ln -sf /usr/bin/pip3.12    /usr/local/bin/pip3
/usr/local/bin/pip3 install --quiet --upgrade pip
/usr/local/bin/pip3 install --quiet pypdf boto3 requests openpyxl

# aws CLI v2 (arm64)
cd /tmp && curl -sS "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o awscliv2.zip \
  && unzip -q -o awscliv2.zip && ./aws/install --update && rm -rf aws awscliv2.zip

timedatectl set-timezone America/Bogota

# swap (t4g.small = 2 GB RAM)
if ! swapon --show | grep -q swapfile; then
  fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# árbol de trabajo, del usuario ec2-user (los cron corren como él)
install -d -o ec2-user -g ec2-user /srv/caudal
sudo -u ec2-user bash -c '
  set -e
  cd /srv/caudal
  [ -d ricardoruiz.co ] || git clone --depth 1 https://github.com/reruizc/ricardoruiz.co.git
  mkdir -p "ricardoruiz.co/Bases de datos/leyes-senado" ~/.config/caudal
  chmod 700 ~/.config/caudal
  # crontab versionado en el repo; CAUDAL_REPO lo leen los run_*.sh
  crontab ricardoruiz.co/tools/caudal/ec2/crontab
'
echo "user-data OK $(date)"
