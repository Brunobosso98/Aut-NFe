import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_name='xml_database.db'):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        """Initialize the database and create necessary tables if they don't exist."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS xml_hashes (
                    hash TEXT PRIMARY KEY,
                    cnpj TEXT,
                    data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def verificar_xml_existente(self, xml_hash):
        """Verifica se um XML já foi baixado anteriormente."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT hash FROM xml_hashes WHERE hash = ?", (str(xml_hash),))
            return cursor.fetchone() is not None

    def registrar_xml(self, xml_hash, cnpj):
        """Registra um novo XML no banco de dados."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO xml_hashes (hash, cnpj) VALUES (?, ?)",
                    (str(xml_hash), cnpj)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            # Hash já existe no banco
            return False
        except Exception as e:
            print(f"❌ Erro ao registrar XML no banco de dados: {e}")
            return False

    def limpar_registros_antigos(self, dias=90):
        """Remove registros mais antigos que o número especificado de dias."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM xml_hashes 
                    WHERE data_processamento < datetime('now', '-' || ? || ' days')
                """, (dias,))
                registros_removidos = cursor.rowcount
                conn.commit()
                print(f"✅ {registros_removidos} registros antigos foram removidos do banco de dados.")
                return registros_removidos
        except Exception as e:
            print(f"❌ Erro ao limpar registros antigos: {e}")
            return 0