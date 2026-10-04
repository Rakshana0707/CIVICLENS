"""
Run promise normalization & categorization over extracted promise records.

Input : data/processed/manifestos/<year>/<party>/promises.jsonl
Output: data/processed/manifestos/<year>/<party>/normalized_promises.jsonl

No real manifestos have been collected yet, so this currently finds nothing.
TEST_FIXTURE records are refused here; they belong under data/tests/ only.
"""
import glob
import json
import logging
import os

from backend.nlp.promise_normalization import PromiseNormalizationService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DIR = "data/processed/manifestos"


def main():
    files = glob.glob(os.path.join(PROCESSED_DIR, "**", "promises.jsonl"), recursive=True)
    if not files:
        logger.info("No promise records found to normalize. Nothing to do.")
        return

    service = PromiseNormalizationService()
    for path in files:
        with open(path, encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]

        fixtures = [r for r in records if r.get("is_test_fixture")]
        if fixtures:
            logger.error(f"{path} contains TEST_FIXTURE records; refusing to write production output.")
            continue

        normalized = service.normalize_batch(records)
        out_path = os.path.join(os.path.dirname(path), "normalized_promises.jsonl")
        with open(out_path, "w", encoding="utf-8") as f:
            for n in normalized:
                f.write(json.dumps(n.to_dict(), ensure_ascii=False) + "\n")
        logger.info(f"{path}: {len(records)} promises -> {len(normalized)} normalized promises -> {out_path}")


if __name__ == "__main__":
    main()
