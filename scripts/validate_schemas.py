# -*- coding: utf-8 -*-
"""数据 JSON 契约校验：schemas/*.schema.json × data/*.json（lib.jsonschema_lite 迷你校验器）。

schema 是对外发布的数据契约（外部消费者可直接拿走），校验挂在 test_integrity
与 CI——手改数据漏字段/拼错枚举值在这里第一时间爆红，而不是等到页面渲染。

用法：python scripts/validate_schemas.py（打印报告，退出码即结论）
      from validate_schemas import validate_all  # test_integrity 消费，返回问题列表
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.jsonschema_lite import validate  # noqa: E402
from lib.paths import DATA, ROOT  # noqa: E402

SCHEMAS = ROOT / "schemas"

# (schema 文件, 数据文件) 清单——cases/impact 按赛季三份共用同一 schema
PAIRS = [
    ("cases.schema.json", [f"cases-{s}.json" for s in ("2024", "2025", "2026")]),
    ("impact.schema.json", [f"impact-{s}.json" for s in ("2024", "2025", "2026")]),
    ("quiz-answers.schema.json", ["quiz-answers.json"]),
    ("weekly.schema.json", ["weekly.json"]),
]


def validate_all():
    problems = []
    for schema_name, data_names in PAIRS:
        schema_path = SCHEMAS / schema_name
        if not schema_path.exists():
            problems.append(f"缺少 schemas/{schema_name}")
            continue
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        for data_name in data_names:
            data_path = DATA / data_name
            if not data_path.exists():
                problems.append(f"缺少 data/{data_name}")
                continue
            data = json.loads(data_path.read_text(encoding="utf-8"))
            found = validate(data, schema, path=data_name)
            problems += found[:20]  # 单文件最多报 20 条，避免刷屏淹没别的信号
            if len(found) > 20:
                problems.append(f"{data_name}: ……另有 {len(found) - 20} 处问题")
    return problems


def main():
    problems = validate_all()
    n_files = sum(len(names) for _, names in PAIRS)
    if problems:
        print(f"schema 校验失败，共 {len(problems)} 项：")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"schema 校验通过: {len(PAIRS)} 份契约 × {n_files} 个数据文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
