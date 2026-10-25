# -*- coding: utf-8 -*-
"""JSON Schema 迷你校验器（纯 stdlib，支持 draft-07 子集）。

只实现 schemas/ 目录实际用到的关键字：type / enum / pattern / required /
properties / additionalProperties / items / minItems / minLength。
刻意不实现 $ref/allOf/oneOf 等高级语义——本仓库的 schema 只作数据契约
与 CI 护栏，不是通用校验器；引入完整实现违反零依赖约束。

用法：problems = validate(instance, schema)，返回问题列表（空=通过）。
"""

import re

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _type_ok(value, name):
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name in _TYPES:
        return isinstance(value, _TYPES[name])
    return False  # 未知类型名按不通过处理（防 schema 手误静默放行）


def validate(instance, schema, path="$"):
    """返回问题字符串列表；schema 为 {} 或无识别关键字时恒通过。"""
    problems = []
    t = schema.get("type")
    types = t if isinstance(t, list) else ([t] if t else [])
    if types and not any(_type_ok(instance, name) for name in types):
        problems.append(f"{path}: 类型应为 {t}，实际 {type(instance).__name__}")
        return problems  # 类型不符时后续关键字没有意义
    if "enum" in schema and instance not in schema["enum"]:
        problems.append(f"{path}: 取值 {instance!r} 不在枚举 {schema['enum']}")
    if (
        "pattern" in schema
        and isinstance(instance, str)
        and not re.search(schema["pattern"], instance)
    ):
        problems.append(f"{path}: {instance!r} 不匹配模式 {schema['pattern']}")
    if (
        "minItems" in schema
        and isinstance(instance, list)
        and len(instance) < schema["minItems"]
    ):
        problems.append(
            f"{path}: 条目数 {len(instance)} < minItems {schema['minItems']}"
        )
    if (
        "minLength" in schema
        and isinstance(instance, str)
        and len(instance) < schema["minLength"]
    ):
        problems.append(
            f"{path}: 长度 {len(instance)} < minLength {schema['minLength']}"
        )
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                problems.append(f"{path}: 缺少必填字段 {key!r}")
        props = schema.get("properties", {})
        for key, value in instance.items():
            if key in props:
                problems += validate(value, props[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                problems.append(
                    f"{path}: 多余字段 {key!r}（additionalProperties=false）"
                )
    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            problems += validate(item, schema["items"], f"{path}[{i}]")
    return problems
