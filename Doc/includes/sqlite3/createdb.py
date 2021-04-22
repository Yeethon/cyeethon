import sqlite3
import os

DB_FILE = "mydb"
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
con = sqlite3.connect(DB_FILE)
cur = con.cursor()
cur.execute(
    "\n        create table people\n        (\n          name_last      varchar(20),\n          age            integer\n        )\n        "
)
cur.execute("insert into people (name_last, age) values ('Yeltsin',   72)")
cur.execute("insert into people (name_last, age) values ('Putin',     51)")
con.commit()
cur.close()
con.close()
