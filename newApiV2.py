import requests
import json
import base64
import os
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime, timedelta
import time

# Configurações da API
API_KEY = f""
URL = f"https://api.sieg.com/BaixarXmlsV2?api_key="
LOG_FILE = "xml_baixados.txt"  # Arquivo para registrar os XMLs já baixados
XML_BASE_DIR = "xml_arquivos"  # Pasta raiz onde os XMLs serão armazenados

# Dicionário de meses para organização das pastas
MESES = {
    "01": "Janeiro", "02": "Fevereiro", "03": "Marco", "04": "Abril",
    "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
    "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro"
}

def carregar_xmls_baixados():
    """Carrega a lista de XMLs já baixados do arquivo de log."""
    baixados = set()
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as log:
            baixados = set(log.read().splitlines())
    return baixados

def fazer_requisicao_api(cnpj, data_str):
    """Faz uma requisição à API do SIEG para obter os XMLs."""
    headers = {"Content-Type": "application/json"}
    payload = {
        "XmlType": 1,  # 1 = NFe
        "Take": 50,  # Máximo 50 XMLs por requisição
        "Skip": 0,
        "DataEmissaoInicio": data_str,
        "DataEmissaoFim": data_str,
        "CnpjEmit": cnpj,
        "Downloadevent": False
    }
    return requests.post(URL, headers=headers, json=payload)

def extrair_dados_xml(xml_content):
    """Extrai informações relevantes do XML da nota fiscal."""
    try:
        root = ET.fromstring(xml_content)
        ns = {"ns": "http://www.portalfiscal.inf.br/nfe"}

        # Extrai data de emissão
        dhEmi = root.find(".//ns:dhEmi", ns)
        data_emissao = dhEmi.text[:10] if dhEmi is not None else "0000-00-00"
        ano, mes, _ = data_emissao.split("-")

        # Extrai CNPJ do emitente
        cnpj_emit = root.find(".//ns:emit/ns:CNPJ", ns)
        cnpj_emit = cnpj_emit.text if cnpj_emit is not None else "00000000000000"

        # Extrai número da nota
        nNF = root.find(".//ns:nNF", ns)
        numero_nota = nNF.text if nNF is not None else None

        return {
            "ano": ano,
            "mes": mes,
            "cnpj_emit": cnpj_emit,
            "numero_nota": numero_nota
        }
    except Exception as e:
        print(f"❌ Erro ao extrair dados do XML: {e}")
        return None

def salvar_xml(xml_content, dados_xml, i):
    """Salva o XML em disco na estrutura de pastas adequada."""
    try:
        mes_nome = MESES.get(dados_xml["mes"], dados_xml["mes"])
        dir_path = os.path.join(XML_BASE_DIR, dados_xml["ano"], mes_nome, dados_xml["cnpj_emit"])
        os.makedirs(dir_path, exist_ok=True)

        numero_nota = dados_xml["numero_nota"] or f"{i}"
        file_name = os.path.join(dir_path, f"{numero_nota}.xml")
        
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(xml_content)
        
        return file_name
    except Exception as e:
        print(f"❌ Erro ao salvar XML: {e}")
        return None

def processar_xml_por_cnpj(cnpj):
    """Processa XMLs de notas fiscais para um CNPJ específico."""
    hoje = datetime.today().date()
    baixados = carregar_xmls_baixados()
    
    # Loop para os últimos 5 dias
    for dias_atras in range(5, 0, -1):
        data_consulta = hoje - timedelta(days=dias_atras)
        data_str = data_consulta.strftime("%Y-%m-%d")
        
        print(f"📅 Buscando notas para CNPJ {cnpj} na data {data_str}")
        
        # Faz requisição à API
        response = fazer_requisicao_api(cnpj, data_str)
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"🔹 Processando resposta para CNPJ {cnpj} do dia {data_str}")

                if "xmls" in data and isinstance(data["xmls"], list) and len(data["xmls"]) > 0:
                    novos_arquivos = 0
                    with open(LOG_FILE, "a", encoding="utf-8") as log:
                        for i, xml_base64 in enumerate(data["xmls"], 1):
                            # Verifica se o XML já foi baixado
                            xml_hash = hash(xml_base64)
                            if str(xml_hash) in baixados:
                                print(f"⚠️ XML {i} já foi baixado anteriormente. Pulando...")
                                continue

                            # Decodifica e processa o XML
                            xml_content = base64.b64decode(xml_base64).decode("utf-8")
                            dados_xml = extrair_dados_xml(xml_content)
                            
                            if dados_xml:
                                file_name = salvar_xml(xml_content, dados_xml, i)
                                if file_name:
                                    log.write(f"{xml_hash}\n")
                                    novos_arquivos += 1
                                    print(f"✅ XML {i} salvo em: {file_name}")

                    if novos_arquivos == 0:
                        print(f"⚠️ Nenhum novo XML encontrado para CNPJ {cnpj} no dia {data_str}.")
                else:
                    print(f"⚠️ Nenhum XML retornado pela API para CNPJ {cnpj} no dia {data_str}.")

            except json.JSONDecodeError:
                print("❌ Erro ao decodificar a resposta JSON.")
        else:
            print(f"❌ Erro na requisição: {response.status_code} - {response.text}")
        
        # Aguarda entre requisições para respeitar limite da API
        time.sleep(2)

def processar_lista_cnpjs():
    """Processa a lista de CNPJs do arquivo Excel."""
    try:
        df = pd.read_excel('cnpj.xlsx')
        cnpjs = df['CNPJ'].astype(str).str.replace(r'\D', '', regex=True).tolist()
        
        print(f"📋 Processando {len(cnpjs)} CNPJs encontrados no arquivo.")
        
        for cnpj in cnpjs:
            if len(cnpj) == 14:  # Validação básica do CNPJ
                print(f"\n🔄 Processando CNPJ: {cnpj}")
                processar_xml_por_cnpj(cnpj)
            else:
                print(f"⚠️ CNPJ inválido ignorado: {cnpj}")
                
    except Exception as e:
        print(f"❌ Erro ao ler arquivo de CNPJs: {e}")

# Executa o processamento principal
if __name__ == "__main__":
    processar_lista_cnpjs()