import sqlite3
conn = sqlite3.connect('data/facts.db')
conn.execute("DELETE FROM relationships WHERE relation='unrelated' AND explanation LIKE 'error:%'")
conn.commit()
print('cleared', conn.total_changes, 'bad rows')