# Barbearia Club 13 - Sistema de Agendamento

## Visão Geral
Sistema web completo para agendamento de cortes de cabelo com validação de horários, gestão de barbeiros e envio automático de confirmação por e-mail.

## Funcionalidades
- **Agendamento Inteligente:** Bloqueio automático de domingos, horário de almoço (11:30-12:30) e intervalos de 30 min.
- **Janela de 7 Dias:** Impede agendamentos muito longos para evitar sobrecarga.
- **Confirmação por E-mail:** O cliente recebe um comprovante automático.
- **Painel do Barbeiro:** Visualização exclusiva para Fábio Farias e Pedro Lima.
- **Segurança:** Validação de dados no servidor e frontend.

## Instalação Rápida
1. Certifique-se de ter o Python 3.8+ instalado.
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt