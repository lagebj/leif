import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL_CASES_FILE = ROOT / "eval" / "eval_cases.jsonl"

sys.path.insert(0, str(ROOT / "scripts"))

from ask import load_system_prompt, load_embeddings, retrieve_context, build_user_prompt, chat  # noqa: E402


def load_eval_cases() -> list[dict]:
    if not EVAL_CASES_FILE.exists():
        raise FileNotFoundError(f"Eval cases file does not exist: {EVAL_CASES_FILE}")

    cases = []
    with EVAL_CASES_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))

    return cases


def main() -> None:
    system_prompt = load_system_prompt()
    rows = load_embeddings()
    cases = load_eval_cases()

    for case in cases:
        context_rows = retrieve_context(case["input"], rows, top_k=5)
        user_prompt = build_user_prompt(case["input"], context_rows)
        answer = chat(system_prompt, user_prompt)

        print("=" * 80)
        print(f"Case: {case['id']}")
        print(f"Task: {case['task']}")
        print(f"Input: {case['input']}")
        print(f"Expected traits: {', '.join(case['expected_traits'])}")
        print("\nRetrieved context:")
        for row in context_rows:
            print(f"- {row['source']} :: {row['id']}")
        print("\nAnswer:\n")
        print(answer)
        print()

    print("=" * 80)
    print(f"Completed {len(cases)} evaluation case(s)")


if __name__ == "__main__":
    main()
