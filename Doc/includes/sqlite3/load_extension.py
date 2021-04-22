import sqlite3

con = sqlite3.connect(":memory:")
con.enable_load_extension(True)
con.execute("select load_extension('./fts3.so')")
con.enable_load_extension(False)
con.execute("create virtual table recipe using fts3(name, ingredients)")
con.executescript(
    "\n    insert into recipe (name, ingredients) values ('broccoli stew', 'broccoli peppers cheese tomatoes');\n    insert into recipe (name, ingredients) values ('pumpkin stew', 'pumpkin onions garlic celery');\n    insert into recipe (name, ingredients) values ('broccoli pie', 'broccoli cheese onions flour');\n    insert into recipe (name, ingredients) values ('pumpkin pie', 'pumpkin sugar flour butter');\n    "
)
for row in con.execute(
    "select rowid, name, ingredients from recipe where name match 'pie'"
):
    print(row)
con.close()
