import os
import sqlite3
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header
from flask import Flask, request, jsonify, send_from_directory, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
DB_NAME = "barbearia.db"

BARBEARIA_NOME = "Barbearia Club 13"
JANELA_DIAS = 7
HORARIO_ABERTURA = 8
HORARIO_FECHAMENTO = 21

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp-relay.brevo.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("b1c1ca001@smtp-brevo.com")
SMTP_PASS = os.environ.get("SMPT_PASS")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)  # endereco que aparece como remetente; na Brevo pode ser diferente do login

BARBEIROS = {1: "Fabio Farias", 2: "Pedro Lima"}


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


# Chamado no nível do módulo: gunicorn importa "app:app" e nunca executa o
# bloco "if __name__ == '__main__'", então init_db() precisa rodar aqui fora,
# senão as tabelas nunca são criadas em produção.
init_db()


def enviar_email_confirmacao(destinatario, cliente, data_corte, hora_corte, barbeiro_nome):
    """Envia e-mail de confirmação via SMTP+STARTTLS. Lança exceção se falhar (tratado pelo caller)."""
    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("SMTP_USER/SMTP_PASS ausentes nas variáveis de ambiente")

    corpo = (
        f"Olá {cliente},\n\n"
        f"Seu agendamento na {BARBEARIA_NOME} está confirmado:\n\n"
        f"Barbeiro: {barbeiro_nome}\n"
        f"Data: {data_corte}\n"
        f"Horário: {hora_corte}\n\n"
        f"Até breve!"
    )
    msg = MIMEText(corpo, _charset="utf-8")
    msg["Subject"] = Header(f"Confirmação de Agendamento - {BARBEARIA_NOME}", "utf-8")
    msg["From"] = SMTP_FROM
    msg["To"] = destinatario

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        recusados = server.sendmail(SMTP_FROM, [destinatario], msg.as_string())
        if recusados:
            raise smtplib.SMTPRecipientsRefused(recusados)


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

        if barbeiro_id not in BARBEIROS:
            return jsonify({"erro": "Barbeiro inválido"}), 400

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
        c.execute(
            'SELECT id FROM reservas WHERE barbeiro_id = ? AND data = ? AND hora = ?',
            (barbeiro_id, data_corte, hora_corte)
        )
        if c.fetchone():
            conn.close()
            return jsonify({"erro": "Horario no disponible"}), 400

        c.execute(
            'INSERT INTO reservas (barbeiro_id, data, hora, nome_cliente, email_cliente) VALUES (?, ?, ?, ?, ?)',
            (barbeiro_id, data_corte, hora_corte, cliente, email)
        )
        conn.commit()
        conn.close()

        try:
            enviar_email_confirmacao(email, cliente, data_corte, hora_corte, BARBEIROS[barbeiro_id])
            print(f"[OK] E-mail enviado para {email}")
            return jsonify({"sucesso": f"Agendado! Confirmacion enviada a {email}", "email_enviado": True}), 201
        except Exception as email_err:
            print(f"[AVISO] Falha no envio de e-mail para {email}: {type(email_err).__name__}: {email_err}")
            return jsonify({"sucesso": "Agendado! (Falha no envio do e-mail de confirmação, mas seu horário está garantido)", "email_enviado": False}), 201

    except Exception as e:
        return jsonify({"erro": f"Error: {str(e)}"}), 500


DIAS_SEMANA = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def formatar_data_extenso(data_iso):
    d = datetime.strptime(data_iso, "%Y-%m-%d").date()
    return f"{DIAS_SEMANA[d.weekday()]}, {d.day} de {MESES[d.month - 1]}"


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

    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            'SELECT data, hora, nome_cliente FROM reservas WHERE barbeiro_id = ? ORDER BY data, hora',
            (bid,)
        )
        reservas = c.fetchall()
        conn.close()

        hoje = datetime.now().date().isoformat()
        dias = {}
        for data, hora, cliente in reservas:
            dias.setdefault(data, []).append({"hora": hora, "cliente": cliente})

        agenda_por_dia = []
        for data, horarios in dias.items():
            try:
                data_extenso = formatar_data_extenso(data)
            except ValueError:
                data_extenso = data  # formato inesperado: mostra a data crua em vez de quebrar a pagina inteira
            agenda_por_dia.append({
                "data_extenso": data_extenso,
                "hoje": data == hoje,
                "horarios": horarios
            })

        return render_template('agenda.html', nome=nome, agenda_por_dia=agenda_por_dia, total=len(reservas))

    except Exception as e:
        print(f"[ERRO] Falha ao carregar agenda de {nome}: {type(e).__name__}: {e}")
        return (
            f"<h1>Erro ao carregar a agenda</h1>"
            f"<p><strong>{type(e).__name__}</strong>: verifique o log do servidor no Render para o detalhe completo.</p>"
            f"<p>Causa mais provável: <code>templates/agenda.html</code> nao chegou no deploy.</p>"
            f"<a href='/'>Voltar</a>"
        ), 500


@app.route('/versao')
def versao():
    return jsonify({
        "versao": "2026-07-12-v4-brevo",
        "smtp_host_padrao": SMTP_HOST,
        "agenda_com_tratamento_erro": True
    })


if __name__ == '__main__':
    print("Barbearia iniciada")
    app.run(host='0.0.0.0', port=5000, debug=False)
