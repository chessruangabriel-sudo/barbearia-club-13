import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
DB_NAME = "barbearia.db"

BARBEARIA_NOME = "Barbearia Club 13"
JANELA_DIAS = 7
HORARIO_ABERTURA = 8
HORARIO_FECHAMENTO = 21
INTERVALO_ALMOCO_INICIO = 11.5
INTERVALO_ALMOCO_FIM = 12.5

EMAIL_SENDER = os.getenv("EMAIL_SENDER", "barbeariaclub298@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "nfek xjft pnen ldfh")
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_PORT = 587

def init_db():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE barbeiros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL)')
        cursor.execute('CREATE TABLE reservas (id INTEGER PRIMARY KEY AUTOINCREMENT, barbeiro_id INTEGER NOT NULL, data TEXT NOT NULL, hora TEXT NOT NULL, nome_cliente TEXT NOT NULL, email_cliente TEXT NOT NULL, FOREIGN KEY(barbeiro_id) REFERENCES barbeiros(id))')
        cursor.execute("INSERT INTO barbeiros (nome) VALUES ('Fabio Farias')")
        cursor.execute("INSERT INTO barbeiros (nome) VALUES ('Pedro Lima')")
        conn.commit()
        conn.close()
        print("OK: Banco inicializado")

def enviar_email(cliente, email, barbeiro, data, hora):
    try:
        subject = f"Confirmacion - {BARBEARIA_NOME}"
        body = f"Hola {cliente},\n\nAgendamiento confirmado!\n\nBarbero: {barbeiro}\nFecha: {data}\nHora: {hora}\n\nAtentamente,\nEquipo {BARBEARIA_NOME}"
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        if EMAIL_PASSWORD and EMAIL_PASSWORD != "":
            context = ssl.create_default_context()
            with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_PORT) as server:
                server.starttls(context=context)
                server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                server.send_message(msg)
            print(f"Email enviado a {email}")
        else:
            print(f"Aviso: EMAIL_PASSWORD no configurada, email no enviado")
    except Exception as e:
        print(f"Aviso: Error al enviar email: {str(e)}")
        
@app.route('/')
def home():
    return send_from_directory('templates', 'index.html')

@app.route('/agendar', methods=['POST'])
def agendar_corte():
    data = request.json
    if not data or not all(k in data for k in ('barbeiro_id', 'data', 'hora', 'cliente', 'email')):
        return jsonify({"erro": "Datos incompletos"}), 400
    
    barbeiro_id = int(data['barbeiro_id'])
    data_corte = data['data']
    hora_corte = data['hora']
    cliente = data['cliente']
    email = data['email']
    
    hoje = datetime.now().date()
    try:
        data_obj = datetime.strptime(data_corte, "%Y-%m-%d").date()
    except:
        return jsonify({"erro": "Fecha invalida"}), 400
    
    dias = (data_obj - hoje).days
    if dias < 0:
        return jsonify({"erro": "No se puede agendar en el pasado"}), 400
    if dias > JANELA_DIAS:
        return jsonify({"erro": f"Maximo {JANELA_DIAS} dias"}), 400
    
    if data_obj.weekday() == 6:
        return jsonify({"erro": "Cerrado los domingos"}), 400
    
    try:
        hora, minuto = map(int, hora_corte.split(':'))
    except:
        return jsonify({"erro": "Hora invalida"}), 400
    
    if hora < HORARIO_ABERTURA or hora >= HORARIO_FECHAMENTO:
        return jsonify({"erro": "Horario fuera de rango"}), 400
    
    hora_float = hora + minuto / 60.0
    if INTERVALO_ALMOCO_INICIO <= hora_float <= INTERVALO_ALMOCO_FIM:
        return jsonify({"erro": "Almuerzo (11:30-12:30)"}), 400
    
    if minuto not in (0, 30):
        return jsonify({"erro": "Cada 30 minutos"}), 400
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM reservas WHERE barbeiro_id = ? AND data = ? AND hora = ?', (barbeiro_id, data_corte, hora_corte))
    if cursor.fetchone():
        conn.close()
        return jsonify({"erro": "Horario no disponible"}), 400
    
    cursor.execute('INSERT INTO reservas (barbeiro_id, data, hora, nome_cliente, email_cliente) VALUES (?, ?, ?, ?, ?)', (barbeiro_id, data_corte, hora_corte, cliente, email))
    conn.commit()
    conn.close()
    
    barbeiro_nome = "Fabio Farias" if barbeiro_id == 1 else "Pedro Lima"
    enviar_email(cliente, email, barbeiro_nome, data_corte, hora_corte)
    
    return jsonify({"sucesso": f"Agendado! Confirmacion enviada a {email}"}), 201

@app.route('/agenda/<barbeiro>')
def agenda_barbeiro(barbeiro):
    if barbeiro.lower() == "fabio":
        nome = "Fabio Farias"
        bid = 1
    elif barbeiro.lower() == "pedro":
        nome = "Pedro Lima"
        bid = 2
    else:
        return "No encontrado", 404
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT data, hora, nome_cliente FROM reservas WHERE barbeiro_id = ? ORDER BY data, hora', (bid,))
    reservas = cursor.fetchall()
    conn.close()
    
    html = f"<html><head><title>Agenda - {nome}</title><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'><style>body{{padding:20px;background:#f0f2f5}}</style></head><body><div class='container'><h1>Agenda de {nome}</h1><a href='/' class='btn btn-secondary mb-3'>Volver</a>"
    
    if not reservas:
        html += "<p>Sin agendamientos</p>"
    else:
        html += "<div class='row'>"
        for data, hora, cliente in reservas:
            html += f"<div class='col-md-3 mb-2'><div class='card bg-success text-white p-3 text-center'><strong>{hora}</strong><br><small>{cliente}</small><br><small>{data}</small></div></div>"
        html += "</div>"
    
    html += "</div></body></html>"
    return html

if __name__ == '__main__':
    init_db()
    print("Barbearia Club 13 iniciada")
    app.run(host='0.0.0.0', port=5000, debug=False)