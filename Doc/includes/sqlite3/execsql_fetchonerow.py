import sqlite3

con = sqlite3.connect("mydb")
cur = con.cursor()
SELECT = "select name_last, age from people order by age, name_last"
cur.execute(SELECT)
for (name_last, age) in cur:
    print(("%s is %d years old." % (name_last, age)))
cur.execute(SELECT)
for row in cur:
    print(("%s is %d years old." % (row[0], row[1])))
con.close()
