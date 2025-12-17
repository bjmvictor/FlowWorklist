# Guia de Query SQL para Worklist DICOM

## Problema Identificado

A query atual está usando `FROM DUAL` que retorna apenas valores literais (dummy data) e não dados reais do banco. Isso resulta em "0 itens encontrados" mesmo que a conexão funcione.

## Estrutura Esperada

A query SQL **DEVE** retornar exatamente **17 colunas** na seguinte ordem:

| Posição | Nome Coluna | DICOM Field | Tipo | Exemplo |
|---------|-------------|-------------|------|---------|
| 1 | Patient Name | PatientName | VARCHAR2 | SILVA^BENJAMIN |
| 2 | Patient ID | PatientID | VARCHAR2 | 12345678 |
| 3 | Birth Date | PatientBirthDate | CHAR(8) YYYYMMDD | 20030201 |
| 4 | Sex | PatientSex | CHAR(1) M/F/O | M |
| 5 | Exam Description | RequestedProcedureDescription | VARCHAR2 | TORAX - PA |
| 6 | Accession Number | AccessionNumber | VARCHAR2 | P102025 |
| 7 | Exam Date | ScheduledProcedureStepStartDate | CHAR(8) YYYYMMDD | 20251216 |
| 8 | Exam Time | ScheduledProcedureStepStartTime | CHAR(6) HH24MISS | 143000 |
| 9 | Physician Name | ScheduledPerformingPhysicianName | VARCHAR2 | JONES^MARY |
| 10 | Modality | Modality | CHAR(2) | CR |
| 11 | Priority | Priority Flag | VARCHAR2 | HIGH |
| 12 | Encounter Type | Patient Type | VARCHAR2 | URGENCIA |
| 13 | Encounter ID | StudyInstanceUID | VARCHAR2 | 456789 |
| 14 | Unit/Location | Location | VARCHAR2 | EMERGENCY ROOM |
| 15 | Procedure Code | ScheduledProcedureStepID | VARCHAR2 | FCR0101 |
| 16 | Code Meaning | Code Meaning | VARCHAR2 | CHEST X-RAY |
| 17 | Code Scheme | Code Scheme Designator | VARCHAR2 | CBR |

## Exemplos de Queries Válidas

### Exemplo 1: Query Simples (Teste com dados dummy)
```sql
SELECT 
  'SILVA^BENJAMIN' AS col_patient_name,
  '12345678' AS col_patient_id,
  '20030201' AS col_birth_date,
  'M' AS col_patient_sex,
  'TORAX - PA' AS col_exam_description,
  'P102025' AS col_accession_number,
  '20251216' AS col_exam_date,
  '143000' AS col_exam_time,
  'JONES^MARY' AS col_physician_name,
  'CR' AS col_modality,
  'HIGH' AS col_priority,
  'URGENCIA' AS col_encounter_type,
  '456789' AS col_encounter_id,
  'EMERGENCY ROOM' AS col_unit_name,
  'FCR0101' AS col_procedure_code,
  'CHEST X-RAY' AS col_code_meaning,
  'CBR' AS col_code_scheme
FROM DUAL
```

### Exemplo 2: Query Real com Tabela de Pacientes
```sql
SELECT 
  CONCAT(p.last_name, '^', p.first_name) AS col_patient_name,
  p.patient_id AS col_patient_id,
  TO_CHAR(p.birth_date, 'YYYYMMDD') AS col_birth_date,
  p.sex AS col_patient_sex,
  w.procedure_description AS col_exam_description,
  w.accession_number AS col_accession_number,
  TO_CHAR(w.scheduled_date, 'YYYYMMDD') AS col_exam_date,
  TO_CHAR(w.scheduled_time, 'HH24MISS') AS col_exam_time,
  CONCAT(d.last_name, '^', d.first_name) AS col_physician_name,
  w.modality AS col_modality,
  DECODE(w.priority, 'U', 'LOW', 'R', 'MEDIUM', 'H', 'HIGH', 'LOW') AS col_priority,
  w.encounter_type AS col_encounter_type,
  w.encounter_id AS col_encounter_id,
  w.location_name AS col_unit_name,
  w.procedure_code AS col_procedure_code,
  w.code_meaning AS col_code_meaning,
  w.code_scheme_designator AS col_code_scheme
FROM worklist_view w
JOIN patients p ON w.patient_id = p.patient_id
JOIN doctors d ON w.doctor_id = d.doctor_id
WHERE TRUNC(w.scheduled_date) >= TRUNC(SYSDATE) - 7
ORDER BY w.scheduled_date DESC, w.scheduled_time ASC
```

### Exemplo 3: Query com Tabela Resumida (Se dados em tabela simples)
```sql
SELECT 
  nome AS col_patient_name,
  matricula AS col_patient_id,
  TO_CHAR(data_nascimento, 'YYYYMMDD') AS col_birth_date,
  sexo AS col_patient_sex,
  descricao_exame AS col_exam_description,
  numero_pedido AS col_accession_number,
  TO_CHAR(data_agendada, 'YYYYMMDD') AS col_exam_date,
  TO_CHAR(hora_agendada, 'HH24MISS') AS col_exam_time,
  medico_responsavel AS col_physician_name,
  modalidade AS col_modality,
  prioridade AS col_priority,
  tipo_atendimento AS col_encounter_type,
  id_atendimento AS col_encounter_id,
  setor AS col_unit_name,
  codigo_procedimento AS col_procedure_code,
  descricao_procedimento AS col_code_meaning,
  tabela_codigo AS col_code_scheme
FROM agendamentos
WHERE data_agendada >= TRUNC(SYSDATE)
AND status = 'ATIVO'
ORDER BY data_agendada DESC, hora_agendada ASC
```

## Como Corrigir

1. **Identifique** as tabelas reais no seu Oracle (ex: `patients`, `worklist`, `scheduled_procedures`)
2. **Mapeie** os nomes de colunas reais para os 17 campos esperados
3. **Use funções Oracle** para formatar datas e valores (TO_CHAR, DECODE, CONCAT)
4. **Teste** a query no SQL Developer ou sqlplus:
   ```sql
   -- Deve retornar 17 colunas
   SELECT * FROM (sua_query_aqui);
   ```
5. **Atualize** a chave `query` em `config.json` com sua query real

## Verificação Rápida

Para verificar quantas colunas sua query retorna:
```sql
SELECT COUNT(*) as column_count 
FROM table(dbms_sql.describe_columns(...)...);
```

Ou execute a query e verifique no terminal quantas colunas aparecem.

## Dicas Importantes

- ✅ Use **exatamente 17 colunas** - nem mais, nem menos
- ✅ Respeite a **ordem** das colunas
- ✅ Use **TO_CHAR()** para formatar datas e horas
- ✅ Use **CONCAT()** ou **||** para separar nomes com `^`
- ❌ Não use `FROM DUAL` com dados dummy em produção
- ❌ Não adicione ou remova colunas sem atualizar `column_mapping`

## Teste Local

Depois de atualizar a query, reinicie os serviços:
```powershell
# Terminal 1
C:/path/Scripts/python.exe mwl_service.py

# Terminal 2
C:/path/Scripts/python.exe startapp.py

# Acesse: http://localhost:5000/tests
# Clique em "DICOM Worklist Test"
```

Você deve ver itens da worklist sendo retornados (count > 0).
