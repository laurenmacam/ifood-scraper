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


EMAIL_SENDER = "lauren@dpaplus.com"
EMAIL_PASSWORD = "svhdnjzithvgbdkh"
EMAIL_RECEIVER = "laurencampregher@gmail.com"
PHONE = "13996110880"
ADDRESS = "Pasteur"


def human_delay(min_sec=1, max_sec=3):
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
        page.fill("input[name='phone']", PHONE)
        
        print("3 Clicando em WhatsApp...")
        page.wait_for_selector("button:has-text('WhatsApp'):not([disabled])", state="visible")
        page.click("button:has-text('WhatsApp')")
        
        print("📱 Complete o login (código + email)...")
        page.pause()
        
        print("Aguardando modal de endereços...")
        page.wait_for_selector(f"text={ADDRESS}", state="visible")
        
        print(f"Selecionando endereço '{ADDRESS}'...")
        page.locator(f".btn-address__container:has-text('{ADDRESS}')").first.click()
        
        print("Aguardando página carregar...")
        page.wait_for_load_state("domcontentloaded")
        
        print("Salvando sessão COM login completo...")
        page.context.storage_state(path="ifood_session.json")
        print("✅ Sessão salva!")
        
        browser.close()


def color_discount(discount):
    bold = "\033[1m"
    reset = "\033[0m"
    
    if 24 <= discount < 33:
        return f"{bold}\033[38;5;208m{discount}%{reset}"
    elif 33 <= discount <= 40:
        return f"{bold}\033[31m{discount}%{reset}"
    elif discount > 40:
        return f"{bold}\033[35m{discount}%{reset}"
    else:
        return f"{discount}%"


def scrape_offers(page, store_name):
    print("Busca mercado...")
    page.fill("input[data-test-id='search-input-field']", store_name)
    human_delay(1, 2)
    page.press("input[data-test-id='search-input-field']", "Enter")
    human_delay(2, 4)

    print("Esperando resultados da busca...")
    page.wait_for_selector(".merchant-list-v2__item-wrapper")

    human_delay(1, 2)

    print("Clicando no primeiro resultado...")
    page.locator(".merchant-v2__link").first.click()

    print("Esperando produtos carregarem...")
    page.wait_for_selector(".product-card-wrapper", state="visible")

    print("Coletando categorias...")
    categories = page.locator(".aisle-menu__item__link__name").all()

    categories_list = []
    for i, cat in enumerate(categories):
        category_name = cat.inner_text()
        if i > 0:
            categories_list.append(category_name)

    print(f"Encontradas {len(categories_list)} categorias:")

    market_products = []

    for category in categories_list:
        print(f"\nProcessando categoria: {category}")
        
        try:
            page.click(f".aisle-menu__item__link__name:has-text('{category}')", timeout=10000)
            page.wait_for_selector(".product-card-wrapper", state="visible", timeout=10000)
        except Exception:
            print(f"  ⚠️ Categoria '{category}' sem produtos ou timeout. Pulando...")
            continue
        
        print("Carregando todos os produtos...")
        previous_products_count = 0
        while True:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            
            current_products_count = page.locator(".product-card-wrapper").count()
            
            if current_products_count == previous_products_count:
                break
            
            previous_products_count = current_products_count
            print(f"  Carregados {current_products_count} produtos...")
        
        print(f"Total: {current_products_count} produtos. Coletando descontos...")
        
        discounted_products = page.evaluate("""
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

        market_products.extend(discounted_products)
        
        print(f"  Encontrados {len(discounted_products)} produtos com desconto >= 24%")
        for p in discounted_products:
            print(f"    - {p['nome']} ({color_discount(p['desconto'])}) - R$ {p['precoDesconto']}")


        
    # page.pause()

    # browser.close()

    print("Voltando para lista de mercados...")
    page.goto("https://www.ifood.com.br/mercados")
    human_delay(2, 3)

    return market_products


def send_email(all_products):
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
    
    for store, store_products in all_products.items():
        html += f"<h2>🏪 {store.upper()}</h2>"
        
        if not store_products:
            html += "<p>Nenhum produto encontrado</p>"
        else:
            for p in store_products:
                discount_percentage = p['desconto']
                
                if 24 <= discount_percentage < 33:
                    cor_class = "desconto-laranja"
                elif 33 <= discount_percentage <= 40:
                    cor_class = "desconto-vermelho"
                else:
                    cor_class = "desconto-roxo"
                
                html += f'<div class="produto">- {p["nome"]} <span class="{cor_class}">{discount_percentage}%</span> - R$ {p["precoDesconto"]}</div>'
    
    html += "</body></html>"
    
    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"Ofertas iFood - {len(all_products)} mercados"
    
    msg.attach(MIMEText(html, 'html', 'utf-8'))
    
    try:
        smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
        smtp_server.starttls()
        smtp_server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp_server.send_message(msg)
        smtp_server.quit()
        print("\n✅ Email enviado com sucesso!")
    except Exception as e:
        print(f"\n❌ Erro ao enviar email: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scraper.py [login|scrape] \"mercado1\" \"mercado2\" ...")
        print("  login - Faz login")
        print("  scrape - Busca ofertas em um ou mais mercados")
        sys.exit(1)
    
    action_command = sys.argv[1]
    
    if action_command == "login":
        do_login()
    elif action_command == "scrape":
        if len(sys.argv) < 3:
            print("❌ Erro: Nome do mercado obrigatório")
            sys.exit(1)
        
        stores = sys.argv[2:]
        all_products = {}
        
        print(f"🛒 Processando {len(stores)} mercado(s)...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                slow_mo=random.randint(200, 500),
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = browser.new_context(
                storage_state="ifood_session.json",
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='pt-BR',
                timezone_id='America/Sao_Paulo'
            )
            
            page = context.new_page()
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en']});
            """)
            
            
            
            # Loop pelos mercados
            for i, store_name in enumerate(stores, 1):
                page.goto("https://www.ifood.com.br/restaurantes")
                human_delay(3, 5)

                print(f"\n{'='*60}")
                print(f"[{i}/{len(stores)}] {store_name}")
                print('='*60)
                
                # Seleciona endereço
                if i == 1:
                    page.wait_for_selector(".address-modal-overlay--after-open", state="visible")
                    page.locator(f".btn-address__container:has-text('{ADDRESS}')").first.click()
                    page.wait_for_selector(".address-modal-overlay", state="hidden", timeout=5000)
                else:
                    human_delay(5, 8)
                
                # Scrape o mercado
                products = scrape_offers(page, store_name)
                all_products[store_name] = products
            
            # browser.close()
        
        send_email(all_products)
    else:
        print("Comando inválido. Use 'login' ou 'scrape'")