import json
from collections import defaultdict

INPUT = "stanford_people.json"
OUTPUT = "stanford_people_clean.json"

with open(INPUT, "r", encoding="utf-8") as f:
    data = json.load(f)

unique = {}
faculty_names = set()

# 先记录 faculty
for item in data:
    if item.get("status") == "faculty":
        faculty_names.add(item["name"])
        unique[item["name"]] = item

def normalize_name(name):
    return name.lower().strip()

for item in data:
    name = item["name"]

    # faculty 跳过，保留原样
    if item.get("status") == "faculty":
        continue

    # 合并 student / postdoc / industry
    key = normalize_name(name)

    # group 集合删除
    if item.get("status") == "group":
        continue

    # 如果 duplicate entry
    if key in unique:
        # 合并 advisor
        old = unique[key]
        advisors_old = set(old.get("advisor", []))
        advisors_new = set(item.get("advisor", []))
        old["advisor"] = list(advisors_old.union(advisors_new))
        
        # citations 用最大值
        if "citations" in item:
            c_old = old.get("citations", {})
            c_new = item["citations"]
            for k,v in c_new.items():
                c_old[k] = max(c_old.get(k,0), v)
            old["citations"] = c_old
            
        continue

    unique[key] = item

clean = list(unique.values())

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(clean, f, indent=2, ensure_ascii=False)

print(f"去重完成，共 {len(clean)} 条数据。保存 → {OUTPUT}")
