# SQL Query Guide

FlowWorklist expects every worklist query row to return exactly 17 columns in the order below. Column aliases are optional; position is authoritative.

| Position | Meaning | DICOM destination | Expected format |
|---:|---|---|---|
| 1 | Patient name | PatientName | Text; `FAMILY^GIVEN` preferred |
| 2 | Patient ID | PatientID | Text |
| 3 | Birth date | PatientBirthDate | `YYYYMMDD` |
| 4 | Sex | PatientSex | `M`, `F`, or `O` |
| 5 | Exam description | RequestedProcedureDescription | Text |
| 6 | Exam/order ID | AccessionNumber | Text |
| 7 | Scheduled date | ScheduledProcedureStepStartDate | `YYYYMMDD` |
| 8 | Scheduled time | ScheduledProcedureStepStartTime | `HHMMSS` |
| 9 | Physician | ScheduledPerformingPhysicianName | Text |
| 10 | Modality | Modality | Standard DICOM code |
| 11 | Priority | Priority | `HIGH`, `MEDIUM`, or `LOW` |
| 12 | Encounter type | Internal context | Text |
| 13 | Encounter ID | Internal context | Text |
| 14 | Unit/location | ScheduledStationName | Text |
| 15 | Procedure code | ScheduledProcedureStepID | Text |
| 16 | Code meaning | ScheduledProtocolCodeSequence | Text |
| 17 | Coding scheme | CodingSchemeDesignator | Text |

## Oracle example

```sql
SELECT
  p.patient_name,
  p.patient_id,
  TO_CHAR(p.birth_date, 'YYYYMMDD'),
  p.sex,
  e.exam_description,
  e.accession_number,
  TO_CHAR(e.scheduled_at, 'YYYYMMDD'),
  TO_CHAR(e.scheduled_at, 'HH24MISS'),
  e.physician_name,
  e.modality,
  e.priority,
  e.encounter_type,
  e.encounter_id,
  e.unit_name,
  e.procedure_code,
  e.code_meaning,
  e.code_scheme
FROM exam_worklist e
JOIN patients p ON p.patient_id = e.patient_id
WHERE e.completed = 'N'
```

Use the database test before testing DICOM. Run the query with the same read-only account used by FlowWorklist and confirm that dates, times, nulls, character encoding, and column order are correct. Avoid `FROM DUAL` dummy queries in production.

See [Column Mapping Guide](COLUMN_MAPPING_GUIDE.md) for detailed field behavior.
