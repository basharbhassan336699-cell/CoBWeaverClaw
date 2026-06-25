#!/bin/bash
# CoBWeaverClaw Installer
# One-line install: curl -sSL https://get.cobweaverclaw.ai | bash

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "${CYAN}"
echo "  ╔═══════════════════════════════╗"
echo "  ║   🕷️  CoBWeaverClaw Installer  ║"
echo "  ╚═══════════════════════════════╝"
echo "${NC}"

# Detect platform
detect_platform() {
    if [ -n "$ANDROID_ROOT" ] || [ -n "$TERMUX_VERSION" ]; then
        echo "android"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif grep -q "Raspberry" /proc/cpuinfo 2>/dev/null; then
        echo "raspi"
    elif [ -f "/system/xbin/bash" ]; then
        echo "ios"
    else
        echo "linux"
    fi
}

PLATFORM=$(detect_platform)
echo "${GREEN}✅ Platform detected: $PLATFORM${NC}"

# Install Python
echo "📦 Installing dependencies..."
case $PLATFORM in
    android) pkg install python git -y ;;
    macos)   brew install python3 git ;;
    raspi|linux) apt-get install -y python3 python3-pip git 2>/dev/null || yum install -y python3 git ;;
    ios)     apk add python3 git ;;
esac

# Install CoBWeaverClaw
pip3 install --quiet pyyaml aiohttp chromadb 2>/dev/null || true

# Clone or download
if command -v git &>/dev/null; then
    git clone --depth=1 https://github.com/basharbhassan336699-cell/CoBWeaverClaw ~/.cobweaverclaw/agent 2>/dev/null || true
fi

# Setup config
mkdir -p ~/.cobweaverclaw
if [ ! -f ~/.cobweaverclaw/config.yaml ]; then
    cp ~/.cobweaverclaw/agent/config.yaml ~/.cobweaverclaw/config.yaml 2>/dev/null || true
fi

# Token setup
echo ""
echo "🔑 Enter your token (or press Enter to register new account):"
read USER_TOKEN

if [ -z "$USER_TOKEN" ]; then
    echo "${GREEN}🌐 Opening registration...${NC}"
    echo "Register at: https://cobweaverclaw.ai/register"
else
    echo "TOKEN=$USER_TOKEN" >> ~/.cobweaverclaw/.env
    echo "${GREEN}✅ Token saved${NC}"
fi

echo ""
echo "${GREEN}🕷️  CoBWeaverClaw installed successfully!${NC}"
echo ""
echo "  Start:    python3 ~/.cobweaverclaw/agent/main.py"
echo "  Diagnose: python3 ~/.cobweaverclaw/agent/main.py doctor"
echo "  Help:     python3 ~/.cobweaverclaw/agent/main.py help"
