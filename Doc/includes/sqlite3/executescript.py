import sqlite3

con = sqlite3.connect(":memory:")
cur = con.cursor()
cur.executescript(
    "\n    create table person(\n        firstname,\n        lastname,\n        age\n    );\n\n    create table book(\n        title,\n        author,\n        published\n    );\n\n    insert into book(title, author, published)\n    values (\n        'Dirk Gently''s Holistic Detective Agency',\n        'Douglas Adams',\n        1987\n    );\n    "
)
con.close()
