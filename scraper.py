from playwright.sync_api import sync_playwright
import time
import os
import random
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import random


EMAIL_REMETENTE = "lauren@dpaplus.com"
EMAIL_SENHA = "svhdnjzithvgbdkh"
EMAIL_DESTINATARIO = "laurencampregher@gmail.com"
TELEFONE = "13996110880"
ENDERECO = "Pasteur"

# rodar com:
#   source venv/bin/activate
#   python3 scraper.py



def espera_humana(min_sec=1, max_sec=3):
    time.sleep(random.uniform(min_sec, max_sec))

def do_login():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            slow_mo=300,
            args=['--disable-blink-features=AutomationControlled']
        )
        page = browser.new_page()
        
        print("1 Acessando iFood...")
        page.goto("https://www.ifood.com.br/entrar/celular")
        
        print("2 Preenchendo número de telefone...")
        page.fill("input[name='phone']", TELEFONE)
        
        print("3 Clicando em WhatsApp...")
        page.wait_for_selector("button:has-text('WhatsApp'):not([disabled])", state="visible")
        page.click("button:has-text('WhatsApp')")
        
        print("📱 Complete o login (código + email)...")
        page.pause()
        
        print("Aguardando modal de endereços...")
        page.wait_for_selector(f"text={ENDERECO}", state="visible")
        
        print(f"Selecionando endereço '{ENDERECO}'...")
        page.locator(f".btn-address__container:has-text('{ENDERECO}')").first.click()
        
        print("Aguardando página carregar...")
        page.wait_for_load_state("domcontentloaded")
        
        print("Salvando sessão COM login completo...")
        page.context.storage_state(path="ifood_session.json")
        print("✅ Sessão salva!")
        
        browser.close()


def colorir_desconto(desconto):
    negrito = "\033[1m"
    reset = "\033[0m"
    
    if 24 <= desconto < 33:
        return f"{negrito}\033[38;5;208m{desconto}%{reset}"
    elif 33 <= desconto <= 40:
        return f"{negrito}\033[31m{desconto}%{reset}"
    elif desconto > 40:
        return f"{negrito}\033[35m{desconto}%{reset}"
    else:
        return f"{desconto}%"


def scrape_ofertas(mercado_slug):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            slow_mo=random.randint(200, 500),
            args=[
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        if not os.path.exists("ifood_session.json"):
            print("❌ Sessão não encontrada! Execute fazer_login() primeiro.")
            browser.close()
            return
        
        print("✅ Carregando sessão salva...")
        context = browser.new_context(
            storage_state="ifood_session.json",
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='pt-BR',
            timezone_id='America/Sao_Paulo'
        )
        
        page = context.new_page()
        # Remove detecção de webdriver
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en']});
        """)
        
        print("Acessando iFood (já logado)...")
        page.goto("https://www.ifood.com.br/mercados")

        espera_humana(3, 5)


        print("Esperando modal de endereços abrir...")
        page.wait_for_selector(".address-modal-overlay--after-open", state="visible")
        page.wait_for_selector(".address-list[data-test-id='address-list']", state="visible")
        
        
        print("🎉 Você está logado!")
        page.locator(f".btn-address__container:has-text('{ENDERECO}')").first.click()

        page.wait_for_selector(".address-modal-overlay", state="hidden", timeout=5000)

        print("Busca mercado...")
        page.fill("input[data-test-id='search-input-field']", mercado_slug)
        espera_humana(1, 2)

        page.press("input[data-test-id='search-input-field']", "Enter")
        espera_humana(2, 4)

        print("Esperando resultados da busca...")
        page.wait_for_selector(".merchant-list-v2__item-wrapper")

        espera_humana(1, 2)

        print("Clicando no primeiro resultado...")
        page.locator(".merchant-v2__link").first.click()

        print("Esperando produtos carregarem...")
        page.wait_for_selector(".product-card-wrapper", state="visible")

        print("Coletando categorias...")
        categorias = page.locator(".aisle-menu__item__link__name").all()

        categorias_lista = []
        for i, cat in enumerate(categorias):
            nome = cat.inner_text()
            if i > 0:
                categorias_lista.append(nome)

        print(f"Encontradas {len(categorias_lista)} categorias:")

        produtos_mercado = []

        for categoria in categorias_lista:
            print(f"\nProcessando categoria: {categoria}")
            
            page.click(f".aisle-menu__item__link__name:has-text('{categoria}')")
            page.wait_for_selector(".product-card-wrapper", state="visible")
            
            print("Carregando todos os produtos...")
            produtos_anteriores = 0
            while True:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
                
                produtos_atuais = page.locator(".product-card-wrapper").count()
                
                if produtos_atuais == produtos_anteriores:
                    break
                
                produtos_anteriores = produtos_atuais
                print(f"  Carregados {produtos_atuais} produtos...")
            
            print(f"Total: {produtos_atuais} produtos. Coletando descontos...")
            
            produtos_com_desconto = page.evaluate("""
                () => {
                    const produtos = [];
                    const cards = document.querySelectorAll('.product-card-wrapper');
                    
                    cards.forEach(card => {
                        const descontoEl = card.querySelector('.product-card__price--discount-percentage');
                        
                        if (descontoEl) {
                            const descontoTexto = descontoEl.textContent.trim();
                            const desconto = parseInt(descontoTexto.replace('-', '').replace('%', ''));
                            
                            if (desconto >= 24) {
                                const nome = card.querySelector('.product-card__description')?.textContent.trim();
                                const precoDesconto = card.querySelector('.product-card__price--discount')?.textContent.split('R$')[1]?.split('-')[0]?.trim();
                                
                                produtos.push({
                                    nome: nome,
                                    desconto: desconto,
                                    precoDesconto: precoDesconto
                                });
                            }
                        }
                    });
                    
                    return produtos;
                }
            """)

            produtos_mercado.extend(produtos_com_desconto)
            
            print(f"  Encontrados {len(produtos_com_desconto)} produtos com desconto >= 24%")
            for p in produtos_com_desconto:
                print(f"    - {p['nome']} ({colorir_desconto(p['desconto'])}) - R$ {p['precoDesconto']}")


        
        # page.pause()

        browser.close()

        return produtos_mercado


def enviar_email(todos_produtos):
    # Cria versão HTML
    html = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; }
            h2 { color: #333; border-bottom: 2px solid #ddd; padding-bottom: 5px; }
            .produto { margin: 10px 0; }
            .desconto-laranja { background-color: #ff8c00; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold; }
            .desconto-vermelho { background-color: #b22222; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold; }
            .desconto-roxo { background-color: #7c00df; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🛒 PRODUTOS COM DESCONTO >= 24%</h1>
    """
    
    for mercado, produtos in todos_produtos.items():
        html += f"<h2>🏪 {mercado.upper()}</h2>"
        
        if not produtos:
            html += "<p>Nenhum produto encontrado</p>"
        else:
            for p in produtos:
                desconto = p['desconto']
                
                if 24 <= desconto < 33:
                    cor_class = "desconto-laranja"
                elif 33 <= desconto <= 40:
                    cor_class = "desconto-vermelho"
                else:
                    cor_class = "desconto-roxo"
                
                html += f'<div class="produto">- {p["nome"]} <span class="{cor_class}">{desconto}%</span> - R$ {p["precoDesconto"]}</div>'
    
    html += "</body></html>"
    
    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = EMAIL_DESTINATARIO
    msg['Subject'] = f"Ofertas iFood - {len(todos_produtos)} mercados"
    
    msg.attach(MIMEText(html, 'html', 'utf-8'))
    
    try:
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(EMAIL_REMETENTE, EMAIL_SENHA)
        servidor.send_message(msg)
        servidor.quit()
        print("\n✅ Email enviado com sucesso!")
    except Exception as e:
        print(f"\n❌ Erro ao enviar email: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scraper.py [login|scrape] \"mercado1\" \"mercado2\" ...")
        print("  login - Faz login")
        print("  scrape - Busca ofertas em um ou mais mercados")
        sys.exit(1)
    
    comando = sys.argv[1]
    
    if comando == "login":
        do_login()
    elif comando == "scrape":
        if len(sys.argv) < 3:
            print("❌ Erro: Nome do mercado obrigatório para scrape")
            print("Exemplo: python scraper.py scrape \"extra bernardino\" \"daki mercado\"")
            sys.exit(1)
        
        mercados = sys.argv[2:]
        todos_produtos = {}
        
        print(f"🛒 Processando {len(mercados)} mercado(s)...")
        
        for i, mercado_nome in enumerate(mercados, 1):
            if i > 1:
                print(f"\n⏳ Aguardando x segundos antes do próximo mercado...")
                time.sleep(8)

            print(f"\n[{i}/{len(mercados)}] {mercado_nome}")
            produtos = scrape_ofertas(mercado_nome)
            todos_produtos[mercado_nome] = produtos

        enviar_email(todos_produtos)
    else:
        print("Comando inválido. Use 'login' ou 'scrape'")