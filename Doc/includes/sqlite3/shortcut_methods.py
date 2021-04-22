import sqlite3

persons = [("Hugo", "Boss"), ("Calvin", "Klein")]
con = sqlite3.connect(":memory:")
con.execute("create table person(firstname, lastname)")
con.executemany("insert into person(firstname, lastname) values (?, ?)", persons)
for row in con.execute("select firstname, lastname from person"):
    print(row)
print("I just deleted", con.execute("delete from person").rowcount, "rows")
con.close()
