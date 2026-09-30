import os, sys, json
sys.path.insert(0, os.path.abspath('.'))
from backend.database.session import SessionLocal
from backend.models.budget import BudgetRecord, BudgetScheme, BudgetDepartment

db = SessionLocal()

# 1. Get all schemes that received a budget_estimate in 2026-27
new_year_records = db.query(BudgetRecord).filter(
    BudgetRecord.financial_year == '2026-27', 
    BudgetRecord.budget_stage == 'budget_estimate',
    BudgetRecord.amount > 0
).all()

# 2. Get all historical schemes prior to 2026
old_records = db.query(BudgetRecord).filter(
    BudgetRecord.financial_year.in_(['2019-20', '2020-21', '2021-22', '2022-23', '2023-24', '2024-25', '2025-26'])
).all()
old_scheme_ids = {r.scheme_id for r in old_records}

# 3. Filter to ONLY entirely new schemes
truly_new_schemes = {}
for r in new_year_records:
    if r.scheme_id not in old_scheme_ids:
        if r.scheme_id not in truly_new_schemes:
            truly_new_schemes[r.scheme_id] = {
                'name': r.scheme.name,
                'department': r.scheme.department.name,
                'be_amount': 0
            }
        truly_new_schemes[r.scheme_id]['be_amount'] += r.amount

# Sort by highest budget allocation to find the most significant new schemes
sorted_new = sorted(truly_new_schemes.values(), key=lambda x: x['be_amount'], reverse=True)

print("Top 5 New Schemes for 2026-2027:")
for s in sorted_new[:5]:
    print(f"- {s['name']} (Dept: {s['department']}) | Budget: {s['be_amount']}")
