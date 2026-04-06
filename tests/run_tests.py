"""
Test runner for simple_camera_manager with a formatted output overview.

Usage:
    python3.12 tests/run_tests.py
"""

import sys
import time
import unittest
from pathlib import Path

# ── ANSI colours ─────────────────────────────────────────────────────────────
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

PASS_MARK = f"{GREEN}✓{RESET}"
FAIL_MARK = f"{RED}✗{RESET}"
ERROR_MARK = f"{YELLOW}!{RESET}"


class GroupedResult(unittest.TestResult):
    """Collect results grouped by TestCase class for a structured overview."""

    def __init__(self):
        super().__init__()
        self.results: dict[str, list[tuple[str, str, str | None]]] = {}
        # (method_name, status, detail)
        self._start_times: dict[str, float] = {}

    def _group(self, test) -> str:
        return type(test).__name__

    def startTest(self, test):
        super().startTest(test)
        self._start_times[test.id()] = time.perf_counter()
        self.results.setdefault(self._group(test), [])

    def _elapsed(self, test) -> str:
        ms = (time.perf_counter() - self._start_times.get(test.id(), 0)) * 1000
        return f"{ms:.1f} ms"

    def addSuccess(self, test):
        super().addSuccess(test)
        self.results[self._group(test)].append(
            (test._testMethodName, "pass", self._elapsed(test))
        )

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.results[self._group(test)].append(
            (test._testMethodName, "fail", self._formatErr(err))
        )

    def addError(self, test, err):
        super().addError(test, err)
        self.results[self._group(test)].append(
            (test._testMethodName, "error", self._formatErr(err))
        )

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.results[self._group(test)].append(
            (test._testMethodName, "skip", reason)
        )

    @staticmethod
    def _formatErr(err) -> str:
        import traceback
        return "".join(traceback.format_exception(*err)).strip()


# ── Friendly method-name formatting ──────────────────────────────────────────

def _friendly(method_name: str) -> str:
    """'test_register_order' → 'register order'"""
    return method_name.removeprefix("test_").replace("_", " ")


# ── Friendly class-name → section header ─────────────────────────────────────

_SECTION_LABELS = {
    "TestRegister":                "register()",
    "TestUnregister":              "unregister()",
    "TestRegisterUnregisterCycle": "register() → unregister() cycle",
    "TestReload":                  "Addon reload (bpy already in namespace)",
}


def _section_label(class_name: str) -> str:
    return _SECTION_LABELS.get(class_name, class_name)


# ── Printer ───────────────────────────────────────────────────────────────────

def _print_report(result: GroupedResult, elapsed_total: float):
    width = 70
    print()
    print(f"{BOLD}{'━' * width}{RESET}")
    print(f"{BOLD}  simple_camera_manager – Registration Tests{RESET}")
    print(f"{BOLD}{'━' * width}{RESET}")

    totals = {"pass": 0, "fail": 0, "error": 0, "skip": 0}

    for class_name, entries in result.results.items():
        label = _section_label(class_name)
        group_pass = sum(1 for _, s, _ in entries if s == "pass")
        group_total = len(entries)
        status_badge = (
            f"{GREEN}{group_pass}/{group_total}{RESET}"
            if group_pass == group_total
            else f"{RED}{group_pass}/{group_total}{RESET}"
        )
        print(f"\n  {BOLD}{CYAN}{label}{RESET}  {DIM}({status_badge}{DIM}){RESET}")
        print(f"  {'─' * (width - 2)}")

        for method_name, status, detail in entries:
            if status == "pass":
                mark = PASS_MARK
                totals["pass"] += 1
            elif status == "fail":
                mark = FAIL_MARK
                totals["fail"] += 1
            elif status == "error":
                mark = ERROR_MARK
                totals["error"] += 1
            else:
                mark = f"{YELLOW}–{RESET}"
                totals["skip"] += 1

            label_text = _friendly(method_name)
            # Right-align timing if it's a pass (detail holds elapsed string)
            if status == "pass" and detail:
                timing = f"{DIM}{detail}{RESET}"
                pad = width - 6 - len(label_text) - len(detail)
                print(f"  {mark}  {label_text}{' ' * max(pad, 1)}{timing}")
            else:
                print(f"  {mark}  {label_text}")
                if detail and status in ("fail", "error"):
                    for line in detail.splitlines():
                        print(f"       {RED}{line}{RESET}")

    # ── Summary bar ──────────────────────────────────────────────────────────
    print()
    print(f"  {'─' * (width - 2)}")
    total = sum(totals.values())
    passed = totals["pass"]
    failed = totals["fail"] + totals["error"]

    if failed == 0:
        outcome = f"{GREEN}{BOLD}ALL {passed} TESTS PASSED{RESET}"
    else:
        outcome = f"{RED}{BOLD}{failed} FAILED  |  {passed} passed{RESET}"

    skipped = f"  {YELLOW}{totals['skip']} skipped{RESET}" if totals["skip"] else ""
    elapsed_str = f"{elapsed_total * 1000:.0f} ms"
    print(f"  {outcome}{skipped}  {DIM}({elapsed_str}){RESET}")
    print(f"{BOLD}{'━' * width}{RESET}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=str(Path(__file__).parent),
        pattern="test_*.py",
    )

    result = GroupedResult()
    t0 = time.perf_counter()
    suite.run(result)
    elapsed = time.perf_counter() - t0

    _print_report(result, elapsed)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
