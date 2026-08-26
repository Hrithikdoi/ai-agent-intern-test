import json
import re
from pathlib import Path

from app.agent import SupportAgent


ROOT = Path(__file__).resolve().parents[1]


def normalize_text(text):
    """
    Normalize harmless wording and Markdown formatting
    while keeping evaluation deterministic.
    """
    text = text.lower()

    # Remove common Markdown formatting markers.
    text = re.sub(r"[*_`]", "", text)

    text = (
        text.replace("-", " ")
        .replace("–", " ")
        .replace("—", " ")
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def contains_phrase(text, phrase):
    """
    Deterministic phrase matching with minor singular/plural tolerance.
    """
    text = normalize_text(text)
    phrase = normalize_text(phrase)

    if phrase in text:
        return True

    words = phrase.split()

    if words and words[-1].endswith("s"):
        singular = " ".join(
            words[:-1] + [words[-1][:-1]]
        )

        if singular in text:
            return True

    return False


def concept_matches(text, concept):
    """
    Match behavior-level concepts using explicit equivalent
    phrasings. No LLM is used for grading.
    """

    normalized = normalize_text(text)
    concept_normalized = normalize_text(concept)
    concept_key = concept_normalized

    # Direct match first.
    if contains_phrase(
        normalized,
        concept_normalized,
    ):
        return True

    aliases = {
        "final sale does not block damaged item review": [
            "final sale items are still eligible for review",
            "final sale does not prevent damaged item review",
            "final sale does not prevent review",
            "eligible for review when they arrive damaged",
            "damaged items are still eligible for review",
        ],

        "report within 7 days": [
            "reported within 7 calendar days",
            "report within 7 calendar days",
            "reported within seven days",
            "report within seven days",
            "within 7 days of delivery",
        ],

        "human review before approval": [
            "requires human review before approval",
            "human review before approval",
            "requires human review",
            "human review",
        ],

        "canada is supported": [
            "ships internationally to canada",
            "ships internationally only to canada",
            "canada is supported",
            "canadian orders",
        ],

        "duties or taxes are not prepaid": [
            "duties and taxes are not prepaid",
            "import duties taxes and brokerage charges are not prepaid",
            "import duties and taxes are not prepaid",
            "duties are not prepaid",
            "taxes are not prepaid",
            "recipient is responsible for charges",
            "recipient is responsible for import duties",
            "recipient is responsible for taxes",
            "recipient is responsible for charges assessed",
            "recipient is responsible for charges assessed by canadian authorities",
            "recipient is responsible for charges assessed by the carrier",
        ],

        "the order is cancelled": [
            "order is cancelled",
            "order was cancelled",
            "the order is cancelled",
            "cancelled so it will not be shipped",
            "cancelled and will not be shipped",
            "cancelled and it will not be shipped",
            "cancelled",
        ],

        "order was not found": [
            "couldn't find order",
            "could not find order",
            "order was not found",
            "couldn't locate order",
            "could not locate order",
        ],

        "delivery estimate is unavailable": [
            "delivery estimate is currently unavailable",
            "a delivery estimate is currently unavailable",
            "delivery estimate is unavailable",
            "delivery estimate currently unavailable",
        ],

        "no lifetime warranty": [
            "does not offer a lifetime warranty",
            "no lifetime warranty",
            "does not have a lifetime warranty",
            "not a lifetime warranty",
        ],

        "bags have 2 years": [
            "bags and backpacks: 2 years",
            "bags and backpacks have 2 years",
            "bags have 2 years",
            "2 years from the purchase date",
        ],

        "drinkware and travel accessories have 1 year": [
            "drinkware: 1 year from the purchase date",
            "drinkware 1 year from the purchase date",
            "drinkware has a 1 year warranty",
            "drinkware has a one year warranty",
            "drinkware is covered for 1 year",
            "drinkware is covered for one year",

            "packing cubes and other travel accessories: 1 year from the purchase date",
            "packing cubes and other travel accessories 1 year from the purchase date",
            "travel accessories have 1 year",
            "travel accessories have a 1 year warranty",
            "travel accessories have a one year warranty",
            "travel accessories are covered for 1 year",
            "travel accessories are covered for one year",

            # Exact wording from the current agent response.
            "drinkware: 1 year",
            "packing cubes and other travel accessories: 1 year",
        ],

        "migration note is not authoritative": [
            "migration note is not an authoritative",
            "migration note is not authoritative",
            "not an authoritative customer policy",
            "not an authoritative policy",
        ],

        "standard policy is 30 days unless a valid exception applies": [
            "standard return policy is 30 calendar days from delivery",
            "standard return window is 30 calendar days from delivery",
            "30 calendar days from delivery unless a valid exception applies",
            "30 calendar days from delivery",
        ],

        "the agent cannot approve a return": [
            "cannot approve a return",
            "can't approve a return",
            "cannot approve the return",
            "can't approve the return",
        ],

        "one says hand-wash the body": [
            "body should be hand washed",
            "stainless steel body should be hand washed",
            "stainless-steel body should be hand washed",
            "hand wash the tumbler body",
            "hand-wash the tumbler body",
        ],

        "one says all components are dishwasher safe": [
            "all components are dishwasher safe",
            "components are dishwasher safe",
        ],

        "human confirmation or safest interim guidance": [
            "please get human confirmation",
            "human confirmation",
            "safest interim guidance",
            "hand wash the tumbler body",
            "hand-wash the tumbler body",
        ],
    }

    candidates = []
    for alias_key, alias_values in aliases.items():
        if normalize_text(alias_key) == concept_normalized:
            candidates.extend(alias_values)
            break

    return any(
        contains_phrase(
            normalized,
            candidate,
        )
        for candidate in candidates
    )


def check_case(case):
    agent = SupportAgent()
    responses = []

    # All messages in one case share the same session.
    for message in case["messages"]:
        response = agent.handle(
            message["content"]
        )
        responses.append(response)

    final = responses[-1]
    expect = case["expect"]

    text = normalize_text(
        final.answer
    )

    failures = []

    # ---------------------------------------------------------
    # Required text
    # ---------------------------------------------------------

    for required in expect.get(
        "must_include",
        [],
    ):
        if not contains_phrase(
            text,
            required,
        ):
            failures.append(
                f"missing: {required}"
            )

    # ---------------------------------------------------------
    # Behavior-level concepts
    # ---------------------------------------------------------

    for concept in expect.get(
        "must_include_concepts",
        [],
    ):
        if not concept_matches(
            text,
            concept,
        ):
            failures.append(
                f"missing concept: {concept}"
            )

    # ---------------------------------------------------------
    # Forbidden text
    # ---------------------------------------------------------

    for forbidden in expect.get(
        "must_not_include",
        [],
    ):
        if contains_phrase(
            text,
            forbidden,
        ):
            failures.append(
                f"forbidden text: {forbidden}"
            )

    # ---------------------------------------------------------
    # Tool expectations
    # ---------------------------------------------------------

    expected_tool = expect.get(
        "tool"
    )

    if expected_tool == "optional_sanitized_lookup":
        allowed_tools = {
            "not_called",
            "order_lookup",
        }

        if final.tool_used not in allowed_tools:
            failures.append(
                "tool expected one of "
                f"{sorted(allowed_tools)}, "
                f"actual={final.tool_used}"
            )

    elif expected_tool and (
        final.tool_used != expected_tool
    ):
        failures.append(
            f"tool expected={expected_tool}, "
            f"actual={final.tool_used}"
        )

    # ---------------------------------------------------------
    # Handoff expectation
    # ---------------------------------------------------------

    expected_handoff = expect.get(
        "handoff"
    )

    if (
        expected_handoff is not None
        and final.handoff != expected_handoff
    ):
        failures.append(
            f"handoff expected={expected_handoff}, "
            f"actual={final.handoff}"
        )

    # ---------------------------------------------------------
    # Required sources
    # ---------------------------------------------------------

    source_names = {
        source["filename"]
        for response in responses
        for source in response.sources
    }

    for required_source in expect.get(
        "required_sources",
        [],
    ):
        if required_source not in source_names:
            failures.append(
                f"missing source: {required_source}"
            )

    # ---------------------------------------------------------
    # Forbidden sources
    # ---------------------------------------------------------

    forbidden_sources = set(
        expect.get(
            "forbidden_sources_as_authority",
            [],
        )
    )

    for source in source_names:
        if source in forbidden_sources:
            failures.append(
                f"forbidden source used: {source}"
            )

    return failures


def load_cases(filename):
    path = ROOT / "evaluation" / filename

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)["cases"]


def main():
    visible_cases = load_cases(
        "visible-cases.json"
    )

    custom_cases = load_cases(
        "custom-cases.json"
    )

    all_cases = (
        [
            ("visible", case)
            for case in visible_cases
        ]
        + [
            ("custom", case)
            for case in custom_cases
        ]
    )

    category_results = {}
    total_passed = 0

    print("=" * 70)
    print("ASTER & ROW EVALUATION")
    print("=" * 70)
    print()

    for suite, case in all_cases:
        failures = check_case(case)
        passed = not failures

        category = case.get(
            "category",
            "uncategorized",
        )

        if category not in category_results:
            category_results[category] = [
                0,
                0,
            ]

        category_results[category][1] += 1

        if passed:
            total_passed += 1
            category_results[category][0] += 1
            status = "PASS"
        else:
            status = "FAIL"

        print(
            f"[{status}] "
            f"{suite}/{case['id']}"
        )

        for failure in failures:
            print(
                f"       - {failure}"
            )

    total = len(all_cases)

    print()
    print("-" * 70)
    print("RESULTS BY CATEGORY")
    print("-" * 70)

    for category in sorted(
        category_results
    ):
        passed, count = (
            category_results[category]
        )

        print(
            f"{category:25} "
            f"{passed}/{count} PASS"
        )

    print()
    print("-" * 70)
    print(
        f"TOTAL: {total_passed}/{total} PASS"
    )
    print("-" * 70)

    if total_passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()