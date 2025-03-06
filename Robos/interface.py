import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTextEdit, QDateEdit, QMessageBox, QScrollArea)
from PyQt5.QtCore import Qt, QDate
from datetime import datetime, timedelta
import requests
import json
import base64
import xml.etree.ElementTree as ET
import time
import pandas as pd
from db_manager import DatabaseManager

# Configurações da API
API_KEY = ""
URL = f"https://api.sieg.com/BaixarXmlsV2?api_key=7dJmT%2f0uVPbX8mEdBrZSdw%3d%3d"
XML_BASE_DIR = rf"\\192.168.1.240\Escritório Digital\Robos\NFE"  # Pasta raiz onde os XMLs serão armazenados

# Dicionário de meses para organização das pastas
MESES = {
    "01": "Janeiro", "02": "Fevereiro", "03": "Marco", "04": "Abril",
    "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
    "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro"
}

class XMLProcessorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.db.limpar_registros_antigos(90)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Processador de XMLs SIEG')
        self.setGeometry(100, 100, 800, 600)

        # Widget central e layout principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Área de entrada de CNPJs
        cnpj_label = QLabel('CNPJs (um por linha):')
        layout.addWidget(cnpj_label)
        self.cnpj_input = QTextEdit()
        self.cnpj_input.setPlaceholderText('Digite os CNPJs aqui, um por linha')
        layout.addWidget(self.cnpj_input)

        # Área de seleção de datas
        date_widget = QWidget()
        date_layout = QHBoxLayout(date_widget)

        # Data inicial
        start_date_label = QLabel('Data Inicial:')
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())

        # Data final
        end_date_label = QLabel('Data Final:')
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())

        date_layout.addWidget(start_date_label)
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(end_date_label)
        date_layout.addWidget(self.end_date)
        layout.addWidget(date_widget)

        # Botão para carregar CNPJs do Excel
        self.load_excel_button = QPushButton('Carregar CNPJs do Excel')
        self.load_excel_button.clicked.connect(self.load_cnpjs_from_excel)
        layout.addWidget(self.load_excel_button)

        # Botão para definir últimos 5 dias
        self.last_5_days_button = QPushButton('Definir Últimos 5 Dias')
        self.last_5_days_button.clicked.connect(self.set_last_5_days)
        layout.addWidget(self.last_5_days_button)

        # Botão de processamento
        self.process_button = QPushButton('Processar XMLs')
        self.process_button.clicked.connect(self.process_cnpjs)
        layout.addWidget(self.process_button)

        # Área de log
        log_label = QLabel('Log de Processamento:')
        layout.addWidget(log_label)

        # Criar uma área de rolagem para o log
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.log_layout = QVBoxLayout(scroll_content)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_layout.addWidget(self.log_text)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def log_message(self, message):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        QApplication.processEvents()

    def validate_cnpj(self, cnpj):
        # Remove caracteres não numéricos
        cnpj = ''.join(filter(str.isdigit, cnpj))
        return len(cnpj) == 14

    def process_cnpjs(self):
        # Limpar a área de log
        self.log_text.clear()

        # Obter e validar CNPJs
        cnpjs_text = self.cnpj_input.toPlainText().strip()
        if not cnpjs_text:
            QMessageBox.warning(self, 'Erro', 'Por favor, insira pelo menos um CNPJ.')
            return

        cnpjs = [cnpj.strip() for cnpj in cnpjs_text.split('\n') if cnpj.strip()]
        valid_cnpjs = []

        for cnpj in cnpjs:
            if self.validate_cnpj(cnpj):
                valid_cnpjs.append(''.join(filter(str.isdigit, cnpj)))
            else:
                self.log_message(f"⚠️ CNPJ inválido ignorado: {cnpj}")

        if not valid_cnpjs:
            QMessageBox.warning(self, 'Erro', 'Nenhum CNPJ válido encontrado.')
            return

        # Obter datas
        start_date = self.start_date.date().toPyDate()
        end_date = self.end_date.date().toPyDate()

        if start_date > end_date:
            QMessageBox.warning(self, 'Erro', 'A data inicial deve ser anterior ou igual à data final.')
            return

        # Desabilitar botão durante o processamento
        self.process_button.setEnabled(False)

        try:
            self.log_message(f"📋 Processando {len(valid_cnpjs)} CNPJs...")

            for cnpj in valid_cnpjs:
                self.log_message(f"\n🔄 Processando CNPJ: {cnpj}")
                self.process_single_cnpj(cnpj, start_date, end_date)

            self.log_message("\n✅ Processamento concluído!")

        except Exception as e:
            self.log_message(f"\n❌ Erro durante o processamento: {str(e)}")

        finally:
            # Reabilitar botão após o processamento
            self.process_button.setEnabled(True)

    def process_single_cnpj(self, cnpj, start_date, end_date):
        current_date = start_date
        while current_date <= end_date:
            data_str = current_date.strftime("%Y-%m-%d")
            self.log_message(f"📅 Buscando notas para CNPJ {cnpj} na data {data_str}")

            skip = 0
            tem_mais_xmls = True

            while tem_mais_xmls:
                response = self.fazer_requisicao_api(cnpj, data_str, skip)

                if response is None:
                    tem_mais_xmls = False
                    continue

                if response.status_code == 200:
                    try:
                        data = response.json()
                        self.log_message(f"🔹 Processando resposta para CNPJ {cnpj} do dia {data_str} (Skip: {skip})")

                        if "xmls" in data and isinstance(data["xmls"], list) and len(data["xmls"]) > 0:
                            novos_arquivos = 0
                            for i, xml_base64 in enumerate(data["xmls"], 1):
                                xml_hash = hash(xml_base64)
                                if self.db.verificar_xml_existente(xml_hash):
                                    self.log_message(f"⚠️ XML {i} já foi baixado anteriormente. Pulando...")
                                    continue

                                xml_content = base64.b64decode(xml_base64).decode("utf-8")
                                dados_xml = self.extrair_dados_xml(xml_content)

                                if dados_xml:
                                    file_name = self.salvar_xml(xml_content, dados_xml, i)
                                    if file_name:
                                        if self.db.registrar_xml(xml_hash, cnpj):
                                            novos_arquivos += 1
                                            self.log_message(f"✅ XML {i} salvo em: {file_name}")

                            if len(data["xmls"]) == 50:
                                skip += 50
                                time.sleep(2)
                            else:
                                tem_mais_xmls = False

                            if novos_arquivos == 0:
                                self.log_message(f"⚠️ Nenhum novo XML encontrado para CNPJ {cnpj} no dia {data_str}.")
                        else:
                            self.log_message(f"⚠️ Nenhum XML retornado pela API para CNPJ {cnpj} no dia {data_str}.")
                            tem_mais_xmls = False

                    except json.JSONDecodeError:
                        self.log_message("❌ Erro ao decodificar a resposta JSON.")
                        tem_mais_xmls = False
                else:
                    self.log_message(f"❌ Erro na requisição: {response.status_code} - {response.text}")
                    tem_mais_xmls = False

                time.sleep(2)

            current_date = current_date + timedelta(days=1)

    def fazer_requisicao_api(self, cnpj, data_str, skip=0, max_retries=5, retry_delay=5):
        headers = {"Content-Type": "application/json"}
        payload = {
            "XmlType": 1,
            "Take": 50,
            "Skip": skip,
            "DataEmissaoInicio": data_str,
            "DataEmissaoFim": data_str,
            "CnpjEmit": cnpj,
            "Downloadevent": False
        }

        for attempt in range(max_retries):
            try:
                response = requests.post(URL, headers=headers, json=payload)

                if response.status_code == 404:
                    try:
                        error_message = response.json()
                        if isinstance(error_message, list) and len(error_message) > 0 and "Nenhum arquivo XML localizado" in error_message[0]:
                            return response
                    except:
                        pass

                if response.status_code == 200:
                    return response

                self.log_message(f"⚠️ Tentativa {attempt + 1} de {max_retries} falhou. Código: {response.status_code}")

                if attempt < max_retries - 1:
                    self.log_message(f"🔄 Aguardando {retry_delay} segundos antes de tentar novamente...")
                    time.sleep(retry_delay)
                    continue
                else:
                    self.log_message(f"❌ Todas as tentativas falharam para CNPJ {cnpj} na data {data_str}. Continuando com o próximo...")
                    return None

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    self.log_message(f"⚠️ Erro de conexão na tentativa {attempt + 1} de {max_retries}: {str(e)}")
                    self.log_message(f"🔄 Aguardando {retry_delay} segundos antes de tentar novamente...")
                    time.sleep(retry_delay)
                    continue
                else:
                    self.log_message(f"❌ Todas as tentativas falharam para CNPJ {cnpj} na data {data_str}. Continuando com o próximo...")
                    return None

        return None

    def extrair_dados_xml(self, xml_content):
        try:
            root = ET.fromstring(xml_content)
            ns = {"ns": "http://www.portalfiscal.inf.br/nfe"}

            dhEmi = root.find(".//ns:dhEmi", ns)
            data_emissao = dhEmi.text[:10] if dhEmi is not None else "0000-00-00"
            ano, mes, _ = data_emissao.split("-")

            cnpj_emit = root.find(".//ns:emit/ns:CNPJ", ns)
            cnpj_emit = cnpj_emit.text if cnpj_emit is not None else "00000000000000"

            nNF = root.find(".//ns:nNF", ns)
            numero_nota = nNF.text if nNF is not None else None

            tpNF = root.find(".//ns:tpNF", ns)
            tipo_nota = "entrada" if tpNF is not None and tpNF.text == "0" else "saida"

            return {
                "ano": ano,
                "mes": mes,
                "cnpj_emit": cnpj_emit,
                "numero_nota": numero_nota,
                "tipo_nota": tipo_nota
            }
        except Exception as e:
            self.log_message(f"❌ Erro ao extrair dados do XML: {e}")
            return None

    def salvar_xml(self, xml_content, dados_xml, i):
        try:
            mes_nome = MESES.get(dados_xml["mes"], dados_xml["mes"])
            dir_path = os.path.join(XML_BASE_DIR, dados_xml["tipo_nota"], dados_xml["ano"], mes_nome, dados_xml["cnpj_emit"])
            os.makedirs(dir_path, exist_ok=True)

            numero_nota = dados_xml["numero_nota"] or f"{i}"
            file_name = os.path.join(dir_path, f"{numero_nota}.xml")

            with open(file_name, "w", encoding="utf-8") as file:
                file.write(xml_content)

            return file_name
        except Exception as e:
            self.log_message(f"❌ Erro ao salvar XML: {e}")
            return None

    def load_cnpjs_from_excel(self):
        try:
            df = pd.read_excel('cnpj.xlsx')
            cnpjs = df['CNPJ'].astype(str).str.replace(r'\D', '', regex=True).tolist()
            valid_cnpjs = [cnpj for cnpj in cnpjs if len(cnpj) == 14]
            
            if valid_cnpjs:
                self.cnpj_input.clear()
                self.cnpj_input.setPlainText('\n'.join(valid_cnpjs))
                self.log_message(f"✅ {len(valid_cnpjs)} CNPJs carregados do Excel com sucesso!")
            else:
                QMessageBox.warning(self, 'Erro', 'Nenhum CNPJ válido encontrado no arquivo Excel.')
                
        except Exception as e:
            QMessageBox.warning(self, 'Erro', f'Erro ao ler arquivo Excel: {str(e)}')

    def set_last_5_days(self):
        today = QDate.currentDate()
        five_days_ago = today.addDays(-5)
        
        self.start_date.setDate(five_days_ago)
        self.end_date.setDate(today)
        self.log_message("✅ Período definido para os últimos 5 dias.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = XMLProcessorGUI()
    window.show()
    sys.exit(app.exec_())
