import sqlite3

con = sqlite3.connect(":memory:")
cur = con.cursor()
cur.execute("create table lang (lang_name, lang_age)")
cur.execute("insert into lang values (?, ?)", ("C", 49))
lang_list = [("Fortran", 64), ("Python", 30), ("Go", 11)]
cur.executemany("insert into lang values (?, ?)", lang_list)
cur.execute(
    "select * from lang where lang_name=:name and lang_age=:age",
    {"name": "C", "age": 49},
)
print(cur.fetchall())
con.close()
