import html
import logging
import os
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(message)s',
)

logging.getLogger("urllib3").setLevel(logging.INFO)
logging.getLogger("requests").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.INFO)

BASE_URL = "https://portal.ufsm.br/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "DNT": "1",
    "Sec-GPC": "1",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Priority": "u=0, i"
}

SECURITY_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://portal.ufsm.br",
    "Referer": "https://portal.ufsm.br/estudantil/j_security_check",
}

login_credentials = {
    "j_username": os.getenv("MATRICULA_LOGIN_UFSM"),
    "j_password": os.getenv("SENHA_LOGIN_UFSM"),
    "enter": ""
}

def renovar(emprestimo_id: str, title: str, session: requests.Session):
    f = session.get(BASE_URL+f"/biblioteca/leitor/renovaEmprestimo.html?idEmprestimo={emprestimo_id}",headers=HEADERS)
    if f.status_code == 500:
        logging.warning(f"Falha em renovar {title}")
    else:
        logging.info(f"Renovado: {title}")

def verificação_data(date: str):
    today = datetime.today()
    return (datetime.strptime(date, '%d/%m/%Y').date() == today.date())

def main():

    session = requests.Session()

    try:
        r = session.post(
            BASE_URL+"estudantil/j_security_check",
            headers=HEADERS | SECURITY_HEADERS,
            data=login_credentials,
            stream=True,
            timeout=25
        )

        r.raise_for_status()

        if "JSESSIONIDSSO" not in session.cookies:

            if "Manutenção" in html.unescape(r.text):
                logging.error("Site em manutenção, tente em outro momento")

            else: 
                logging.error("Matrícula ou senhas incorretas.")

            return

        r = session.get(
            BASE_URL+"/biblioteca/leitor/situacao.html",
            headers=HEADERS
        )

    except requests.exceptions.ConnectTimeout:
        logging.exception("Server took too long to respond, check if it's down.")
        return

    except Exception:
        logging.exception("An Error Ocurred!")
        return

    soup = BeautifulSoup(r.text, 'html.parser')
    emp_sec = soup.find("table",id="emprestimos")
    if emp_sec is None:
        logging.error("Tabela não encontrada!")
        return

    bks = emp_sec.find_all("tr")
    renovado = False

    for bk in bks[1:]:
        button = bk.find('button')
        if button is None:
            logging.critical("Elemento não encontrado, tentando continuar...")
            continue

        emprestimo_id = button.get('data-id')
        if emprestimo_id is None:
            logging.critical("ID não encontrado, tentando continuar...")
            continue

        date = bk.find_all("td")[5].get_text(strip=True)
        title = bk.find_all("td")[2].get_text(strip=True)

        try: 
            emprestimo_id = str(emprestimo_id)
        except ValueError:
            logging.error("ID não é do tipo esperado!")
            continue

        if verificação_data(date):
            renovar(emprestimo_id, title, session=session)
            renovado = True
            
    if not renovado:
        logging.info("Nenhum empréstimo foi renovado.")

if __name__ == "__main__":
    main()    