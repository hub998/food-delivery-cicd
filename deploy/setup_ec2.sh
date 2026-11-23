#!/usr/bin/env bash
# ONE-TIME server setup. Paste this into "User data" when launching the EC2 instance
# (Amazon Linux 2023), or run it once with sudo. The pipeline does everything else.
set -euxo pipefail
dnf install -y python3 python3-pip unzip
mkdir -p /opt/foodapp/releases
