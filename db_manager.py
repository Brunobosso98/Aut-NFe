import sqlite3
import os
import logging
import datetime

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseManager:
    def __init__(self, db_name='xml_database.db'):
        self.db_name = db_name
        logging.info(f"🔄 Inicializando gerenciador de banco de dados: {db_name}")
        self.init_database()

    def init_database(self):
        """Initialize the database and create necessary tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS xml_hashes (
                        hash TEXT PRIMARY KEY,
                        cnpj TEXT,
                        numero_nota TEXT,
                        data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                logging.info(f"✅ Banco de dados inicializado com sucesso: {self.db_name}")
                # Verificar se a tabela já tem registros
                cursor.execute("SELECT COUNT(*) FROM xml_hashes")
                count = cursor.fetchone()[0]
                logging.info(f"📊 Total de registros no banco: {count}")
                return True
        except sqlite3.Error as e:
            logging.error(f"❌ Erro ao inicializar banco de dados: {e}")
            print(f"❌ Erro ao inicializar banco de dados: {e}")
            return False

    def verificar_xml_existente(self, xml_hash):
        """Verifica se um XML já foi baixado anteriormente pelo hash."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT hash FROM xml_hashes WHERE hash = ?", (str(xml_hash),))
                resultado = cursor.fetchone() is not None
                return resultado
        except sqlite3.Error as e:
            logging.error(f"❌ Erro ao verificar XML existente: {e}")
            print(f"❌ Erro ao verificar XML existente: {e}")
            return False
            
    def verificar_nota_existente(self, cnpj, numero_nota):
        """Verifica se uma nota com o mesmo CNPJ e número já foi baixada anteriormente."""
        if not numero_nota:  # Se o número da nota for None ou vazio
            logging.info(f"⚠️ Verificação ignorada: número da nota não fornecido para CNPJ {cnpj}")
            return False
        
        try:    
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT hash FROM xml_hashes WHERE cnpj = ? AND numero_nota = ?", (cnpj, numero_nota))
                resultado = cursor.fetchone() is not None
                return resultado
        except sqlite3.Error as e:
            logging.error(f"❌ Erro ao verificar nota existente: {e}")
            print(f"❌ Erro ao verificar nota existente: {e}")
            return False

    def registrar_xml(self, xml_hash, cnpj, numero_nota=None):
        """Registra um novo XML no banco de dados."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO xml_hashes (hash, cnpj, numero_nota) VALUES (?, ?, ?)",
                    (str(xml_hash), cnpj, numero_nota)
                )
                conn.commit()
                logging.info(f"✅ XML registrado com sucesso: CNPJ {cnpj}, Nota {numero_nota or 'N/A'}")
                return True
        except sqlite3.IntegrityError:
            logging.warning(f"⚠️ Tentativa de registrar XML duplicado: CNPJ {cnpj}, Nota {numero_nota or 'N/A'}")
            return False
        except Exception as e:
            logging.error(f"❌ Erro ao registrar XML no banco de dados: {e}")
            print(f"❌ Erro ao registrar XML no banco de dados: {e}")
            return False

    def limpar_registros_antigos(self, dias=90):
        """Remove registros mais antigos que o número especificado de dias."""
        try:
            data_limite = datetime.datetime.now() - datetime.timedelta(days=dias)
            data_formatada = data_limite.strftime("%Y-%m-%d")
            
            with sqlite3.connect(self.db_name) as conn:
                # Primeiro, contar quantos registros serão afetados
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM xml_hashes 
                    WHERE data_processamento < datetime('now', '-' || ? || ' days')
                """, (dias,))
                total_registros = cursor.fetchone()[0]
                
                # Agora executar a exclusão
                cursor.execute("""
                    DELETE FROM xml_hashes 
                    WHERE data_processamento < datetime('now', '-' || ? || ' days')
                """, (dias,))
                registros_removidos = cursor.rowcount
                conn.commit()
                
                mensagem = f"✅ {registros_removidos} registros anteriores a {data_formatada} foram removidos do banco de dados."
                logging.info(mensagem)
                print(mensagem)
                
                # Contar quantos registros restaram
                cursor.execute("SELECT COUNT(*) FROM xml_hashes")
                registros_restantes = cursor.fetchone()[0]
                logging.info(f"📊 Total de registros restantes no banco: {registros_restantes}")
                
                return registros_removidos
        except Exception as e:
            erro_msg = f"❌ Erro ao limpar registros antigos: {e}"
            logging.error(erro_msg)
            print(erro_msg)
            return 0