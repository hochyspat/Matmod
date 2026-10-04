"""Проверка структуры входа; не проверяет существование допустимого плана."""
import json
import math
from pathlib import Path

def load_instance(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_instance(data)

def validate_instance(data):
    """Проверить структуру объекта задачи без решения самой задачи."""
    if not isinstance(data, dict):
        raise ValueError("Корень JSON должен быть объектом")
    for name in ("schema_version", "model_id", "instance_id", "horizon", "demand", "capacity", "initial_inventory", "terminal_inventory", "costs"):
        if name not in data:
            raise ValueError(f"Не задано поле {name}")
    if data["schema_version"] != "1.0" or data["model_id"] != "serial_inventory_v1":
        raise ValueError("Неподдерживаемая версия формата или модели")
    if not isinstance(data["instance_id"], str) or not data["instance_id"]:
        raise ValueError("instance_id должен быть непустой строкой")
    def integer(value, label, minimum=0):
        if type(value) is not int or value < minimum:
            raise ValueError(f"{label}: нужно целое число >= {minimum}")
    integer(data["horizon"], "horizon", 1)
    if not isinstance(data["demand"], list) or len(data["demand"]) != data["horizon"]:
        raise ValueError("Длина demand должна равняться horizon")
    for i, value in enumerate(data["demand"]):
        integer(value, f"demand[{i}]")
    for section in ("capacity", "initial_inventory", "terminal_inventory"):
        if not isinstance(data[section], dict):
            raise ValueError(f"{section}: нужен объект")
        for node in ("warehouse", "retailer"):
            integer(data[section].get(node), f"{section}.{node}")
    if not isinstance(data["costs"], dict):
        raise ValueError("costs: нужен объект")
    for key in ("order_warehouse", "order_retailer", "hold_warehouse", "hold_retailer"):
        value = data["costs"].get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError(f"costs.{key}: нужно конечное число >= 0")
    return data
