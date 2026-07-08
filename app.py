from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
DB_NAME = "barbearia.db"

# --- CONFIGURAÇÕES DA BARBEARIA ---
BARBEARIA_NOME = "Barbearia Club 13"
JANELA_DIAS = 7
HORARIO_ABERTURA = 8
HORARIO_FECHAMENTO = 21
INTERVALO_ALMOCO_INICIO = 11.5  # 11:30
INTERVALO_ALMOCO_FIM = 12.5     # 12:30

# --- CONFIGURAÇÕES DE E-MAIL (ATUALIZE AQUI) ---
EMAIL_SENDER = "barbeariaclub298@gmail.com"
# ⚠️ IMPORTANTE: Substitua abaixo pela senha de app de 16 caracteres do Google
EMAIL_PASSWORD = "nfek xjft pnen ldfh" 
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_PORT = 587

# --- INICIALIZAÇÃO DO BANCO DE DADOS ---
def init_db():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS reservas')
        cursor.execute('DROP TABLE IF EXISTS barbeiros')
        
        cursor.execute('CREATE TABLE IF NOT EXISTS barbeiros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL)')
        cursor.execute('CREATE TABLE IF NOT EXISTS reservas (id INTEGER PRIMARY KEY AUTOINCREMENT, barbeiro_id INTEGER NOT NULL, data TEXT NOT NULL, hora TEXT NOT NULL, nome_cliente TEXT NOT NULL, email_cliente TEXT NOT NULL, FOREIGN KEY(barbeiro_id) REFERENCES barbeiros(id))')
        
        cursor.execute("INSERT INTO barbeiros (nome) VALUES ('Fábio Farias')")
        cursor.execute("INSERT INTO barbeiros (nome) VALUES ('Pedro Lima')")
        
        conn.commit()
        conn.close()
        print(f"✅ Banco de dados inicializado para {BARBEARIA_NOME}.")

# --- FUNÇÃO DE ENVIO DE E-MAIL ---
def enviar_email_confirmacao(cliente, email, barbeiro, data, hora):
    if not email:
        return False

    try:
        subject = f"Confirmação de Agendamento - {BARBEARIA_NOME}"
        body = f"""
        Olá {cliente},

        Seu agendamento na {BARBEARIA_NOME} foi confirmado com sucesso!

        Detalhes do Agendamento:
        ------------------------
        Barbeiro: {barbeiro}
        Data: {data}
        Horário: {hora}
        
        Este e-mail serve como o seu comprovante oficial.
        Em caso de dúvidas, entre em contato conosco.

        Atenciosamente,
        Equipe {BARBEARIA_NOME}
        """
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Conexão segura com o servidor Gmail
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"📧 Email de confirmação enviado para {email}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ ERRO CRÍTICO: Autenticação falhou. Verifique se a 'Senha de App' está correta no código.")
        return False
    except Exception as e:
        print(f"⚠️ Falha ao enviar email: {str(e)}")
        return False

# --- ROTAS ---

@app.route('/')
def home():
    caminho = os.path.join('templates', 'index.html')
    if not os.path.exists(caminho):
        return f"ERRO: Arquivo 'index.html' não encontrado em 'templates'.<br>Caminho: {caminho}", 500
    return send_from_directory('templates', 'index.html')

@app.route('/agendar', methods=['POST'])
def agendar_corte():
    data = request.json
    if not data or not all(k in data for k in ('barbeiro_id', 'data', 'hora', 'cliente', 'email')):
        return jsonify({"erro": "Dados incompletos. E-mail é obrigatório."}), 400

    barbeiro_id = int(data['barbeiro_id'])
    data_corte = data['data']
    hora_corte = data['hora']
    cliente = data['cliente']
    email = data['email']

    hoje = datetime.now().date()
    try:
        data_obj = datetime.strptime(data_corte, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"erro": "Formato de data inválido."}), 400

    diferenca_dias = (data_obj - hoje).days

    # 1. Validação da Janela de 7 Dias
    if diferenca_dias < 0:
        return jsonify({"erro": "🚫 Não é possível agendar datas passadas."}), 400
    if diferenca_dias > JANELA_DIAS:
        return jsonify({"erro": f"📅 Agendamentos permitidos apenas para os próximos {JANELA_DIAS} dias."}), 400

    # 2. Validação de Horário e Domingo
    try:
        dia_semana = data_obj.weekday()
        if dia_semana == 6: # Domingo
            return jsonify({"erro": "🚫 Fechado aos Domingos."}), 400

        hora, minuto = map(int, hora_corte.split(':'))
        hora_float = hora + (minuto / 60.0)
        
        if hora < HORARIO_ABERTURA or hora >= HORARIO_FECHAMENTO or (hora == HORARIO_FECHAMENTO and minuto > 0):
            return jsonify({"erro": "⏰ Horário fora do expediente (08:00 - 21:00)."}), 400
        if INTERVALO_ALMOCO_INICIO <= hora_float <= INTERVALO_ALMOCO_FIM:
            return jsonify({"erro": "🍽️ Horário de almoço (11:30 - 12:30)."}), 400
        if minuto != 0 and minuto != 30:
            return jsonify({"erro": "⏱️ Agendamentos somente a cada 30 minutos (ex: 08:00, 08:30)."}), 400
    except ValueError:
        return jsonify({"erro": "Formato de hora inválido."}), 400

    # 3. Verificar Conflito no Banco
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM reservas WHERE barbeiro_id = ? AND data = ? AND hora = ?', (barbeiro_id, data_corte, hora_corte))
    
    if cursor.fetchone():
        conn.close()
        return jsonify({"erro": "⛔ Horário indisponível para este barbeiro."}), 400

    # 4. Salvar e Enviar Email
    try:
        cursor.execute('INSERT INTO reservas (barbeiro_id, data, hora, nome_cliente, email_cliente) VALUES (?, ?, ?, ?, ?)', 
                       (barbeiro_id, data_corte, hora_corte, cliente, email))
        conn.commit()
        conn.close()
        
        # Determinar nome do barbeiro para o email
        barbeiro_nome = "Fábio Farias" if barbeiro_id == 1 else "Pedro Lima"
        
        # Tenta enviar o email
        enviar_email_confirmacao(cliente, email, barbeiro_nome, data_corte, hora_corte)
        
        return jsonify({"sucesso": f"✅ Agendamento confirmado! Um comprovante foi enviado para {email}."}), 201
    except Exception as e:
        conn.close()
        return jsonify({"erro": f"Erro interno no servidor: {str(e)}"}), 500

# --- ROTAS DE AGENDA (ADMIN) ---
@app.route('/agenda/<barbeiro>')
def agenda_barbeiro(barbeiro):
    barbeiro_nome = ""
    barbeiro_id = 0
    if barbeiro.lower() == "fabio":
        barbeiro_nome = "Fábio Farias"
        barbeiro_id = 1
    elif barbeiro.lower() == "pedro":
        barbeiro_nome = "Pedro Lima"
        barbeiro_id = 2
    else:
        return "Barbeiro não encontrado", 404

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT data, hora, nome_cliente, email_cliente FROM reservas WHERE barbeiro_id = ? ORDER BY data, hora', (barbeiro_id,))
    reservas = cursor.fetchall()
    conn.close()

    # Gerar Grid HTML
    grid_html = "<div class='row mt-3'>"
    reservas_por_data = {}
    for r in reservas:
        if r['data'] not in reservas_por_data:
            reservas_por_data[r['data']] = []
        reservas_por_data[r['data']].append(r)

    if not reservas_por_data:
        grid_html += "<p class='text-muted'>Nenhum agendamento para este barbeiro.</p>"
    else:
        for data, lista in sorted(reservas_por_data.items()):
            grid_html += f"<div class='col-12 mb-4'><h5 class='border-bottom pb-2'>{data}</h5><div class='row'>"
            for r in lista:
                status_class = "bg-success text-white"
                grid_html += f"""
                <div class='col-md-3 col-sm-6 mb-2'>
                    <div class='card p-2 {status_class} text-center'>
                        <strong>{r['hora']}</strong><br>
                        <small>{r['nome_cliente']}</small>
                    </div>
                </div>
                """
            grid_html += "</div></div>"
    grid_html += "</div>"

    return f"""
    <html>
        <head>
            <title>Agenda - {barbeiro_nome}</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>body {{ background: #f0f2f5; font-family: sans-serif; }} .card {{ border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}</style>
        </head>
        <body class="p-4">
            <div class="container">
                <h1 class="mb-4">📅 Agenda de {barbeiro_nome}</h1>
                <a href="/" class="btn btn-secondary mb-3">← Voltar para Agendamento</a>
                {grid_html}
            </div>
        </body>
    </html>
    """

if __name__ == '__main__':
    init_db()
    print(f"🚀 {BARBEARIA_NOME} v2.0 Iniciado!")
    app.run(host='0.0.0.0', port=5000, debug=False)