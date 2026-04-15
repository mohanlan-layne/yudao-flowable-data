#!/usr/bin/env bash
# BPM 服务配置

BPM_BASE_URL="http://192.168.1.182:30080"
TENANT_ID="1"
USERNAME="admin"
PASSWORD="admin123"

FLOWS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/flows"
