# DICOM Worklist Column Mapping Guide

This guide explains how to configure your SQL query to properly map database columns to DICOM Modality Worklist fields.

## Overview

The FlowWorklist MWLSCP server expects your SQL query to return **exactly 17 columns** in a **specific order**. The column names in your SQL query don't matter—only the **position/order** matters.

## Column Mapping Reference

| Pos | Generic Name | DICOM Field | Description | Format | Example |
|-----|---|---|---|---|---|
| 1 | `col_patient_name` | **PatientName** | The full name of the patient. Used for patient identification on the modality and in reports. | Text (names separated by ^ for first/middle/last) | `SMITH^JOHN^M` |
| 2 | `col_patient_id` | **PatientID** | A unique identifier for the patient within the hospital or system. This is crucial for linking studies. | Text (alphanumeric) | `12345678` |
| 3 | `col_birth_date` | **PatientBirthDate** | The patient's date of birth, formatted as YYYYMMDD. Important for age-related protocol checks and patient demographics. | YYYYMMDD (8 digits) | `19751025` |
| 4 | `col_patient_sex` | **PatientSex** | The patient's biological sex. Typically represented as M (Male), F (Female), or O (Other). | Single character: M, F, or O | `M` |
| 5 | `col_exam_description` | **RequestedProcedureDescription** | A free-text description of the procedure or exam requested. This helps the technologist understand the context. | Text | `RX TORAX PA E LATERAL` |
| 6 | `col_accession_number` | **AccessionNumber / RequestedProcedureID** | A unique identifier for the specific request (the order). In Worklist, this is often the Accession Number or order ID. | Text or numeric | `P102025` |
| 7 | `col_exam_date` | **ScheduledProcedureStepStartDate** | The scheduled or requested date for the exam, formatted as YYYYMMDD. | YYYYMMDD (8 digits) | `20251216` |
| 8 | `col_exam_time` | **ScheduledProcedureStepStartTime** | The scheduled or requested time for the exam, formatted as HH24MISS (24-hour format). | HH24MISS (6 digits) | `143000` |
| 9 | `col_physician_name` | **ScheduledPerformingPhysicianName** | The name of the physician/provider responsible for ordering or referring the exam. | Text (names separated by ^ for first/middle/last) | `JONES^MARY` |
| 10 | `col_modality` | **Modality** | The type of imaging equipment that will perform the exam. Standard DICOM modality codes. | 2-letter DICOM code (CR, CT, US, MR, etc.) | `CR` |
| 11 | `col_priority` | **Priority Flag** | A derived priority level based on triage classification. Used for scheduling and workflow prioritization. | Text (HIGH, MEDIUM, LOW) | `HIGH` |
| 12 | `col_encounter_type` | **Encounter Type** | The type of hospital visit or encounter. | Text (URGENCIA, INTERNACAO, AMBULATORIO, etc.) | `URGENCIA` |
| 13 | `col_encounter_id` | **StudyInstanceUID / Encounter ID** | The unique identifier for the patient's current hospital encounter or admission. | Text or numeric | `456789` |
| 14 | `col_unit_name` | **Location** | The name of the hospital unit or sector where the patient is located or where the request originated. | Text | `EMERGENCY ROOM` |
| 15 | `col_procedure_code` | **ScheduledProcedureStepID (Procedure Code)** | A coded value identifying the specific procedure being requested. Often prefixed with an institutional code (e.g., FCR). | Text (alphanumeric code) | `FCR0101` |
| 16 | `col_code_meaning` | **Code Meaning** | The descriptive meaning associated with the procedure code. | Text | `CHEST X-RAY` |
| 17 | `col_code_scheme` | **Code Scheme Designator** | Identifies the coding system used for the procedure code (e.g., SNOMED, CBR, DCM). | Text (coding standard abbreviation) | `CBR` |

## Current Production Query

Your current production query returns columns in this exact order:

```sql
SELECT
    paciente.nm_paciente,                                    -- 1. col_patient_name
    paciente.cd_paciente,                                     -- 2. col_patient_id
    TO_CHAR(paciente.dt_nascimento, 'YYYYMMDD'),             -- 3. col_birth_date
    paciente.tp_sexo,                                         -- 4. col_patient_sex
    exa_rx.ds_exa_rx,                                         -- 5. col_exam_description
    ped_rx.cd_ped_rx,                                         -- 6. col_accession_number
    TO_CHAR(ped_rx.dt_pedido, 'YYYYMMDD'),                   -- 7. col_exam_date
    TO_CHAR(ped_rx.hr_pedido, 'HH24MISS'),                   -- 8. col_exam_time
    prestador.nm_prestador,                                   -- 9. col_physician_name
    CASE WHEN exa_rx.ds_exa_rx LIKE '%RX%' THEN 'CR' ELSE 'CT' END, -- 10. col_modality
    CASE WHEN sacr_classificacao.ds_sigla = 'PI' THEN 'HIGH' WHEN sacr_classificacao.ds_sigla = 'PII' THEN 'MEDIUM' ELSE 'LOW' END, -- 11. col_priority
    decode(atendime.tp_atendimento,'U', 'URGENCIA', 'I', 'INTERNACAO', 'A', 'AMBULATORIO'), -- 12. col_encounter_type
    atendime.cd_atendimento,                                  -- 13. col_encounter_id
    setor.nm_setor,                                           -- 14. col_unit_name
    'FCR'||wk.procedure_code_value,                           -- 15. col_procedure_code
    wk.code_meaning,                                          -- 16. col_code_meaning
    wk.code_scheme_designator                                 -- 17. col_code_scheme
FROM dbamv.ped_rx
-- ... JOIN statements ...
```

## Important Notes

### ✅ Do's
- **Always return 17 columns** in the specified order
- **Use the generic column names** (`col_patient_name`, `col_patient_id`, etc.) for clarity
- **Format dates as YYYYMMDD** (8 digits, e.g., 20251216)
- **Format times as HH24MISS** (6 digits, e.g., 143000 for 2:30 PM)
- **Use ^ separator** in names for first/middle/last (e.g., `SMITH^JOHN^M`)
- **Use standard DICOM modality codes** (CR, CT, US, MR, RF, NM, PT, etc.)
- **NULL values are acceptable** - empty strings will be used if a field is NULL

### ❌ Don'ts
- **Don't reorder columns** - the position is what matters, not the name
- **Don't change the number of columns** - always return exactly 17
- **Don't use lowercase or special formatting** - match the examples in the guide
- **Don't forget the CASE statements** for derived fields (modality, priority, encounter type)
- **Don't use NULL directly in DICOM text fields** - use empty string or meaningful default values

## Customization Examples

### Example 1: Adding a Hospital Code Prefix to Accession Number
If you want to prefix the accession number with your hospital code:

```sql
'HOSP-' || ped_rx.cd_ped_rx AS accession_number,  -- Position 6
```

### Example 2: Using Different Modality Logic
If your exam descriptions use different patterns:

```sql
CASE 
    WHEN exa_rx.ds_exa_rx LIKE '%CT%' THEN 'CT'
    WHEN exa_rx.ds_exa_rx LIKE '%RX%' THEN 'CR'
    WHEN exa_rx.ds_exa_rx LIKE '%ULTRASSOM%' THEN 'US'
    WHEN exa_rx.ds_exa_rx LIKE '%RESSONANCIA%' THEN 'MR'
    ELSE 'OT'
END AS modalidade,  -- Position 10
```

### Example 3: Using NULL Coalescing for Optional Fields
If some fields might be NULL, use COALESCE:

```sql
COALESCE(prestador.nm_prestador, 'UNKNOWN') AS medico_responsavel,  -- Position 9
```

## Testing Your Configuration

1. **Verify column count**: Execute your query and confirm it returns exactly 17 columns
2. **Check data types**: Ensure dates/times are formatted correctly
3. **Test MWLSCP**: Start the server and check the logs for any errors
4. **Query via C-FIND**: Use a DICOM client (e.g., findscu) to query the worklist

```bash
# Example using findscu (if available)
findscu -aec MWLSCP -aet ConsoleApp 192.168.1.3 11112
```

## Configuration File Location

The column mapping is documented in `config.json` under the `database.column_mapping` section. This serves as a reference for your team and can be used to generate documentation or UI guides.

## Support

If you encounter issues:
1. Check the `logs/mwl_server.log` file for detailed error messages
2. Verify that all 17 columns are being returned in the correct order
3. Ensure data formatting matches the specifications (dates, times, codes)
4. Test your SQL query directly in your database client
