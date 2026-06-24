import tkinter as tk
from urllib.parse import urlparse, parse_qs, unquote
import subprocess
import json
import os


class ProxyToggle:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("VPN Proxy Control")
        self.root.geometry("400x620")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(False, False)

        self.is_on = self.check_status()

        title = tk.Label(
            self.root, text="VPN Proxy", font=("Helvetica", 24, "bold"),
            fg="white", bg="#1a1a2e"
        )
        title.pack(pady=(20, 5))

        self.status_label = tk.Label(
            self.root, text="", font=("Helvetica", 14),
            fg="white", bg="#1a1a2e"
        )
        self.status_label.pack(pady=(0, 15))

        self.canvas = tk.Canvas(
            self.root, width=200, height=200,
            bg="#1a1a2e", highlightthickness=0
        )
        self.canvas.pack()

        self.circle = self.canvas.create_oval(
            25, 25, 175, 175, fill="#2ecc71", outline="", width=0
        )
        self.power_text = self.canvas.create_text(
            100, 100, text="\u23FB", font=("Helvetica", 40, "bold"), fill="white"
        )

        self.canvas.bind("<Button-1>", self.toggle)
        self.canvas.configure(cursor="hand2")

        info = tk.Label(
            self.root, text="Click circle to toggle",
            font=("Helvetica", 10), fg="#888888", bg="#1a1a2e"
        )
        info.pack(pady=(5, 10))

        sep = tk.Frame(self.root, height=1, bg="#333355")
        sep.pack(fill="x", padx=40, pady=5)

        config_label = tk.Label(
            self.root, text="New Vless Config:",
            font=("Helvetica", 11, "bold"), fg="white", bg="#1a1a2e"
        )
        config_label.pack(anchor="w", padx=40, pady=(5, 2))

        self.config_entry = tk.Entry(
            self.root, font=("Helvetica", 9),
            bg="#16213e", fg="#00ff88", insertbackground="white",
            relief="flat", bd=0
        )
        self.config_entry.pack(fill="x", padx=40, pady=(0, 8), ipady=6)

        self.apply_btn = tk.Button(
            self.root, text="Apply Config", font=("Helvetica", 11, "bold"),
            bg="#0f3460", fg="white", activebackground="#1a5276",
            activeforeground="white", relief="flat", bd=0,
            cursor="hand2", command=self.apply_config
        )
        self.apply_btn.pack(fill="x", padx=40, ipady=4)

        self.msg_label = tk.Label(
            self.root, text="", font=("Helvetica", 9),
            fg="#888888", bg="#1a1a2e", wraplength=320
        )
        self.msg_label.pack(pady=(5, 0))

        self.update_display()
        self.root.mainloop()

    def run_cmd(self, cmd):
        return subprocess.run(
            ["sudo", "-n"] + cmd,
            capture_output=True, text=True
        )

    def check_status(self):
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "xray-proxy"],
                capture_output=True, text=True
            )
            return result.stdout.strip() == "active"
        except Exception:
            return False

    def update_display(self):
        if self.is_on:
            self.canvas.itemconfig(self.circle, fill="#2ecc71")
            self.status_label.config(text="Proxy is ON", fg="#2ecc71")
        else:
            self.canvas.itemconfig(self.circle, fill="#e74c3c")
            self.status_label.config(text="Proxy is OFF", fg="#e74c3c")

    def parse_vless(self, url):
        url = url.strip()
        if not url.startswith("vless://"):
            return None

        without_proto = url[len("vless://"):]
        hash_idx = without_proto.find("#")
        label = ""
        if hash_idx != -1:
            label = unquote(without_proto[hash_idx + 1:])
            without_proto = without_proto[:hash_idx]

        q_idx = without_proto.find("?")
        params = {}
        if q_idx != -1:
            query_str = without_proto[q_idx + 1:]
            params = parse_qs(query_str, keep_blank_values=True)
            server_part = without_proto[:q_idx]
        else:
            server_part = without_proto

        at_idx = server_part.find("@")
        if at_idx == -1:
            return None
        uuid = server_part[:at_idx]
        host_port = server_part[at_idx + 1:]
        colon_idx = host_port.rfind(":")
        if colon_idx == -1:
            return None
        server = host_port[:colon_idx]
        port = int(host_port[colon_idx + 1:])

        def get(key, default=""):
            val = params.get(key, [default])
            return unquote(val[0]) if val else default

        alpn_raw = get("alpn", "h2,http/1.1")
        alpn = [a.strip() for a in alpn_raw.split(",") if a.strip()]
        sni = get("sni", server)
        fp = get("fp", "chrome")
        net = get("type", "tcp")

        return {
            "uuid": uuid, "server": server, "port": port,
            "sni": sni, "fp": fp, "alpn": alpn,
            "network": net, "label": label
        }

    def apply_config(self):
        raw = self.config_entry.get().strip()
        if not raw:
            self.msg_label.config(text="Paste a vless:// link first", fg="#e74c3c")
            return

        parsed = self.parse_vless(raw)
        if not parsed:
            self.msg_label.config(text="Invalid vless:// link format", fg="#e74c3c")
            return

        was_on = self.is_on
        if was_on:
            self.run_cmd(["systemctl", "stop", "xray-proxy"])

        config = {
            "log": {"loglevel": "warning"},
            "inbounds": [
                {
                    "tag": "socks-in",
                    "port": 10808,
                    "protocol": "socks",
                    "listen": "0.0.0.0",
                    "settings": {"udp": True},
                    "sniffing": {"enabled": True, "destOverride": ["http", "tls"]}
                },
                {
                    "tag": "tproxy-in",
                    "port": 12345,
                    "protocol": "dokodemo-door",
                    "listen": "0.0.0.0",
                    "settings": {"network": "tcp,udp", "followRedirect": True},
                    "sniffing": {"enabled": True, "destOverride": ["http", "tls"]}
                }
            ],
            "outbounds": [
                {
                    "tag": "proxy",
                    "protocol": "vless",
                    "settings": {
                        "vnext": [{
                            "address": parsed["server"],
                            "port": parsed["port"],
                            "users": [{
                                "id": parsed["uuid"],
                                "encryption": "none"
                            }]
                        }]
                    },
                    "streamSettings": {
                        "network": parsed["network"],
                        "security": "tls",
                        "tlsSettings": {
                            "serverName": parsed["sni"],
                            "fingerprint": parsed["fp"],
                            "alpn": parsed["alpn"],
                            "allowInsecure": False
                        }
                    }
                },
                {"tag": "direct", "protocol": "freedom"}
            ],
            "routing": {
                "domainStrategy": "IPIfNonMatch",
                "rules": [
                    {"type": "field", "outboundTag": "direct",
                     "domain": ["domain:" + parsed["sni"]]},
                    {"type": "field", "outboundTag": "direct",
                     "ip": ["geoip:private"]},
                    {"type": "field", "inboundTag": ["tproxy-in", "socks-in"],
                     "outboundTag": "proxy"}
                ]
            }
        }

        config_json = json.dumps(config, indent=2)
        self.run_cmd(["bash", "-c",
                       f"echo '{config_json}' | sudo tee /etc/xray/config.json > /dev/null"])

        self.run_cmd(["bash", "-c",
                       f"echo '{raw}' > /home/{os.getlogin()}/v2ray_current.txt"])

        if was_on:
            self.run_cmd(["iptables", "-t", "nat", "-F", "PREROUTING"])
            self.run_cmd(["iptables", "-t", "nat", "-F", "OUTPUT"])
            for rule in [
                ["-A", "PREROUTING", "-d", "192.168.4.1/32", "-j", "RETURN"],
                ["-A", "PREROUTING", "-d", "127.0.0.0/8", "-j", "RETURN"],
                ["-A", "PREROUTING", "-p", "tcp", "--dport", "12345", "-j", "RETURN"],
                ["-A", "PREROUTING", "-p", "tcp", "--dport", "10808", "-j", "RETURN"],
                ["-A", "PREROUTING", "-d", parsed["server"] + "/32", "-j", "RETURN"],
                ["-A", "PREROUTING", "-i", "wlan0", "-p", "tcp", "-j", "REDIRECT",
                 "--to-ports", "12345"],
                ["-A", "PREROUTING", "-i", "wlan0", "-p", "udp", "--dport", "53",
                 "-j", "REDIRECT", "--to-ports", "12345"],
            ]:
                self.run_cmd(["iptables", "-t", "nat"] + rule)

            for rule in [
                ["-A", "OUTPUT", "-d", "192.168.4.1/32", "-j", "RETURN"],
                ["-A", "OUTPUT", "-d", "127.0.0.0/8", "-j", "RETURN"],
                ["-A", "OUTPUT", "-p", "tcp", "--dport", "12345", "-j", "RETURN"],
                ["-A", "OUTPUT", "-p", "tcp", "--dport", "10808", "-j", "RETURN"],
                ["-A", "OUTPUT", "-p", "tcp", "--dport", "53", "-j", "RETURN"],
                ["-A", "OUTPUT", "-d", parsed["server"] + "/32", "-j", "RETURN"],
                ["-A", "OUTPUT", "-p", "tcp", "-j", "REDIRECT", "--to-ports", "12345"],
            ]:
                self.run_cmd(["iptables", "-t", "nat"] + rule)

            self.run_cmd(["iptables", "-t", "nat", "-I", "PREROUTING", "1",
                           "-m", "addrtype", "--dst-type", "LOCAL", "-j", "DOCKER"])
            self.run_cmd(["iptables", "-t", "nat", "-A", "POSTROUTING",
                           "-o", "eth0", "-j", "MASQUERADE"])
            self.run_cmd(["iptables", "-A", "FORWARD", "-i", "wlan0",
                           "-o", "eth0", "-j", "ACCEPT"])
            self.run_cmd(["iptables", "-A", "FORWARD", "-i", "eth0", "-o", "wlan0",
                           "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"])
            self.run_cmd(["systemctl", "start", "xray-proxy"])

        lbl = parsed["label"] or parsed["server"]
        self.msg_label.config(
            text=f"Applied: {lbl}\n{parsed['server']}:{parsed['port']}",
            fg="#2ecc71"
        )

    def disable_redirect(self):
        self.run_cmd(["iptables", "-t", "nat", "-F", "PREROUTING"])
        self.run_cmd(["iptables", "-t", "nat", "-F", "OUTPUT"])
        self.run_cmd(["iptables", "-t", "nat", "-A", "PREROUTING",
                       "-m", "addrtype", "--dst-type", "LOCAL", "-j", "DOCKER"])
        self.run_cmd(["iptables", "-t", "nat", "-A", "POSTROUTING",
                       "-o", "eth0", "-j", "MASQUERADE"])
        self.run_cmd(["iptables", "-A", "FORWARD", "-i", "wlan0",
                       "-o", "eth0", "-j", "ACCEPT"])
        self.run_cmd(["iptables", "-A", "FORWARD", "-i", "eth0", "-o", "wlan0",
                       "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"])

    def enable_redirect(self):
        self.run_cmd(["iptables", "-t", "nat", "-F", "PREROUTING"])
        self.run_cmd(["iptables", "-t", "nat", "-F", "OUTPUT"])
        for rule in [
            ["-A", "PREROUTING", "-d", "192.168.4.1/32", "-j", "RETURN"],
            ["-A", "PREROUTING", "-d", "127.0.0.0/8", "-j", "RETURN"],
            ["-A", "PREROUTING", "-p", "tcp", "--dport", "12345", "-j", "RETURN"],
            ["-A", "PREROUTING", "-p", "tcp", "--dport", "10808", "-j", "RETURN"],
            ["-A", "PREROUTING", "-i", "wlan0", "-p", "tcp", "-j", "REDIRECT",
             "--to-ports", "12345"],
            ["-A", "PREROUTING", "-i", "wlan0", "-p", "udp", "--dport", "53",
             "-j", "REDIRECT", "--to-ports", "12345"],
        ]:
            self.run_cmd(["iptables", "-t", "nat"] + rule)

        for rule in [
            ["-A", "OUTPUT", "-d", "192.168.4.1/32", "-j", "RETURN"],
            ["-A", "OUTPUT", "-d", "127.0.0.0/8", "-j", "RETURN"],
            ["-A", "OUTPUT", "-p", "tcp", "--dport", "12345", "-j", "RETURN"],
            ["-A", "OUTPUT", "-p", "tcp", "--dport", "10808", "-j", "RETURN"],
            ["-A", "OUTPUT", "-p", "tcp", "--dport", "53", "-j", "RETURN"],
            ["-A", "OUTPUT", "-p", "tcp", "-j", "REDIRECT", "--to-ports", "12345"],
        ]:
            self.run_cmd(["iptables", "-t", "nat"] + rule)

        self.run_cmd(["iptables", "-t", "nat", "-I", "PREROUTING", "1",
                       "-m", "addrtype", "--dst-type", "LOCAL", "-j", "DOCKER"])
        self.run_cmd(["iptables", "-t", "nat", "-A", "POSTROUTING",
                       "-o", "eth0", "-j", "MASQUERADE"])
        self.run_cmd(["iptables", "-A", "FORWARD", "-i", "wlan0",
                       "-o", "eth0", "-j", "ACCEPT"])
        self.run_cmd(["iptables", "-A", "FORWARD", "-i", "eth0", "-o", "wlan0",
                       "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"])

    def toggle(self, event=None):
        if self.is_on:
            self.run_cmd(["systemctl", "stop", "xray-proxy"])
            self.disable_redirect()
            self.is_on = False
        else:
            self.enable_redirect()
            self.run_cmd(["systemctl", "start", "xray-proxy"])
            self.is_on = True
        self.update_display()


if __name__ == "__main__":
    ProxyToggle()
