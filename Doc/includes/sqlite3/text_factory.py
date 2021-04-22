import sqlite3

con = sqlite3.connect(":memory:")
cur = con.cursor()
AUSTRIA = "Österreich"
cur.execute("select ?", (AUSTRIA,))
row = cur.fetchone()
assert row[0] == AUSTRIA
con.text_factory = bytes
cur.execute("select ?", (AUSTRIA,))
row = cur.fetchone()
assert type(row[0]) is bytes
assert row[0] == AUSTRIA.encode("utf-8")
con.text_factory = lambda x: (x.decode("utf-8") + "foo")
cur.execute("select ?", ("bar",))
row = cur.fetchone()
assert row[0] == "barfoo"
con.close()
