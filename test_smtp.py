"""
Teste isolado de envio SMTP - rode localmente (nao faz parte do app em producao).

Uso:
    python test_smtp.py

Le as mesmas variaveis do .env que o app.py usa. Mostra o dialogo completo
com o servidor SMTP (server.set_debuglevel(1)), entao da pra ver exatamente
em que ponto o envio falha ou se ele e aceito pelo Gmail.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")

if not SMTP_USER or not SMTP_PASS:
    print("ERRO: SMTP_USER ou SMTP_PASS nao encontrados. Confira o arquivo .env.")
    raise SystemExit(1)

destino = input("E-mail de destino para o teste: ").strip()

msg = MIMEText("Este e um teste de envio SMTP do projeto Barbearia Club 13.", _charset="utf-8")
msg["Subject"] = Header("Teste SMTP - Barbearia Club 13", "utf-8")
msg["From"] = SMTP_USER
msg["To"] = destino

print(f"\nConectando em {SMTP_HOST}:{SMTP_PORT} como {SMTP_USER}...\n")

try:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        server.set_debuglevel(1)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        recusados = server.sendmail(SMTP_USER, [destino], msg.as_string())
        print("\n" + "=" * 50)
        if recusados:
            print(f"RECUSADO para: {recusados}")
        else:
            print("ACEITO pelo servidor SMTP para todos os destinatarios.")
            print("Se mesmo assim nao chegar, o problema e de entrega")
            print("(pasta de spam, limite diario do Gmail, etc), nao de codigo.")
except smtplib.SMTPAuthenticationError as e:
    print(f"\nERRO DE AUTENTICACAO: {e}")
    print("Confira se SMTP_PASS e uma senha de app de 16 digitos, nao a senha normal.")
except Exception as e:
    print(f"\nERRO: {type(e).__name__}: {e}")
