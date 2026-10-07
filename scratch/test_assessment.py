import json
import backend.database.base
from backend.database.session import SessionLocal
from backend.services.promise_assessment_engine import PromiseAssessmentEngine
from backend.models.promise import PoliticalPromise

db = SessionLocal()
engine = PromiseAssessmentEngine(db_session=db)

promises = db.query(PoliticalPromise).filter(PoliticalPromise.is_test_fixture == False).all()
print(f"Retrieved {len(promises)} real promises for assessment.")

status_counts = {}
for p in promises:
    res = engine.evaluate_promise(p, persist=False)
    st = res["status"]
    status_counts[st] = status_counts.get(st, 0) + 1

print("\n--- TEST ASSESSMENT STATUS BREAKDOWN ---")
for k, v in status_counts.items():
    print(f"  {k:<25}: {v} ({v/len(promises)*100:.1f}%)")
