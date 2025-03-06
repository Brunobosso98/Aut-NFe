import requests
import json
import sys
import base64
import os
import openpyxl
import openpyxl
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime, timedelta
import time
from db_manager import DatabaseManager

# Configurações da API
API_KEY = ""
URL = f"https://api.sieg.com/BaixarXmlsV2?api_key=7dJmT%2f0uVPbX8mEdBrZSdw%3d%3d"

# Configurações de documentos
DOC_TYPES = {
    1: {  # NFSe
        "base_dir": rf"\\192.168.1.240\Fiscal\Nota fiscal Eletronica\SIEG\NFE",
        "namespace": "http://www.portalfiscal.inf.br/nfe",
        "numero_tag": "nNF",
        "tipo_tag": "tpNF",
        "tipo_map": {"0": "entrada", "1": "saida"}
    },
    2: {  # CTe
        "base_dir": rf"\\192.168.1.240\Fiscal\Nota fiscal Eletronica\SIEG\CTE",
        "namespace": "http://www.portalfiscal.inf.br/cte",
        "numero_tag": "cCT",
        "tipo_tag": "tpCTe",
        "tipo_map": {"0": "entrada", "1": "saida"}
    }
}

# Dicionário de meses para organização das pastas
MESES = {
    "01": "Janeiro", "02": "Fevereiro", "03": "Marco", "04": "Abril",
    "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
    "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro"
}

# Inicializa o gerenciador do banco de dados
db = DatabaseManager()

def fazer_requisicao_api(cnpj, data_str, xml_type=1, skip=0, max_retries=5, retry_delay=5):
    """Faz uma requisição à API do SIEG para obter os XMLs com mecanismo de retry."""
    headers = {"Content-Type": "application/json"}
    payload = {
        "XmlType": xml_type,  # 1 = NFe, 2 = CTe
        "Take": 50,  # Máximo 50 XMLs por requisição
        "Skip": skip,
        "DataEmissaoInicio": data_str,
        "DataEmissaoFim": data_str,
        "CnpjEmit": cnpj,
        "Downloadevent": False
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(URL, headers=headers, json=payload)
            
            # Se a resposta for 404 com a mensagem específica de "Nenhum arquivo XML localizado",
            # retornamos imediatamente pois isso não é um erro da API
            if response.status_code == 404:
                try:
                    error_message = response.json()
                    if isinstance(error_message, list) and len(error_message) > 0 and "Nenhum arquivo XML localizado" in error_message[0]:
                        return response
                except:
                    pass
            
            # Se a resposta for bem-sucedida (200) ou for o caso específico de "não encontrado",
            # retornamos a resposta
            if response.status_code == 200:
                return response
                
            # Se chegamos aqui, é um erro real da API
            print(f"⚠️ Tentativa {attempt + 1} de {max_retries} falhou. Código: {response.status_code}")
            
            if attempt < max_retries - 1:  # Se não for a última tentativa
                print(f"🔄 Aguardando {retry_delay} segundos antes de tentar novamente...")
                time.sleep(retry_delay)
                continue
            elif attempt == max_retries - 1:  # Se for a última tentativa
                print(f"❌ Todas as tentativas falharam para CNPJ {cnpj} na data {data_str}. Continuando com o próximo...")
                return None  # Retorna None para indicar falha total
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:  # Se não for a última tentativa
                print(f"⚠️ Erro de conexão na tentativa {attempt + 1} de {max_retries}: {str(e)}")
                print(f"🔄 Aguardando {retry_delay} segundos antes de tentar novamente...")
                time.sleep(retry_delay)
                continue
            elif attempt == max_retries - 1:  # Se for a última tentativa
                print(f"❌ Todas as tentativas falharam para CNPJ {cnpj} na data {data_str}. Continuando com o próximo...")
                return None  # Retorna None para indicar falha total
    
    return None  # Garante que sempre retornamos None em caso de falha total

def extrair_dados_xml(xml_content, xml_type=1):
    """Extrai informações relevantes do XML da nota fiscal ou CTe."""
    try:
        root = ET.fromstring(xml_content)
        doc_config = DOC_TYPES[xml_type]
        ns = {"ns": doc_config["namespace"]}

        # Extrai data de emissão
        dhEmi = root.find(".//ns:dhEmi", ns)
        data_emissao = dhEmi.text[:10] if dhEmi is not None else "0000-00-00"
        ano, mes, _ = data_emissao.split("-")

        # Extrai CNPJ do emitente
        cnpj_emit = root.find(".//ns:emit/ns:CNPJ", ns)
        cnpj_emit = cnpj_emit.text if cnpj_emit is not None else "00000000000000"

        # Extrai número do documento
        num_doc = root.find(f".//ns:{doc_config['numero_tag']}", ns)
        numero_nota = num_doc.text if num_doc is not None else None

        # Extrai tipo do documento
        tp_doc = root.find(f".//ns:{doc_config['tipo_tag']}", ns)
        tipo_nota = doc_config['tipo_map'].get(tp_doc.text if tp_doc is not None else "1", "saida")

        return {
            "ano": ano,
            "mes": mes,
            "cnpj_emit": cnpj_emit,
            "numero_nota": numero_nota,
            "tipo_nota": tipo_nota,
            "xml_type": xml_type
        }
    except Exception as e:
        print(f"❌ Erro ao extrair dados do XML: {e}")
        return None

def salvar_xml(xml_content, dados_xml, i):
    """Salva o XML em disco na estrutura de pastas adequada."""
    try:
        doc_config = DOC_TYPES[dados_xml["xml_type"]]
        mes_nome = MESES.get(dados_xml["mes"], dados_xml["mes"])
        dir_path = os.path.join(doc_config["base_dir"], dados_xml["tipo_nota"], dados_xml["ano"], mes_nome, dados_xml["cnpj_emit"])
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
    """Processa XMLs de notas fiscais e CTes para um CNPJ específico."""
    hoje = datetime.today().date()
    
    # Loop para os últimos 5 dias
    for dias_atras in range(5, 0, -1):
        data_consulta = hoje - timedelta(days=dias_atras)
        data_str = data_consulta.strftime("%Y-%m-%d")
        
        # Processa ambos os tipos de documento
        for xml_type in [1, 2]:  # 1 = NFe, 2 = CTe
            doc_name = "NFe" if xml_type == 1 else "CTe"
            print(f"📅 Buscando {doc_name}s para CNPJ {cnpj} na data {data_str}")

            # Inicializa variáveis para paginação
            skip = 0
            tem_mais_xmls = True
            
            while tem_mais_xmls:
                # Faz requisição à API
                response = fazer_requisicao_api(cnpj, data_str, xml_type, skip)
                
                # Se a resposta for None, significa que todas as tentativas falharam
                if response is None:
                    tem_mais_xmls = False
                    continue
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"🔹 Processando resposta para CNPJ {cnpj} do dia {data_str} (Skip: {skip})")

                        if "xmls" in data and isinstance(data["xmls"], list) and len(data["xmls"]) > 0:
                            novos_arquivos = 0
                            for i, xml_base64 in enumerate(data["xmls"], 1):
                                # Verifica se o XML já foi baixado
                                xml_hash = hash(xml_base64)
                                if db.verificar_xml_existente(xml_hash):
                                    print(f"⚠️ XML {i} já foi baixado anteriormente. Pulando...")
                                    continue

                                # Decodifica e processa o XML
                                xml_content = base64.b64decode(xml_base64).decode("utf-8")
                                dados_xml = extrair_dados_xml(xml_content, xml_type)
                                
                                if dados_xml:
                                    file_name = salvar_xml(xml_content, dados_xml, i)
                                    if file_name:
                                        if db.registrar_xml(xml_hash, cnpj):
                                            novos_arquivos += 1
                                            print(f"✅ XML {i} salvo em: {file_name}")

                            # Verifica se há mais XMLs para buscar
                            if len(data["xmls"]) == 50:  # Se retornou o máximo de XMLs, provavelmente há mais
                                skip += 50  # Incrementa o skip para a próxima página
                                time.sleep(2)  # Aguarda entre requisições para respeitar limite da API
                            else:
                                tem_mais_xmls = False  # Se retornou menos que 50, não há mais XMLs

                            if novos_arquivos == 0:
                                print(f"⚠️ Nenhum novo XML encontrado para CNPJ {cnpj} no dia {data_str}.")
                        else:
                            print(f"⚠️ Nenhum XML retornado pela API para CNPJ {cnpj} no dia {data_str}.")
                            tem_mais_xmls = False

                    except json.JSONDecodeError:
                        print("❌ Erro ao decodificar a resposta JSON.")
                        tem_mais_xmls = False
                else:
                    print(f"❌ Erro na requisição: {response.status_code} - {response.text}")
                    tem_mais_xmls = False
                
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
    try:
        processar_lista_cnpjs()
        # Limpa registros mais antigos que 90 dias
        db.limpar_registros_antigos(90)
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        sys.exit(1)