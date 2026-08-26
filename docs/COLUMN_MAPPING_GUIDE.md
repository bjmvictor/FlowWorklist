# DICOM worklist column mapping

FlowWorklist maps query results by position. SQL aliases are descriptive only; the service requires exactly 17 columns in this order.

| # | Meaning | Primary DICOM destination | Format |
|---:|---|---|---|
| 1 | Patient name | Patient Name (0010,0010) | DICOM PN; `FAMILY^GIVEN` preferred |
| 2 | Patient ID | Patient ID (0010,0020) | Text |
| 3 | Birth date | Patient Birth Date (0010,0030) | `YYYYMMDD` |
| 4 | Sex | Patient Sex (0010,0040) | `M`, `F`, or `O` |
| 5 | Requested procedure description | Requested Procedure Description (0032,1060) | Text |
| 6 | Accession number | Accession Number (0008,0050) | Text |
| 7 | Scheduled date | Scheduled Procedure Step Start Date (0040,0002) | `YYYYMMDD` |
| 8 | Scheduled time | Scheduled Procedure Step Start Time (0040,0003) | `HHMMSS` |
| 9 | Performing physician | Scheduled Performing Physician Name (0040,0006) | DICOM PN |
| 10 | Modality | Modality (0008,0060) | Standard DICOM modality code |
| 11 | Priority | Scheduling/priority context | `HIGH`, `MEDIUM`, or `LOW` |
| 12 | Encounter type | Internal workflow context | Text |
| 13 | Encounter ID | Internal workflow context | Text |
| 14 | Location | Scheduled Station Name (0040,0010) | Text |
| 15 | Procedure code | Scheduled Procedure Step ID (0040,0009) | Text |
| 16 | Code meaning | Scheduled Protocol Code Sequence | Text |
| 17 | Coding scheme | Coding Scheme Designator (0008,0102) | Registered or local scheme |

## Mapping rules

- Always return all 17 positions, even when optional source values are null.
- Format dates and times in DICOM compact format without separators.
- Use standard modality codes such as `CR`, `CT`, `MR`, `US`, `NM`, or `PT`.
- Keep patient, accession, procedure, and encounter identifiers stable across MWL and MPPS workflows.
- Use a documented local coding scheme when a standard coding system is not available.
- Normalize unsupported nulls to empty strings or a clinically approved default in SQL.
- Validate character encoding and person-name separators with every target modality.

## Customization examples

Add a controlled prefix without changing column position:

```sql
SELECT
  patient_name,
  patient_id,
  birth_date,
  sex,
  procedure_description,
  'SITE-' || accession_number,
  scheduled_date,
  scheduled_time,
  physician_name,
  modality,
  priority,
  encounter_type,
  encounter_id,
  location,
  procedure_code,
  code_meaning,
  code_scheme
FROM worklist_source
```

Use engine-appropriate null handling, for example `COALESCE(value, '')`, while preserving the 17-column order.

## Validation

1. Run the SQL with the same account configured in FlowWorklist.
2. Confirm exactly 17 columns and inspect null, date, time, and character values.
3. Run the database test in the management interface.
4. Start MWL and run C-ECHO.
5. Query from a test modality or DCMTK:

```powershell
findscu -W -aec FLOWMWL -aet MODALITY_AE 127.0.0.1 11112 -k 0008,0052=WORKLIST -k 0010,0010
```

The canonical SQL contract and query example are maintained in the [SQL Query Guide](SQL_QUERY_GUIDE.md).
