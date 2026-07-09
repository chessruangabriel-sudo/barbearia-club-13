import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)
DB_NAME = "barbearia.db"

BARBEARIA_NOME = "Barbearia Club 13"
JANELA_DIAS = 7
HORARIO_ABERTURA = 8
HORARIO_FECHAMENTO = 21

def init_db():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('CREATE TABLE barbeiros (id INTEGER PRIMARY KEY, nome TEXT)')
        c.execute('CREATE TABLE reservas (id INTEGER PRIMARY KEY, barbeiro_id INTEGER, data TEXT, hora TEXT, nome_cliente TEXT, email_cliente TEXT)')
        c.execute("INSERT INTO barbeiros VALUES (1, 'Fabio Farias')")
        c.execute("INSERT INTO barbeiros VALUES (2, 'Pedro Lima')")
        conn.commit()
        conn.close()

@app.route('/')
def home():
    return send_from_directory('templates', 'index.html')

@app.route('/agendar', methods=['POST'])
def agendar():
    try:
        data = request.json
        barbeiro_id = int(data['barbeiro_id'])
        data_corte = data['data']
        hora_corte = data['hora']
        cliente = data['cliente']
        email = data['email']
        
        hoje = datetime.now().date()
        data_obj = datetime.strptime(data_corte, "%Y-%m-%d").date()
        dias = (data_obj - hoje).days
        
        if dias < 0:
            return jsonify({"erro": "No se puede agendar en el pasado"}), 400
        if dias > JANELA_DIAS:
            return jsonify({"erro": f"Maximo {JANELA_DIAS} dias"}), 400
        if data_obj.weekday() == 6:
            return jsonify({"erro": "Cerrado los domingos"}), 400
        
        hora, minuto = map(int, hora_corte.split(':'))
        if hora < HORARIO_ABERTURA or hora >= HORARIO_FECHAMENTO:
            return jsonify({"erro": "Horario fuera de rango"}), 400
        if minuto not in (0, 30):
            return jsonify({"erro": "Cada 30 minutos"}), 400
        
        hora_float = hora + minuto / 60.0
        if 11.5 <= hora_float <= 12.5:
            return jsonify({"erro": "Almuerzo (11:30-12:30)"}), 400
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT id FROM reservas WHERE barbeiro_id = ? AND data = ? AND hora = ?', (barbeiro_id, data_corte, hora_corte))
        if c.fetchone():
            conn.close()
            return jsonify({"erro": "Horario no disponible"}), 400
        
        c.execute('INSERT INTO reservas (barbeiro_id, data, hora, nome_cliente, email_cliente) VALUES (?, ?, ?, ?, ?)', (barbeiro_id, data_corte, hora_corte, cliente, email))
        conn.commit()
        conn.close()
        
        return jsonify({"sucesso": f"Agendado! Confirmacion enviada a {email}"}), 201
    except Exception as e:
        return jsonify({"erro": f"Error: {str(e)}"}), 500

@app.route('/agenda/<barbeiro>')
def agenda(barbeiro):
    if barbeiro.lower() == "fabio":
        nome = "Fabio Farias"
        bid = 1
    elif barbeiro.lower() == "pedro":
        nome = "Pedro Lima"
        bid = 2
    else:
        return "No encontrado", 404
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT data, hora, nome_cliente FROM reservas WHERE barbeiro_id = ? ORDER BY data, hora', (bid,))
    reservas = c.fetchall()
    conn.close()
    
    html = f"<html><head><title>Agenda</title><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'></head><body><div class='container p-4'><h1>{nome}</h1><a href='/' class='btn btn-secondary'>Volver</a><div class='row mt-3'>"
    for data, hora, cliente in reservas:
        html += f"<div class='col-md-3 mb-2'><div class='card bg-success text-white p-3'><strong>{hora}</strong><br>{cliente}<br>{data}</div></div>"
    html += "</div></div></body></html>"
    return html

if __name__ == '__main__':
    init_db()
    print("Barbearia iniciada")
    app.run(host='0.0.0.0', port=5000, debug=False)