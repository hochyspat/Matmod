"""Независимая проверка плана для serial_inventory_v1, без поиска оптимума."""
import math
from .io import validate_instance

STATUSES = {'optimal', 'feasible', 'infeasible_proven', 'no_solution_found', 'time_limit', 'error'}

def validate_plan(instance, plan):
    """Вернуть отчёт; некорректный формат вызывает ValueError.

    valid — допустимость действий, cost_matches — совпадение стоимости.
    При отсутствии плана valid=None: недопустимость задачи не доказывается.
    При первом физическом нарушении остановиться, не считать фиктивные затраты.
    """
    validate_instance(instance)
    if not isinstance(plan, dict):
        raise ValueError('План должен быть JSON-объектом')
    for key in ('schema_version', 'model_id', 'instance_id'):
        if plan.get(key) != instance[key]:
            raise ValueError(f'План и задача: не совпадает {key}')
    for key in ('algorithm', 'message'):
        if not isinstance(plan.get(key), str):
            raise ValueError(f'{key}: нужна строка')
    if not plan['algorithm']:
        raise ValueError('algorithm: нужна непустая строка')
    if not isinstance(plan.get('status'), str) or plan['status'] not in STATUSES:
        raise ValueError('Неизвестный status')
    if type(plan.get('has_plan')) is not bool:
        raise ValueError('has_plan: нужно логическое значение')
    if plan['status'] in ('optimal', 'feasible') and not plan['has_plan']:
        raise ValueError('optimal/feasible требуют наличия плана')
    if plan['status'] in ('infeasible_proven', 'no_solution_found') and plan['has_plan']:
        raise ValueError('Статус отсутствия решения несовместим с планом')
    for key in ('orders', 'transfers', 'reported_cost'):
        if key not in plan:
            raise ValueError(f'Не задано поле {key}')
    report = dict(instance_id=instance['instance_id'], valid=None, cost_matches=None,
                  accepted=None, violations=[], trace=[], recomputed_cost=None,
                  reported_cost=plan['reported_cost'], cost_difference=None,
                  optimality_checked=False, message='')
    if not plan['has_plan']:
        if any(plan[key] is not None for key in ('orders', 'transfers', 'reported_cost')):
            raise ValueError('При has_plan=false действия и стоимость должны быть null')
        report['message'] = 'Плана нет. Допустимость задачи и доказательство статуса не проверялись.'
        return report
    for key in ('orders', 'transfers'):
        values = plan[key]
        if not isinstance(values, list) or len(values) != instance['horizon']:
            raise ValueError(f'{key}: длина должна равняться horizon')
        if any(type(x) is not int or x < 0 for x in values):
            raise ValueError(f'{key}: нужны неотрицательные целые объёмы')
    value = plan['reported_cost']
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('reported_cost: нужно конечное неотрицательное число')

    def fail(code, period, message):
        report.update(valid=False, accepted=False, message=message)
        report['violations'].append(dict(code=code, period=period, message=message))
        return report

    w = instance['initial_inventory']['warehouse']
    r = instance['initial_inventory']['retailer']
    cw, cr = instance['capacity']['warehouse'], instance['capacity']['retailer']
    if w > cw or r > cr:
        return fail('initial_capacity', 0, 'Начальный запас превышает вместимость.')
    costs = instance['costs']
    for t, (q, x, d) in enumerate(zip(plan['orders'], plan['transfers'], instance['demand']), 1):
        row = dict(period=t, warehouse_start=w, retailer_start=r, order=q, transfer=x,
                   demand=d, warehouse_after_receipt=w+q, retailer_before_demand=None,
                   warehouse_end=None, retailer_end=None, ordering_cost=None,
                   holding_cost=None, period_cost=None)
        report['trace'].append(row)
        if w + q > cw:
            return fail('warehouse_capacity', t, 'После внешней поставки превышена вместимость склада.')
        if x > w + q:
            return fail('insufficient_warehouse_stock', t, 'Для перемещения не хватает товара на складе.')
        row['retailer_before_demand'] = r + x
        if r + x > cr:
            return fail('retailer_capacity', t, 'Перед выполнением спроса превышена вместимость магазина.')
        if r + x < d:
            return fail('shortage', t, 'Для выполнения спроса не хватает товара в магазине.')
        w, r = w + q - x, r + x - d
        ordering = (costs['order_warehouse'] if q > 0 else 0) + (costs['order_retailer'] if x > 0 else 0)
        holding = costs['hold_warehouse'] * w + costs['hold_retailer'] * r
        row.update(warehouse_end=w, retailer_end=r, ordering_cost=ordering,
                   holding_cost=holding, period_cost=ordering+holding)
    if (w, r) != (instance['terminal_inventory']['warehouse'], instance['terminal_inventory']['retailer']):
        return fail('terminal_inventory', instance['horizon'], 'Конечные запасы не совпадают с заданными.')
    total = math.fsum(row['period_cost'] for row in report['trace'])
    matches = math.isclose(total, plan['reported_cost'], rel_tol=1e-9, abs_tol=1e-9)
    report.update(valid=True, cost_matches=matches, accepted=matches,
                  recomputed_cost=total, cost_difference=plan['reported_cost']-total,
                  message='План допустим; стоимость подтверждена.' if matches else
                          'План допустим, но заявленная стоимость неверна.')
    return report
