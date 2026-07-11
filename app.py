import os
import sqlite3
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, send_from_directory, render_template

app = Flask(__name__)
DB_NAME = "barbearia.db"

BARBEARIA_NOME = "Barbearia Club 13"
JANELA_DIAS = 7
HORARIO_ABERTURA = 8
HORARIO_FECHAMENTO = 21

# ==========================================================
# CONFIGURAÇÃO DE E-MAIL (fixo + senha no Render)
# ==========================================================
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "barbeariaclub298@gmail.com"
SMTP_PASS = os.environ.get("SMTP_PASS")  # coloque no Render

def init_db():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('CREATE TABLE barbeiros (id INTEGER PRIMARY KEY, nome TEXT)')
        c.execute('''CREATE TABLE reservas (
            id INTEGER PRIMARY KEY,
            barbeiro_id INTEGER,
            data TEXT,
            hora TEXT,
            nome_cliente TEXT,
            email_cliente TEXT
        )''')
        c.execute("INSERT INTO barbeiros VALUES (1, 'Fabio Farias')")
        c.execute("INSERT INTO barbeiros VALUES (2, 'Pedro Lima')")
        conn.commit()
        conn.close()
        print("✅ Banco criado")

def enviar_email(destinatario, cliente, data, hora, barbeiro):
    if not SMTP_PASS:
        print("⚠️ SMTP_PASS não configurado. Email NÃO enviado.")
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = f"{BARBEARIA_NOME} <{SMTP_USER}>"
        msg["To"] = destinatario
        msg["Subject"] = "✂️ Confirmação do seu corte - Barbearia Club 13"

        corpo = f"""
        <html>
        <body style="font-family:Arial; color:#2c3e50;">
            <h2>✂️ Barbearia Club 13</h2>
            <p>Olá <strong>{cliente}</strong>, seu horário foi confirmado!</p>
            <ul>
                <li><strong>📅 Data:</strong> {data}</li>
                <li><strong>🕐 Hora:</strong> {hora}</li>
                <li><strong>💈 Barbeiro:</strong> {barbeiro}</li>
            </ul>
            <p>Nos vemos na barbearia! 😎</p>
            <hr>
            <small>Barbearia Club 13 - Sistema v2.1</small>
        </body>
        </html>
        """
        msg.attach(MIMEText(corpo, "html"))

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email enviado para {destinatario}")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        return False

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
        c.execute('SELECT id FROM reservas WHERE barbeiro_id = ? AND data = ? AND hora = ?',
                  (barbeiro_id, data_corte, hora_corte))
        if c.fetchone():
            conn.close()
            return jsonify({"erro": "Horario no disponible"}), 400

        c.execute('INSERT INTO reservas (barbeiro_id, data, hora, nome_cliente, email_cliente) VALUES (?, ?, ?, ?, ?)',
                  (barbeiro_id, data_corte, hora_corte, cliente, email))
        conn.commit()
        conn.close()

        nome_barbeiro = "Fabio Farias" if barbeiro_id == 1 else "Pedro Lima"
        email_ok = enviar_email(email, cliente, data_corte, hora_corte, nome_barbeiro)

        if email_ok:
            return jsonify({"sucesso": f"¡Agendado! Confirmación enviada a {email}"}), 201
        else:
            return jsonify({"sucesso": "¡Agendado! (Email no enviado)"}), 201

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

    return render_template("agenda.html", nome=nome, reservas=reservas)

# ✅ IMPORTANTE: init_db fora do if __name__
init_db()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)