import sqlite3

FIELD_MAX_WIDTH = 20
TABLE_NAME = "people"
SELECT = "select * from %s order by age, name_last" % TABLE_NAME
con = sqlite3.connect("mydb")
cur = con.cursor()
cur.execute(SELECT)
for fieldDesc in cur.description:
    print(fieldDesc[0].ljust(FIELD_MAX_WIDTH), end=" ")
print()
print(("-" * 78))
fieldIndices = range(len(cur.description))
for row in cur:
    for fieldIndex in fieldIndices:
        fieldValue = str(row[fieldIndex])
        print(fieldValue.ljust(FIELD_MAX_WIDTH), end=" ")
    print()
con.close()
