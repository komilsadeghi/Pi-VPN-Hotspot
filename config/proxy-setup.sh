#!/bin/bash
# Setup proxy and hotspot - runs on boot

sleep 3

# Ensure wlan0 has static IP
ip addr add 192.168.4.1/24 dev wlan0 2>/dev/null
ip link set wlan0 up

# Enable forwarding
sysctl -w net.ipv4.ip_forward=1

# Create proxy user if not exists
id proxyuser >/dev/null 2>&1 || useradd -r -s /bin/false proxyuser

# Ensure NetworkManager doesn't manage wlan0
sleep 2

# Flush nat chains
iptables -t nat -F PREROUTING
iptables -t nat -F OUTPUT
iptables -t nat -F POSTROUTING
iptables -F FORWARD

# PREROUTING: redirect wlan0 traffic to xray
iptables -t nat -A PREROUTING -d 192.168.4.1/32 -j RETURN
iptables -t nat -A PREROUTING -d 127.0.0.0/8 -j RETURN
iptables -t nat -A PREROUTING -p tcp --dport 12345 -j RETURN
iptables -t nat -A PREROUTING -p tcp --dport 10808 -j RETURN
iptables -t nat -A PREROUTING -i wlan0 -p tcp -j REDIRECT --to-ports 12345
iptables -t nat -A PREROUTING -i wlan0 -p udp --dport 53 -j REDIRECT --to-ports 12345

# OUTPUT: redirect Pi own traffic to xray
iptables -t nat -A OUTPUT -d 192.168.4.1/32 -j RETURN
iptables -t nat -A OUTPUT -d 127.0.0.0/8 -j RETURN
iptables -t nat -A OUTPUT -p tcp --dport 12345 -j RETURN
iptables -t nat -A OUTPUT -p tcp --dport 10808 -j RETURN
iptables -t nat -A OUTPUT -p tcp --dport 53 -j RETURN
iptables -t nat -A OUTPUT -p tcp -j REDIRECT --to-ports 12345

# NAT and forwarding
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
iptables -A FORWARD -i wlan0 -o eth0 -j ACCEPT
iptables -A FORWARD -i eth0 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT

# Re-add Docker PREROUTING jump (create chain if it doesn't exist)
iptables -t nat -N DOCKER 2>/dev/null || true
iptables -t nat -I PREROUTING 1 -m addrtype --dst-type LOCAL -j DOCKER 2>/dev/null || true

# Save rules
iptables-save > /etc/iptables.rules

echo "$(date) - proxy-setup complete" >> /var/log/proxy-setup.log
