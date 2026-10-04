"""Просмотр задачи и независимая проверка готового расписания."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from src.io import load_instance
from src.validation import validate_plan

def main():
    parser = argparse.ArgumentParser(description='Просмотр задачи и проверка плана поставок')
    parser.add_argument('instance', type=Path)
    parser.add_argument('--plan', type=Path, help='JSON с готовым планом')
    parser.add_argument('--output', type=Path, help='Сохранить JSON-отчёт проверки')
    args = parser.parse_args()
    if args.output and not args.plan:
        parser.error('--output используется вместе с --plan')
    if args.output and args.output.resolve() in {args.instance.resolve(), args.plan.resolve()}:
        parser.error('Отчёт не должен перезаписывать входной файл')
    try:
        data = load_instance(args.instance)
        if not args.plan:
            print(f"Экземпляр: {data['instance_id']}")
            print(f"Модель: {data['model_id']} (рабочая версия)")
            print(f"Периоды: {data['horizon']}; спрос: {data['demand']}")
            print(f"Ёмкости: {data['capacity']}")
            print('Структура корректна. Допустимость расписания и оптимум не вычислялись.')
            return 0
        plan = json.loads(args.plan.read_text(encoding='utf-8'))
        report = validate_plan(data, plan)
        print(report['message'])
        if report['trace']:
            print('Период | Заказ | Передача | Склад в конце | Магазин в конце | Затраты')
            for row in report['trace']:
                def show(v):
                    return '—' if v is None else str(v)
                print(' | '.join(show(row[k]) for k in ('period','order','transfer','warehouse_end','retailer_end','period_cost')))
        if report['recomputed_cost'] is not None:
            print(f"Пересчитанная стоимость: {report['recomputed_cost']:g}")
            print(f"Заявленная стоимость: {report['reported_cost']:g}")
        for error in report['violations']:
            print(f"Период {error['period']}: {error['code']} — {error['message']}")
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
            print(f'Отчёт: {args.output}')
        return 0 if report['accepted'] is True else 1 if report['accepted'] is False else 3
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Ошибка входных данных или записи отчёта: {exc}\n')

if __name__ == '__main__':
    raise SystemExit(main())
