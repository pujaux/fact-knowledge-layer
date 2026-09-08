from app import db

with open('facts_list.txt', 'w', encoding='utf-8') as out:
    for f in db.get_all_facts():
        out.write(f"{f['id']} | {f['doc_name']} | {f['entity']} | {f['metric']} | {f['value']}\n")

print('done')