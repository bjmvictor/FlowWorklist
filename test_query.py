import cx_Oracle
import json

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

query = config['database']['query']
print(f"Query length: {len(query)}")
print(f"Query: {query[:200]}...")

# Test connection
try:
    conn = cx_Oracle.connect('db_weknow', 'pass_1929', '192.168.1.3:1521/PRD')
    cur = conn.cursor()
    cur.execute(query)
    row = cur.fetchone()
    print(f"\n✓ Query executed successfully!")
    print(f"Columns returned: {len(row)}")
    print(f"First 3 values: {row[:3]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"\n✗ Query failed: {e}")
