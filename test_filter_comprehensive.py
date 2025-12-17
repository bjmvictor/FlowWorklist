#!/usr/bin/env python
"""
Comprehensive test to verify DICOM wildcard filtering logic works correctly.
This test simulates the exact filter matching logic in mwl_service.py
"""

import re
import logging

# Configure logging to see debug output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)-8s - %(message)s'
)

def matches_filter(db_value, filter_value):
    """
    Checks if a database value matches a filter value.
    Supports DICOM wildcards: * (any characters) and ? (single character).
    If filter_value is None, returns True (no filter applied).
    """
    if filter_value is None:
        return True
    
    # Normalize for case-insensitive comparison
    db_value = str(db_value).upper() if db_value else ""
    filter_value = str(filter_value).upper() if filter_value else ""
    
    # Convert DICOM wildcards to regex
    regex_pattern = re.escape(filter_value)  # Escape special regex chars
    regex_pattern = regex_pattern.replace(r'\*', '.*')  # * matches any characters
    regex_pattern = regex_pattern.replace(r'\?', '.')   # ? matches single character
    regex_pattern = f"^{regex_pattern}$"  # Match entire string
    
    try:
        matches = bool(re.match(regex_pattern, db_value))
        logging.debug(f"matches_filter: '{db_value}' vs '{filter_value}' (regex: {regex_pattern}) = {matches}")
        return matches
    except re.error as e:
        logging.error(f"Regex error: {e} for pattern {regex_pattern}")
        return False


# Test cases
test_cases = [
    # (db_value, filter_value, expected_result, description)
    ("BENJAMIN VIEIRA", "BENJAMIN*", True, "Exact start match with wildcard"),
    ("BENJAMIN VIEIRA", "BENJAMIN", False, "Exact match without wildcard (no trailing)"),
    ("BENJAMIN", "BENJAMIN*", True, "Exact match with wildcard that matches nothing"),
    ("EDUARDO FERREIRA", "BENJAMIN*", False, "Different name should not match"),
    ("BILLY", "B?LLY", True, "Single char wildcard match"),
    ("BILLY", "B*LLY", True, "Prefix wildcard match"),
    ("BILLY", "?ILLY", True, "Leading single char wildcard"),
    ("BENJAMIN VIEIRA", "*BENJAMIN*", True, "Wildcard on both sides"),
    ("BENJAMIN", "*BENJAMIN", True, "Wildcard at start"),
    ("BENJAMIN", "BENJAMIN", True, "Exact match"),
    ("BENJAMIN", "BEN*", True, "Prefix match"),
    ("BENJAMIN", "*JAMIN", True, "Suffix match"),
    ("BENJAMIN", None, True, "No filter (None) should always match"),
    ("HELLO", "HELLO", True, "Case-insensitive exact match"),
    ("hello", "HELLO", True, "Case-insensitive (lower to upper)"),
    ("HELLO", "hello", True, "Case-insensitive (upper to lower)"),
]

print("\n" + "="*80)
print("COMPREHENSIVE DICOM FILTER TEST")
print("="*80 + "\n")

passed = 0
failed = 0

for db_value, filter_value, expected, description in test_cases:
    result = matches_filter(db_value, filter_value)
    status = "✓ PASS" if result == expected else "✗ FAIL"
    
    if result == expected:
        passed += 1
    else:
        failed += 1
    
    print(f"{status}: {description}")
    print(f"       DB Value: '{db_value}'")
    print(f"       Filter:   '{filter_value}'")
    print(f"       Expected: {expected}, Got: {result}")
    print()

print("="*80)
print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
print("="*80)

# Simulate the exact scenario from the issue
print("\n" + "="*80)
print("SCENARIO: User queries with PatientName='BENJAMIN*'")
print("="*80 + "\n")

# Simulate database records
db_records = [
    {"nm_paciente": "BENJAMIN VIEIRA", "cd_paciente": "12345", "tp_sexo": "M"},
    {"nm_paciente": "EDUARDO FERREIRA", "cd_paciente": "54321", "tp_sexo": "M"},
    {"nm_paciente": "MARIA SILVA", "cd_paciente": "99999", "tp_sexo": "F"},
]

# User provides filter
patient_name_filter = "BENJAMIN*"
patient_id_filter = None
sex_filter = None

print(f"Applied filters:")
print(f"  PatientName: {patient_name_filter}")
print(f"  PatientID: {patient_id_filter}")
print(f"  Sex: {sex_filter}\n")

print("Checking database records:")
matching_records = []

for record in db_records:
    db_patient_name = str(record.get('nm_paciente', '')).strip()
    db_patient_id = str(record.get('cd_paciente', '')).strip()
    db_sex = str(record.get('tp_sexo', '')).strip()
    
    # Apply filter logic (from mwl_service.py)
    if not matches_filter(db_patient_name, patient_name_filter):
        print(f"  ✗ {db_patient_name} - FILTERED OUT (PatientName mismatch)")
        continue
    if not matches_filter(db_patient_id, patient_id_filter):
        print(f"  ✗ {db_patient_name} - FILTERED OUT (PatientID mismatch)")
        continue
    if sex_filter and db_sex.upper() != sex_filter.upper():
        print(f"  ✗ {db_patient_name} - FILTERED OUT (Sex mismatch)")
        continue
    
    # If we get here, the record passes all filters
    print(f"  ✓ {db_patient_name} - PASSED all filters")
    matching_records.append(record)

print(f"\nExpected results: Only 'BENJAMIN VIEIRA' should be returned")
print(f"Actual results: {len(matching_records)} record(s) returned")
if len(matching_records) > 0:
    for rec in matching_records:
        print(f"  - {rec['nm_paciente']}")

if len(matching_records) == 1 and matching_records[0]['nm_paciente'] == "BENJAMIN VIEIRA":
    print("\n✓ SCENARIO TEST PASSED: Filter working correctly!")
else:
    print("\n✗ SCENARIO TEST FAILED: Filter not working as expected!")
