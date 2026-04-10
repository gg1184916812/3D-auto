# -*- coding: utf-8 -*-
import json, os, time

INPUT_FILE = "training_dataset.jsonl"
OUTPUT_FILE = "training_dataset_cleaned.jsonl"
LOG_FILE = "dedup_log.txt"

seen = set()
dup_count = 0
total_count = 0
unique_count = 0

with open(INPUT_FILE, "r", encoding="utf-8") as fin, open(OUTPUT_FILE, "w", encoding="utf-8") as fout:
    for line in fin:
        total_count += 1
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            key = json.dumps(data.get("instruction", ""), ensure_ascii=False)
        except:
            key = line
        if key in seen:
            dup_count += 1
        else:
            seen.add(key)
            unique_count += 1
            fout.write(line + "\n")

log_content = """去重報告
============================================================
輸入檔案: {0}
輸出檔案: {1}
============================================================
總行數: {2}
重複行數: {3}
清理後行數: {4}
============================================================
完成時間: {5}
""".format(
    INPUT_FILE,
    OUTPUT_FILE,
    total_count,
    dup_count,
    unique_count,
    time.strftime("%Y-%m-%d %H:%M:%S")
)

with open(LOG_FILE, "w", encoding="utf-8") as flog:
    flog.write(log_content)

print(log_content)
print("已備份原始檔案: {0}".format(INPUT_FILE + ".bak"))
os.rename(INPUT_FILE, INPUT_FILE + ".bak")
os.rename(OUTPUT_FILE, INPUT_FILE)
print("完成！")
