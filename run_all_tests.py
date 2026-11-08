"""
Master Test Runner for DistriDemand-LLM.
Executes all verification checkpoints sequentially and displays an end-to-end evaluation scorecard.
"""

import sys
import os
import time

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tests.test_broker import run_checkpoint_1
from tests.test_llm_agents import run_checkpoint_2
from tests.test_simulation import run_checkpoint_3


def main():
    print("\n" + "=" * 75)
    print("      DISTRIBUTED ANALYTICS: DISTRIDEMAND-LLM EVALUATION SUITE")
    print("=" * 75)
    print("Starting automated verification across all distributed layers...\n")

    results = {}
    start_time = time.time()

    # Checkpoint 1
    try:
        t0 = time.time()
        run_checkpoint_1()
        results["Checkpoint 1: Distributed Core & Message Broker"] = ("PASSED", f"{time.time() - t0:.2f}s")
    except Exception as e:
        results["Checkpoint 1: Distributed Core & Message Broker"] = ("FAILED", str(e))

    # Checkpoint 2
    try:
        t0 = time.time()
        run_checkpoint_2()
        results["Checkpoint 2: LLM Multi-Agent Reasoning Engine"] = ("PASSED", f"{time.time() - t0:.2f}s")
    except Exception as e:
        results["Checkpoint 2: LLM Multi-Agent Reasoning Engine"] = ("FAILED", str(e))

    # Checkpoint 3
    try:
        t0 = time.time()
        run_checkpoint_3()
        results["Checkpoint 3: Simulation Engine & Rebalancing"] = ("PASSED", f"{time.time() - t0:.2f}s")
    except Exception as e:
        results["Checkpoint 3: Simulation Engine & Rebalancing"] = ("FAILED", str(e))

    total_duration = time.time() - start_time

    # Print Summary Scorecard
    print("\n" + "=" * 75)
    print("                      FINAL VERIFICATION SCORECARD")
    print("=" * 75)
    all_passed = True
    for checkpoint, (status, detail) in results.items():
        symbol = "✅" if status == "PASSED" else "❌"
        if status != "PASSED":
            all_passed = False
        print(f" {symbol} {checkpoint:<52} : {status:<8} ({detail})")

    print("-" * 75)
    print(f" Total Verification Runtime: {total_duration:.2f} seconds")
    if all_passed:
        print(" 🎉 OVERALL STATUS: ALL CHECKPOINTS PASSED - SYSTEM IS PRODUCTION & DEMO READY!")
    else:
        print(" ⚠️ OVERALL STATUS: SOME CHECKPOINTS FAILED - REVIEW LOGS ABOVE.")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()

