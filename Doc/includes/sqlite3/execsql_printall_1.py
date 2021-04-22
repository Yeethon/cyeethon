import sqlite3

con = sqlite3.connect("mydb")
cur = con.cursor()
cur.execute("select * from people order by age")
print(cur.fetchall())
con.close()
