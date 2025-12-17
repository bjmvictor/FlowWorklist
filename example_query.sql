-- Exemplo de Query SQL Válida (17 colunas EXATAMENTE)
-- Use esta query como base para seus testes

SELECT 
  'BENJAMIN VICTOR SILVA' AS col_patient_name,        -- 1. Nome completo do paciente (conversão automática para DICOM)
  '1234' AS col_patient_id,                           -- 2. ID do Paciente
  '20030201' AS col_birth_date,                       -- 3. Data Nascimento (YYYYMMDD)
  'M' AS col_patient_sex,                             -- 4. Sexo (M/F/O)
  'TORAX - PA E LATERAL' AS col_exam_description,     -- 5. Descrição do Exame
  '123456' AS col_accession_number,                   -- 6. Número de Acesso/Pedido
  '20251216' AS col_exam_date,                        -- 7. Data do Exame (YYYYMMDD)
  '203205' AS col_exam_time,                          -- 8. Hora do Exame (HHMMSS)
  'MICHAEL MAYERS' AS col_physician_name,             -- 9. Nome completo do médico (conversão automática para DICOM)
  'CR' AS col_modality,                               -- 10. Modalidade (CR/CT/MR/US/...)
  'HIGH' AS col_priority,                             -- 11. Prioridade (HIGH/MEDIUM/LOW)
  'URGENCIA' AS col_encounter_type,                   -- 12. Tipo Atendimento
  '123456' AS col_encounter_id,                       -- 13. ID do Atendimento
  'EMERGENCY ROOM' AS col_unit_name,                  -- 14. Localização/Setor
  'FCR0000-0000' AS col_procedure_code,               -- 15. Código do Procedimento
  'TORAX - PA' AS col_code_meaning,                   -- 16. Significado do Código
  '99HOSP' AS col_code_scheme                         -- 17. Esquema de Codificação
FROM DUAL;

-- IMPORTANTE: 
-- ✅ Query DEVE retornar EXATAMENTE 17 colunas
-- ✅ Ordem das colunas é CRÍTICA (não pode mudar)
-- ✅ Nomes das colunas são ignorados (apenas a POSIÇÃO importa)
-- ✅ Use TO_CHAR() para formatar datas: TO_CHAR(data_coluna, 'YYYYMMDD')
-- ✅ Use TO_CHAR() para formatar horas: TO_CHAR(hora_coluna, 'HH24MISS')
-- ⚠️ NOMES: Envie como "NOME SOBRENOME" - o serviço converte para formato DICOM "SOBRENOME^NOME" automaticamente
-- ❌ NÃO use CONCAT(sobrenome, '^', nome) - o serviço faz isso automaticamente!

-- Exemplo com tabela real:
/*
SELECT 
  CONCAT(p.last_name, '^', p.first_name) AS nome_paciente,
  p.patient_id,
  TO_CHAR(p.birth_date, 'YYYYMMDD') AS nascimento,
  p.sex,
  w.procedure_description,
  w.accession_number,
  TO_CHAR(w.scheduled_date, 'YYYYMMDD') AS data_agendada,
  TO_CHAR(w.scheduled_time, 'HH24MISS') AS hora_agendada,
  CONCAT(d.last_name, '^', d.first_name) AS medico,
  w.modality,
  w.priority,
  w.encounter_type,
  w.encounter_id,
  w.location_name,
  w.procedure_code,
  w.code_meaning,
  w.code_scheme
FROM worklist_table w
JOIN patients p ON w.patient_id = p.patient_id
JOIN doctors d ON w.doctor_id = d.doctor_id
WHERE w.scheduled_date >= TRUNC(SYSDATE)
ORDER BY w.scheduled_date DESC;
*/
