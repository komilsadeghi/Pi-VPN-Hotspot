#!/bin/bash
# ============================================================
#  Pi VPN Hotspot - One-Click Installer
#  Turns your Raspberry Pi into a VPN WiFi hotspot
# ============================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root: sudo bash install.sh${NC}"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo ~"$USER_NAME")

echo -e "${CYAN}"
echo "========================================="
echo "   Pi VPN Hotspot - Installer"
echo "========================================="
echo -e "${NC}"

echo -e "${YELLOW}[1/8] Installing dependencies...${NC}"
apt-get update -qq
apt-get install -y -qq hostapd dnsmasq python3 python3-tk iptables curl wget > /dev/null 2>&1
echo -e "${GREEN}  Done${NC}"

echo -e "${YELLOW}[2/8] Installing xray...${NC}"
mkdir -p /usr/local/share/xray
cp "$SCRIPT_DIR/xray/xray" /usr/local/share/xray/xray
chmod +x /usr/local/share/xray/xray
ln -sf /usr/local/share/xray/xray /usr/local/bin/xray
echo -e "${GREEN}  Done${NC}"

echo -e "${YELLOW}[3/8] Installing xray config...${NC}"
mkdir -p /etc/xray
cp "$SCRIPT_DIR/config/xray.json" /etc/xray/config.json
echo -e "${GREEN}  Done${NC}"

echo -e "${YELLOW}[4/8] Configuring WiFi hotspot...${NC}"
systemctl stop hostapd 2>/dev/null || true

mkdir -p /etc/hostapd

cat > /etc/hostapd/hostapd.conf << 'HCEOF'
country_code=GB
interface=wlan0
driver=nl80211
ssid=PiVPN_Hotspot
hw_mode=g
channel=6
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=changeme123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
rsn_pairwise=CCMP
macaddr_acl=1
accept_mac_file=/etc/hostapd/hostapd.accept
HCEOF

echo "00:00:00:00:00:00" > /etc/hostapd/hostapd.accept

echo "DAEMON_CONF=\"/etc/hostapd/hostapd.conf\"" > /etc/default/hostapd

echo -e "${YELLOW}  Disabling NetworkManager for wlan0...${NC}"
mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/99-unmanaged-wlan0.conf << 'NMEOF'
[keyfile]
unmanaged-devices=interface:wlan0
NMEOF

echo -e "${GREEN}  Done${NC}"

echo -e "${YELLOW}[5/8] Configuring DHCP (dnsmasq)...${NC}"
cp /etc/dnsmasq.conf /etc/dnsmasq.conf.orig 2>/dev/null || true
cat > /etc/dnsmasq.conf << 'DCEOF'
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
dhcp-option=option:router,192.168.4.1
server=8.8.8.8
server=1.1.1.1
no-hosts
DCEOF
echo -e "${GREEN}  Done${NC}"

echo -e "${YELLOW}[6/8] Installing services and scripts...${NC}"
cp "$SCRIPT_DIR/config/proxy-setup.sh" /usr/local/bin/proxy-setup.sh
chmod +x /usr/local/bin/proxy-setup.sh

cp "$SCRIPT_DIR/config/proxy-setup.service" /etc/systemd/system/proxy-setup.service
cp "$SCRIPT_DIR/config/xray-proxy.service" /etc/systemd/system/xray-proxy.service
systemctl daemon-reload
systemctl enable hostapd dnsmasq proxy-setup xray-proxy 2>/dev/null
echo -e "${GREEN}  Done${NC}"

echo -e "${YELLOW}[7/8] Installing GUI app...${NC}"
cp "$SCRIPT_DIR/app/proxy_toggle.pyw" "$USER_HOME/Desktop/proxy_toggle.pyw"
chmod +x "$USER_HOME/Desktop/proxy_toggle.pyw"
chown "$USER_NAME:$USER_NAME" "$USER_HOME/Desktop/proxy_toggle.pyw"

cat > "$USER_HOME/Desktop/ProxyToggle.desktop" << 'DTEOF'
[Desktop Entry]
Name=Proxy Toggle
Comment=Toggle VPN Proxy
Exec=python3 /home/USER_PLACEHOLDER/Desktop/proxy_toggle.pyw
Icon=preferences-system-network
Terminal=false
Type=Application
Categories=Utility;
DTEOF
sed -i "s/USER_PLACEHOLDER/$USER_NAME/g" "$USER_HOME/Desktop/ProxyToggle.desktop"
chmod +x "$USER_HOME/Desktop/ProxyToggle.desktop"
chown "$USER_NAME:$USER_NAME" "$USER_HOME/Desktop/ProxyToggle.desktop"
echo -e "${GREEN}  Done${NC}"

echo -e "${YELLOW}[8/8] Configuring sudoers...${NC}"
cat > /etc/sudoers.d/pi-vpn-proxy << 'SUDOEOF'
_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl start xray-proxy, /usr/bin/systemctl stop xray-proxy, /usr/bin/systemctl restart xray-proxy, /usr/bin/systemctl is-active xray-proxy, /sbin/iptables *, /usr/bin/tee /etc/xray/config.json, /bin/bash -c *, /usr/bin/tee /home/_USER/Desktop/v2ray/v2ray.txt, /usr/bin/tee /home/_USER/v2ray_current.txt
SUDOEOF
sed -i "s/_USER/$USER_NAME/g" /etc/sudoers.d/pi-vpn-proxy
chmod 440 /etc/sudoers.d/pi-vpn-proxy
echo -e "${GREEN}  Done${NC}"

echo ""
echo -e "${GREEN}========================================="
echo "   Installation Complete!"
echo "=========================================${NC}"
echo ""
echo -e "  Hotspot: ${CYAN}PiVPN_Hotspot${NC}"
echo -e "  Password: ${CYAN}changeme123${NC}"
echo ""
echo -e "  ${YELLOW}Steps:${NC}"
echo -e "  1. Edit /etc/hostapd/hostapd.conf to change hotspot name/password"
echo -e "  2. Click ${CYAN}Proxy Toggle${NC} on desktop"
echo -e "  3. Paste your vless:// link and click Apply"
echo -e "  4. Click the circle to connect"
echo ""
echo -e "  ${YELLOW}Reboot recommended: sudo reboot${NC}"
