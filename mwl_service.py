#!/usr/bin/env python3
# mwl_server_corrected.py
import logging
import logging.handlers
# Prefer cx_Oracle (mais compatível) e fallback para oracledb
try:
    import cx_Oracle as _dbmod
    ORACLE_DB_MODULE = _dbmod
    ORACLE_DRIVER_NAME = 'cx_Oracle'
except Exception:
    try:
        import oracledb as _dbmod
        ORACLE_DB_MODULE = _dbmod
        ORACLE_DRIVER_NAME = 'oracledb'
    except Exception:
        ORACLE_DB_MODULE = None
        ORACLE_DRIVER_NAME = None
import os
import unidecode
import sys
import atexit
import json

from logging.handlers import TimedRotatingFileHandler
from typing import List, Dict, Any, Tuple
from datetime import datetime
from pydicom.dataset import Dataset
from pydicom.uid import generate_uid
from pydicom.valuerep import PersonName
from pynetdicom import AE, evt, StoragePresentationContexts
from pynetdicom.sop_class import ModalityWorklistInformationFind

# --- LOCKFILE PARA EVITAR EXECUÇÃO DO CÓDIGO DUPLICADO ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCK_FILE = os.path.join(BASE_DIR, "mwl_server.lock")

def is_process_running(pid):
    """Verifica se um processo está realmente rodando"""
    import subprocess
    try:
        result = subprocess.run(
            ['tasklist', '/FI', f'PID eq {pid}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return f"{pid}" in result.stdout
    except Exception:
        return False

if os.path.exists(LOCK_FILE):
    try:
        with open(LOCK_FILE, "r") as f:
            old_pid = f.read().strip()
        
        # Se o arquivo de lock existe, verificar se o processo ainda está rodando
        if old_pid and old_pid.isdigit() and is_process_running(int(old_pid)):
            print(f"Servidor MWL já está em execução (PID {old_pid}). Abortando nova instância.")
            sys.exit(1)
        else:
            # Processo não está rodando, remover lock obsoleto
            print(f"Removendo lock obsoleto (PID {old_pid})...")
            os.remove(LOCK_FILE)
    except Exception as e:
        # Se houver erro ao ler o lock, remover e continuar
        print(f"Erro ao verificar lock: {e}. Limpando...")
        try:
            os.remove(LOCK_FILE)
        except:
            pass

with open(LOCK_FILE, "w") as f:
    f.write(str(os.getpid()))
    
def cleanup():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass

atexit.register(cleanup)

# --- CONFIGURAÇÃO DE LOGGING DETALHADO ---
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILENAME = os.path.join(LOG_DIR, "mwl_server.log")

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(name)s - %(module)s.%(funcName)s - %(message)s'
)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler - UM ARQUIVO POR DIA, mantém os últimos 5
file_handler = TimedRotatingFileHandler(
    filename=LOG_FILENAME,
    when="midnight",
    interval=1,
    backupCount=5,
    encoding='utf-8'
)

file_handler.suffix = "%Y-%m-%d"
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Log para pynetdicom
pynetdicom_logger = logging.getLogger('pynetdicom')
pynetdicom_logger.setLevel(logging.DEBUG)
# --- FIM DA CONFIGURAÇÃO DE LOGGING ---

# --- IMPORTAÇÃO DAS CONFIGURAÇÕES .JSON ---
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Erro ao carregar config.json: {e}")
        sys.exit(1)

# --- SETUP DE COMNFIGURAÇÔES ---
config = load_config()

# --- LANGUAGE / I18N ---
def _get_lang() -> str:
    # Env override takes precedence
    lang = os.environ.get('MWL_LANG')
    if lang:
        return lang[:2].lower()
    # Try config.ui.language or server.language
    try:
        ui_lang = (config.get('ui', {}) or {}).get('language')
        if ui_lang:
            return str(ui_lang)[:2].lower()
    except Exception:
        pass
    try:
        srv_lang = (config.get('server', {}) or {}).get('language')
        if srv_lang:
            return str(srv_lang)[:2].lower()
    except Exception:
        pass
    return 'pt'

LANG = _get_lang()

TR = {
    'db_connecting': {
        'pt': "Tentando conectar ao {db} DB...",
        'en': "Attempting to connect to {db} DB...",
    },
    'db_connected': {
        'pt': "Conexão com o {db} estabelecida com sucesso.",
        'en': "Connected to {db} successfully.",
    },
    'db_config_incomplete': {
        'pt': "Configuração de banco incompleta (user/dsn ausentes). Pulando conexão.",
        'en': "Database configuration incomplete (missing user/dsn). Skipping connection.",
    },
    'db_driver_missing': {
        'pt': "Driver {db} ausente. Instale o plugin correspondente no venv.",
        'en': "{db} driver missing. Install the corresponding plugin in the venv.",
    },
    'db_connect_error': {
        'pt': "Erro ao conectar ao banco ({db}): {err}",
        'en': "Error connecting to database ({db}): {err}",
    },
    'db_dsn_invalid': {
        'pt': "DSN inválido para {db}. Esperado IP:PORT/DB",
        'en': "Invalid DSN for {db}. Expected IP:PORT/DB",
    },
    'sql_exec_error': {
        'pt': "Erro ao executar a consulta SQL: {err}",
        'en': "Error executing SQL query: {err}",
    },
    'server_starting': {
        'pt': "Iniciando Servidor MWL DICOM em {host}:{port} com AE Title: {ae}",
        'en': "Starting MWL DICOM Server at {host}:{port} with AE Title: {ae}",
    },
    'server_started_banner': {
        'pt': "Servidor Worklist DICOM (SCP) iniciado em {host}:{port}",
        'en': "Worklist DICOM Server (SCP) started at {host}:{port}",
    },
    'server_started_ae': {
        'pt': "AE Title: {ae}",
        'en': "AE Title: {ae}",
    },
    'server_waiting': {
        'pt': "Aguardando conexões Worklist C-FIND do client...",
        'en': "Waiting for Worklist C-FIND connections from client...",
    },
    'no_items_found': {
        'pt': "Nenhum item encontrado no banco de dados para a Worklist.",
        'en': "No items found in database for Worklist.",
    },
    'db_type_not_supported': {
        'pt': "Tipo de banco não suportado: {db}",
        'en': "Unsupported database type: {db}",
    },
}

def t(key: str, **kwargs) -> str:
    table = TR.get(key, {})
    msg = table.get(LANG) or table.get('pt') or key
    try:
        return msg.format(**kwargs)
    except Exception:
        return msg

# --- SERVER CONFIG ---
SERVER_CFG = config.get("server", {})
MWL_AE_TITLE = SERVER_CFG.get("aet", "FMWL").encode()
MWL_HOST = SERVER_CFG.get("host", "localhost")
MWL_PORT = int(SERVER_CFG.get("port", 104))
CLIENT_AE_TITLE = SERVER_CFG.get("client_aet", "ANY").encode()

# --- DATABASE CONFIG ---
DB_CFG = config.get("database", {})
DB_TYPE = (DB_CFG.get("type") or "oracle").lower()
DB_USER = DB_CFG.get("user")
DB_PASSWORD = DB_CFG.get("password")
DB_DSN = DB_CFG.get("dsn")
SQL_QUERY = DB_CFG.get("query")



def _parse_dsn_ip_port_db(dsn_str: str, default_port: int) -> Tuple[str, int, str]:
    try:
        host_part, dbname = dsn_str.split('/', 1)
        if ':' in host_part:
            host, port = host_part.split(':', 1)
            return host.strip(), int(port), dbname.strip()
        return host_part.strip(), default_port, dbname.strip()
    except Exception:
        return None, None, None


def _translate_query_for_mysql(query: str) -> str:
    """Very small best-effort translation of common Oracle functions to MySQL equivalents."""
    if not query:
        return query
    q = query
    # TO_CHAR(date,'YYYYMMDD') -> DATE_FORMAT(date,'%Y%m%d')
    q = q.replace("TO_CHAR(", "to_char(")  # normalize
    q = q.replace("to_char(", "TO_CHAR(")
    q = q.replace("'YYYYMMDD'", "'%Y%m%d'")
    q = q.replace("'HH24MISS'", "'%H%i%s'")
    # Replace function calls: naive replacements for patterns in config
    q = q.replace("TO_CHAR(paciente.dt_nascimento, '%Y%m%d')", "DATE_FORMAT(paciente.dt_nascimento, '%Y%m%d')")
    q = q.replace("TO_CHAR(ped_rx.dt_pedido, '%Y%m%d')", "DATE_FORMAT(ped_rx.dt_pedido, '%Y%m%d')")
    q = q.replace("TO_CHAR(ped_rx.hr_pedido, '%H%i%s')", "DATE_FORMAT(ped_rx.hr_pedido, '%H%i%s')")
    q = q.replace("TO_CHAR(paciente.dt_nascimento, 'YYYYMMDD')", "DATE_FORMAT(paciente.dt_nascimento, '%Y%m%d')")
    q = q.replace("TO_CHAR(ped_rx.dt_pedido, 'YYYYMMDD')", "DATE_FORMAT(ped_rx.dt_pedido, '%Y%m%d')")
    q = q.replace("TO_CHAR(ped_rx.hr_pedido, 'HH24MISS')", "DATE_FORMAT(ped_rx.hr_pedido, '%H%i%s')")
    # Oracle DECODE -> CASE for the specific pattern present
    q = q.replace(
        "decode(atendime.tp_atendimento,'U', 'URGENCIA', 'I', 'INTERNACAO', 'A', 'AMBULATORIO')",
        "CASE WHEN atendime.tp_atendimento='U' THEN 'URGENCIA' WHEN atendime.tp_atendimento='I' THEN 'INTERNACAO' WHEN atendime.tp_atendimento='A' THEN 'AMBULATORIO' ELSE '' END"
    )
    return q


def _translate_query_for_postgres(query: str) -> str:
    # Basic translation: DECODE to CASE (specific pattern)
    if not query:
        return query
    q = query
    q = q.replace(
        "decode(atendime.tp_atendimento,'U', 'URGENCIA', 'I', 'INTERNACAO', 'A', 'AMBULATORIO')",
        "CASE WHEN atendime.tp_atendimento='U' THEN 'URGENCIA' WHEN atendime.tp_atendimento='I' THEN 'INTERNACAO' WHEN atendime.tp_atendimento='A' THEN 'AMBULATORIO' ELSE '' END"
    )
    return q


class WorklistProvider:
    """Flexible provider supporting Oracle, PostgreSQL, and MySQL based on config."""
    def __init__(self):
        self.conn = None
        self.db_type = DB_TYPE
        self.driver = None

    def connect(self) -> bool:
        try:
            if not DB_USER or not DB_DSN:
                logging.error(t('db_config_incomplete'))
                return False

            if self.db_type == 'oracle':
                # Tentando conectar a Oracle
                if ORACLE_DB_MODULE is None:
                    logging.error(t('db_driver_missing', db='Oracle'))
                    return False
                
                self.conn = ORACLE_DB_MODULE.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
                self.driver = 'oracle'
            # Conexão Oracle estabelecida
                return True

            if self.db_type in ('postgres', 'postgresql'):
                # Tentando conectar a PostgreSQL
                try:
                    import psycopg2
                except Exception as e:
                    logging.error(t('db_driver_missing', db='PostgreSQL') + f" {e}")
                    return False
                host, port, dbname = _parse_dsn_ip_port_db(DB_DSN, 5432)
                if not host:
                    logging.error(t('db_dsn_invalid', db='PostgreSQL'))
                    return False
                self.conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=DB_USER, password=DB_PASSWORD)
                self.driver = 'postgres'
            # Conexão PostgreSQL estabelecida
                return True

            if self.db_type == 'mysql':
                # Tentando conectar a MySQL
                try:
                    import pymysql
                except Exception as e:
                    logging.error(t('db_driver_missing', db='MySQL') + f" {e}")
                    return False
                host, port, dbname = _parse_dsn_ip_port_db(DB_DSN, 3306)
                if not host:
                    logging.error(t('db_dsn_invalid', db='MySQL'))
                    return False
                self.conn = pymysql.connect(host=host, port=port, user=DB_USER, password=DB_PASSWORD, database=dbname)
                self.driver = 'mysql'
            # Conexão MySQL estabelecida
                return True

            logging.error(t('db_type_not_supported', db=self.db_type))
            return False
        except Exception as e:
            logging.error(t('db_connect_error', db=self.db_type, err=e))
            return False

    def _effective_query(self) -> str:
        q = SQL_QUERY
        if self.db_type == 'mysql':
            if 'TO_CHAR' in (q or '').upper() or 'DECODE(' in (q or '').upper():
                logging.warning("Traduzindo SQL Oracle->MySQL para funções comuns (TO_CHAR, DECODE). Verifique resultados.")
            return _translate_query_for_mysql(q)
        if self.db_type in ('postgres', 'postgresql'):
            return _translate_query_for_postgres(q)
        return q

    def get_worklist_items(self) -> List[Dict[str, Any]]:
        if not self.conn and not self.connect():
            return []
        if not all([DB_USER, DB_PASSWORD, DB_DSN, SQL_QUERY]):
            logging.error("Configuração de banco incompleta no config.json")
            sys.exit(1)
        cursor = None
        try:
            cursor = self.conn.cursor()
            q = self._effective_query()
            cursor.execute(q)
            
            # Map columns by INDEX order (column names are ignored)
            # Expected column order from production query:
            # 1. nm_paciente, 2. cd_paciente, 3. nascimento, 4. tp_sexo, 5. exame_descricao,
            # 6. exame_id, 7. exame_data, 8. exame_hora, 9. medico_responsavel, 10. modalidade,
            # 11. prioridade, 12. tp_atendimento, 13. cd_atendimento, 14. unidade,
            # 15. procedure_code_value, 16. code_meaning, 17. code_scheme_designator
            
            col_names = [
                'nm_paciente', 'cd_paciente', 'nascimento', 'tp_sexo', 'exame_descricao',
                'exame_id', 'exame_data', 'exame_hora', 'medico_responsavel', 'modalidade',
                'prioridade', 'tp_atendimento', 'cd_atendimento', 'unidade',
                'procedure_code_value', 'code_meaning', 'code_scheme_designator'
            ]
            
            results = []
            for row in cursor:
                # Map positional values to column names
                row_dict = {}
                for i, col_name in enumerate(col_names):
                    if i < len(row):
                        row_dict[col_name] = row[i]
                    else:
                        row_dict[col_name] = None
                results.append(row_dict)
            
                # Consulta executada com sucesso
            return results
        except Exception as e:
            logging.error(t('sql_exec_error', err=e))
            return []
        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception:
                pass

# --- FUNCAO DE LIMPEZA DAS STRINGS

def sanitize_string(text):
    if text is None:
        return ""
    s = str(text).strip()
    s = unidecode.unidecode(s)
    s = " ".join(s.split())
    return s.upper()

# --- HANDLER DICOM MWL FIND (C-FIND SCP) ---
def handle_find_mwl(event, worklist_provider: WorklistProvider):
    # O 'identifier' contém os filtros DICOM enviados pelo cliente
    identifier = event.identifier

    # --- Extração de filtros simples ---
    patient_id_filter = identifier.get('PatientID', None)
    sex_filter = identifier.get('PatientSex', None)
    birth_date_filter = identifier.get('PatientBirthDate', None)
    modality_filter = identifier.get('Modality', None)
    accession_number_filter = identifier.get('AccessionNumber', None)
    scheduled_date_filter = identifier.get('ScheduledProcedureStepStartDate', None)
    scheduled_time_filter = identifier.get('ScheduledProcedureStepStartTime', None)

    def clean_filter(value):
        if value is None:
            return None
        v = str(value).strip()
        return None if not v or v == '*' else v

    patient_id_filter = clean_filter(patient_id_filter)
    sex_filter = clean_filter(sex_filter)
    birth_date_filter = clean_filter(birth_date_filter)
    modality_filter = clean_filter(modality_filter)
    accession_number_filter = clean_filter(accession_number_filter)
    scheduled_date_filter = clean_filter(scheduled_date_filter)
    scheduled_time_filter = clean_filter(scheduled_time_filter)

            # Consultando worklist do banco de dados
    worklist_rows = worklist_provider.get_worklist_items()

    if not worklist_rows:
        # Nenhum item encontrado na worklist
        yield (0x0000, None)
        return

    # --- Agrupa linhas por 'exame_id' (cd_ped_rx) para que cada pedido vire 1 único item MWL ---
    from collections import defaultdict
    grouped = defaultdict(list)
    for row in worklist_rows:
        key = str(row.get('exame_id', '')).strip()
        grouped[key].append(row)

    response_count = 0

    # Itera por cada pedido (agregado)
    for ped_id, itens in grouped.items():
        if not itens:
            continue
        # Usa a primeira linha como fonte para dados do nível raiz (Patient, Accession etc.)
        primeira = itens[0]

        # Aplicar filtros recebidos pelo client (todos os filtros têm que casar para enviar o pedido)
        db_patient_id = str(primeira.get('cd_paciente', '')).strip()
        db_sex = str(primeira.get('tp_sexo', '')).strip()
        db_birth_date = str(primeira.get('nascimento', '')).strip()
        db_modality = str(primeira.get('modalidade', '')).strip()
        db_accession_number = str(primeira.get('exame_id', '')).strip()
        db_scheduled_date = str(primeira.get('exame_data', '')).strip()
        db_scheduled_time = str(primeira.get('exame_hora', '')).strip()

        if patient_id_filter and db_patient_id != patient_id_filter:
            continue
        if sex_filter and db_sex.upper() != sex_filter.upper():
            continue
        if birth_date_filter and db_birth_date != birth_date_filter:
            continue
        if modality_filter and db_modality.upper() != modality_filter.upper():
            continue
        if accession_number_filter and db_accession_number != accession_number_filter:
            continue
        if scheduled_date_filter and db_scheduled_date != scheduled_date_filter:
            continue
        if scheduled_time_filter and db_scheduled_time != scheduled_time_filter:
            continue

        # Monta o Dataset MWL (1 item por PED_RX)
        ds = Dataset()

        # NÍVEL RAIZ
        pn = sanitize_string(primeira.get('nm_paciente', '')).replace(" ", "^")
        ds.PatientName = PersonName(pn if pn else "^")
        ds.PatientID = db_patient_id
        ds.PatientBirthDate = db_birth_date or ''
        ds.PatientSex = {'F': 'F', 'M': 'M'}.get(primeira.get('tp_sexo', 'O'), 'O')
        ds.AccessionNumber = db_accession_number
        ds.Modality = db_modality or 'CR'
        ds.RequestedProcedureDescription = sanitize_string(primeira.get('exame_descricao', ''))
        ds.SpecificCharacterSet = 'ISO_IR 192'
        ds.InstanceCreationDate = datetime.now().strftime('%Y%m%d')
        ds.InstanceCreationTime = datetime.now().strftime('%H%M%S')

        # Código(s) do procedimento - No nível raiz também (Prima exige)
        # Vamos montar uma lista única de códigos para colocar no RequestedProcedureCodeSequence do nível raiz.
        codes_seen = set()
        requested_proc_codes = []
        scheduled_protocol_codes = []

        for item in itens:
            code_value = str(item.get('procedure_code_value') or '').strip()
            code_scheme = str(item.get('code_scheme_designator') or '').strip()
            code_meaning = str(item.get('code_meaning') or sanitize_string(item.get('exame_descricao') or '')).strip()

            # Evita duplicar protocolos idênticos
            code_key = (code_value, code_scheme, code_meaning)
            if code_key in codes_seen:
                continue
            codes_seen.add(code_key)

            # Criar dataset de código para RequestedProcedureCodeSequence e ScheduledProtocolCodeSequence
            code_ds = Dataset()
            # Se code_value vier com prefixo como 'FCR0200-0001', mantemos. Caso precise cortar prefixo, faça aqui.
            code_ds.CodeValue = code_value
            code_ds.CodingSchemeDesignator = code_scheme if code_scheme else ''
            code_ds.CodeMeaning = code_meaning if code_meaning else ''
            requested_proc_codes.append(code_ds)

            # Para ScheduledProtocolCodeSequence (cada protocolo)
            prot_ds = Dataset()
            prot_ds.CodeValue = code_value
            prot_ds.CodingSchemeDesignator = code_scheme if code_scheme else ''
            prot_ds.CodeMeaning = code_meaning if code_meaning else ''
            scheduled_protocol_codes.append(prot_ds)

        # Atribui RequestedProcedureCodeSequence no nível raiz (se houver)
        if requested_proc_codes:
            ds.RequestedProcedureCodeSequence = requested_proc_codes

        # UIDs
        ds.StudyInstanceUID = generate_uid()
        ds.RequestedProcedureUID = generate_uid()
        ds.SOPInstanceUID = generate_uid()

        # Scheduled Procedure Step Sequence (obrigatório ter pelo menos 1 item)
        sps = Dataset()
        sps.Modality = db_modality or 'CR'
        sps.RequestedProcedureID = str(primeira.get('exame_id', '')).strip() or ped_id
        sps.ScheduledProcedureStepID = str(primeira.get('exame_id', '')).strip() or ped_id
        sps.ScheduledProcedureStepDescription = sanitize_string(primeira.get('exame_descricao', ''))
        sps.ScheduledProcedureStepStartDate = db_scheduled_date or ''
        sps.ScheduledProcedureStepStartTime = db_scheduled_time or ''
        sps.ScheduledProcedureStepUID = generate_uid()
        sps.ScheduledStationAETitle = CLIENT_AE_TITLE.decode()
        medico = sanitize_string(primeira.get('medico_responsavel', '')).replace(" ", "^")
        sps.ScheduledPerformingPhysicianName = PersonName(medico if medico else "^")

        # Adiciona todos os protocolos solicitados no SPS
        if scheduled_protocol_codes:
            sps.ScheduledProtocolCodeSequence = scheduled_protocol_codes

        # Também coloca o RequestedProcedureCodeSequence dentro do SPS (alguns consoles exigem)
        if requested_proc_codes:
            sps.RequestedProcedureCodeSequence = requested_proc_codes

        # Coloca a SPS na sequência do item
        ds.ScheduledProcedureStepSequence = [sps]

        # Extra: alguns consoles esperam que exista também RequestedProcedureID e RequestedProcedureDescription
        ds.RequestedProcedureID = str(primeira.get('exame_id', '')).strip() or ped_id
        #ds.RequestedProcedureDescription = sanitize_string(primeira.get('exame_descricao', ''))

        # Logging e yield
        response_count += 1
            # Processando item MWL
        yield (0xFF00, ds)

            # Retornando itens da worklist
    yield (0x0000, None)

# --- SETUP DO SERVIDOR DICOM AE ---
def run_mwl_scp():
    worklist_provider = WorklistProvider()
    if not worklist_provider.connect():
        logging.error("Falha ao conectar ao banco. Servidor MWL não iniciado.")
        return

    ae = AE(ae_title=MWL_AE_TITLE)
    handlers = [(evt.EVT_C_FIND, handle_find_mwl, [worklist_provider])]

    ae.add_supported_context(ModalityWorklistInformationFind)
    ae.add_supported_context('1.2.840.10008.1.1')  # C-ECHO
    # Opcional: aceita Storage (caso queira testar C-STORE)
    #ae.supported_contexts = ae.supported_contexts + StoragePresentationContexts
    for context in StoragePresentationContexts:
        ae.add_supported_context(context.abstract_syntax)   

    logging.info(t('server_starting', host=MWL_HOST, port=MWL_PORT, ae=MWL_AE_TITLE.decode()))
    print("-" * 50)
    print(t('server_started_banner', host=MWL_HOST, port=MWL_PORT))
    print(t('server_started_ae', ae=MWL_AE_TITLE.decode()))
    print(t('server_waiting'))
    print("-" * 50)

    ae.start_server((MWL_HOST, MWL_PORT), block=True, evt_handlers=handlers)

if __name__ == '__main__':
    run_mwl_scp()
