import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --------- Configurações ----------
EMAIL_SENDER = "barbeariaclub298@gmail.com"
EMAIL_PASSWORD = "nfek xjft pnen ldfh"   # <-- SENHA DE APP, 16 caracteres
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_PORT = 587

# --------- Mensagem ----------
msg = MIMEMultipart()
msg["From"] = EMAIL_SENDER
msg["To"] = EMAIL_SENDER
msg["Subject"] = "Teste de envio"

body = "Este é um e‑mail de teste enviado pelo seu script Python."
msg.attach(MIMEText(body, "plain"))

# --------- Envio ----------
context = ssl.create_default_context()
with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_PORT) as server:
    server.starttls(context=context)          # TLS
    server.login(EMAIL_SENDER, EMAIL_PASSWORD)
    server.send_message(msg)

print("Enviado!")