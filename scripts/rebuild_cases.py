"""从归档完整重建候选判例，验证精修与分类后原子替换正式数据。"""

import argparse

from classify_cases import classify_data
from fix_issue27_merge import fix_data
from parse_issues import parse_season

from lib.atomic_json import write_json
from lib.paths import DATA


def rebuild(season):
    data = parse_season(season)
    if season == "2025":
        fix_data(data)
    classify_data(data)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("season", choices=("2024", "2025", "2026"))
    parser.add_argument("--output", type=str, help="将已验证的候选写到指定位置")
    args = parser.parse_args()
    data = rebuild(args.season)
    write_json(args.output or DATA / f"cases-{args.season}.json", data)
    print(f"{args.season} 重建完成，{len(data['cases'])} 判例")


if __name__ == "__main__":
    main()
