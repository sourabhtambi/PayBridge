#!/usr/bin/env python3
"""
PayBridge Routing Verifier
Programmatic Claude Agent SDK usage to verify routing rules.
This script uses the Anthropic SDK to validate routing decisions.
"""

import anthropic
import json

ROUTING_RULES = {
    "UPI": {"min": 100, "max": 10_000_000},
    "IMPS": {"min": 10_000_001, "max": 20_000_000},
    "NEFT": {"min": 20_000_001, "max": 50_000_000},
    "RTGS": {"min": 50_000_001, "max": None},
}

TEST_CASES = [
    {"amount_paise": 100, "expected_rail": "UPI"},
    {"amount_paise": 10_000_000, "expected_rail": "UPI"},
    {"amount_paise": 10_000_001, "expected_rail": "IMPS"},
    {"amount_paise": 20_000_000, "expected_rail": "IMPS"},
    {"amount_paise": 20_000_001, "expected_rail": "NEFT"},
    {"amount_paise": 50_000_000, "expected_rail": "NEFT"},
    {"amount_paise": 50_000_001, "expected_rail": "RTGS"},
    {"amount_paise": 1_000_000_000, "expected_rail": "RTGS"},
]


def verify_routing_with_claude(test_cases: list) -> None:
    """Use Claude to verify routing decisions."""
    client = anthropic.Anthropic()

    prompt = f"""
    Verify these PayBridge routing decisions against the rules:
    
    Rules:
    {json.dumps(ROUTING_RULES, indent=2)}
    
    Test cases to verify:
    {json.dumps(test_cases, indent=2)}
    
    For each test case, confirm if the expected_rail is correct.
    Report any mismatches.
    """

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    print("Claude Routing Verification Report:")
    print("=" * 40)
    print(message.content[0].text)


if __name__ == "__main__":
    verify_routing_with_claude(TEST_CASES)
