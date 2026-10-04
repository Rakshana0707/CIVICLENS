"""
Run promise extraction over extracted manifesto segments.

Input : data/processed/manifestos/<year>/<party>/extracted_segments.jsonl
Output: data/processed/manifestos/<year>/<party>/promises.jsonl

No real manifestos have been collected yet, so this currently finds nothing.
TEST_FIXTURE records are refused here; they belong under data/tests/ only.
"""
import glob
import json
import logging
import os

from backend.nlp.promise_extraction import PromiseExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DIR = "data/processed/manifestos"


def main():
    files = glob.glob(os.path.join(PROCESSED_DIR, "**", "extracted_segments.jsonl"), recursive=True)
    if not files:
        logger.info("No extracted manifesto segments found. Nothing to do.")
        return

    extractor = PromiseExtractor()
    for path in files:
        with open(path, encoding="utf-8") as f:
            segments = [json.loads(line) for line in f if line.strip()]

        records = extractor.extract(segments)
        fixtures = [r for r in records if r.is_test_fixture]
        if fixtures:
            logger.error(f"{path} contains TEST_FIXTURE records; refusing to write production output.")
            continue

        out_path = os.path.join(os.path.dirname(path), "promises.jsonl")
        with open(out_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
        logger.info(f"{path}: {len(segments)} segments -> {len(records)} promise candidates -> {out_path}")


if __name__ == "__main__":
    main()
