# Pi VPN Hotspot

Turn your Raspberry Pi into a **WiFi VPN hotspot**. Any device that connects to the Pi's WiFi will have its traffic automatically routed through a VLESS proxy.


#### Don't forget to extract xray in xray folder

## What It Does

- Creates a WiFi hotspot (`PiVPN_Hotspot`)
- Runs Xray transparent proxy
- All connected devices go through the VPN automatically
- GUI app to toggle proxy ON/OFF and change configs
- One-click install — transfer the folder to a new Pi and run `install.sh`

## Requirements

- Raspberry Pi (ARM64, Pi 4/5 recommended)
- Raspberry Pi OS (Bookworm or later)
- Ethernet cable connected (for internet)
- WiFi adapter (built-in or USB)
- A VLESS config link

## Quick Install (One Command)

```bash
# Copy the v2ray2 folder to your Pi, then:
sudo bash install.sh
```

That's it! Reboot after install:
```bash
sudo reboot
```

## After Install

1. Connect your phone/laptop to **PiVPN_Hotspot** (password: `changeme123`)
2. Click **Proxy Toggle** on the Pi desktop
3. Paste your `vless://` link in the text box
4. Click **Apply Config**
5. Click the **green circle** to connect
6. Browse freely!

## What the Installer Does

The `install.sh` script handles everything automatically:

| Step | Action |
|------|--------|
| 1 | Installs hostapd, dnsmasq, python3-tk, iptables |
| 2 | Installs Xray binary to `/usr/local/share/xray/` |
| 3 | Copies Xray config template to `/etc/xray/config.json` |
| 4 | Configures hostapd WiFi hotspot on `wlan0` |
| 5 | Configures dnsmasq DHCP (192.168.4.2-20) |
| 6 | Installs boot service (`proxy-setup`) and xray service |
| 7 | Installs GUI app to desktop |
| 8 | Configures passwordless sudo for proxy commands |
| **NEW** | Disables NetworkManager for `wlan0` to prevent conflicts |
| **NEW** | Sets up MAC address filter in hostapd |

## Change Hotspot Name/Password

Edit `/etc/hostapd/hostapd.conf`:
```
ssid=YourHotspotName
wpa_passphrase=YourPassword
```
Then restart: `sudo systemctl restart hostapd`

## Project Structure

```
v2ray2/
├── install.sh              # One-click installer
├── README.md               # This file
├── app/
│   ├── proxy_toggle.pyw    # GUI app (tkinter)
│   └── ProxyToggle.desktop # Desktop shortcut
├── config/
│   ├── xray.json           # Xray config template
│   ├── proxy-setup.sh      # iptables setup script (runs on boot)
│   ├── proxy-setup.service # Systemd: runs setup on boot
│   └── xray-proxy.service  # Systemd: runs xray
└── xray/
    └── xray                # Xray binary (ARM64)
```

## How It Works

1. **hostapd** broadcasts WiFi hotspot on `wlan0`
2. **dnsmasq** assigns IPs (192.168.4.2-20) and handles DNS
3. **iptables** redirects all wlan0 traffic to Xray's tproxy port
4. **Xray** tunnels traffic through your VLESS server
5. **proxy-toggle.pyw** lets you control everything with one click

## Services

| Service | Purpose |
|---------|---------|
| `hostapd` | WiFi hotspot |
| `dnsmasq` | DHCP + DNS |
| `proxy-setup` | Sets iptables rules on boot |
| `xray-proxy` | Runs the VPN tunnel |

## Backup & Restore

This folder (`v2ray2/`) is your **complete backup**. To restore to a new Pi:

```bash
# Copy the folder to the new Pi
scp -r v2ray2/ komil@NEW_PI_IP:~/

# SSH into the new Pi
ssh komil@NEW_PI_IP

# Run the installer
sudo bash ~/v2ray2/install.sh

# Reboot
sudo reboot
```

After reboot, the hotspot will be broadcasting and ready to use.

## Troubleshooting

```bash
# Check if services are running
sudo systemctl status hostapd dnsmasq xray-proxy

# Check xray logs
sudo journalctl -u xray-proxy -f

# Test proxy connectivity
curl -x socks5://127.0.0.1:10808 https://api.ipify.org

# Restart everything
sudo systemctl restart hostapd dnsmasq proxy-setup xray-proxy
```

### Common Issues

**Hotspot not showing after reboot:**
```bash
# Check if NetworkManager is managing wlan0 (it shouldn't)
sudo nmcli device

# If wlan0 shows as "connected" or "disconnected" in NM, fix it:
echo -e "[keyfile]\nunmanaged-devices=interface:wlan0" | sudo tee /etc/NetworkManager/conf.d/99-unmanaged-wlan0.conf
sudo systemctl restart NetworkManager
sudo systemctl restart hostapd
```

**wlan0 is DOWN or NO-CARRIER:**
```bash
# Check WiFi radio state
sudo rfkill list

# If soft-blocked:
sudo rfkill unblock wifi

# Restart hostapd
sudo systemctl restart hostapd
```

**iptables Docker chain error on boot:**
The `proxy-setup` script creates the Docker chain if it doesn't exist. If you see errors in logs:
```bash
sudo journalctl -u proxy-setup
sudo systemctl restart proxy-setup
```

**WiFi interface is managed mode instead of AP:**
```bash
# Stop NetworkManager from touching wlan0
sudo nmcli device set wlan0 managed no
sudo ip link set wlan0 down
sudo ip link set wlan0 up
sudo systemctl restart hostapd

# Check AP mode
sudo iw dev wlan0 info
# Should show: type AP
```

**Complete reset of all proxy rules:**
```bash
sudo systemctl stop xray-proxy
sudo bash /usr/local/bin/proxy-setup.sh
sudo systemctl start xray-proxy
```

## License

Open source. Use freely.
