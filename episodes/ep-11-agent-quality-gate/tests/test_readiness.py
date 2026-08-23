from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

EPISODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EPISODE_ROOT))

from agent.dataverse import LaunchResearch  # noqa: E402
from agent.quality_check import QualityResult  # noqa: E402
from agent.readiness import analyze_readiness  # noqa: E402

FORMATTED = "@OData.Community.Display.V1.FormattedValue"


class ReadinessTests(unittest.TestCase):
    def test_blockers_and_overdue_work_fail_readiness(self) -> None:
        research = LaunchResearch(
            launch={
                "lc_name": "Risky Launch",
                "lc_risksummary": "High: unresolved release blockers",
            },
            milestones=[{
                "lc_name": "Security review",
                "lc_milestonestatus" + FORMATTED: "Blocked",
                "lc_duedate": "2026-08-01T00:00:00Z",
            }],
            tasks=[{
                "lc_title": "Resolve P1",
                "lc_taskstatus" + FORMATTED: "Blocked",
                "lc_isblocked": True,
                "lc_blockerreason": "P1 authentication defect",
                "lc_duedate": "2026-08-01T00:00:00Z",
            }],
            status_updates=[{
                "lc_health" + FORMATTED: "Yellow",
                "lc_summary": "Mitigation is still in progress.",
            }],
        )
        browser = QualityResult("PASSED", 100, "Browser passed", "shot.png")
        with tempfile.TemporaryDirectory() as directory:
            result = analyze_readiness(
                research,
                browser,
                Path(directory),
                now=datetime(2026, 8, 18, tzinfo=timezone.utc),
            )
            self.assertEqual(result.outcome, "FAILED")
            self.assertLess(result.score, 60)
            self.assertTrue(Path(result.evidence).exists())

    def test_clean_evidence_passes_readiness(self) -> None:
        research = LaunchResearch(
            launch={"lc_name": "Ready Launch", "lc_risksummary": "Low"},
            milestones=[{
                "lc_name": "Release sign-off",
                "lc_milestonestatus" + FORMATTED: "Done",
                "lc_duedate": "2026-08-01T00:00:00Z",
            }],
            tasks=[{
                "lc_title": "Publish release",
                "lc_taskstatus" + FORMATTED: "Done",
                "lc_isblocked": False,
                "lc_duedate": "2026-08-01T00:00:00Z",
            }],
            status_updates=[{
                "lc_health" + FORMATTED: "Green",
                "lc_summary": "All release criteria are complete.",
            }],
        )
        browser = QualityResult("PASSED", 100, "Browser passed", "shot.png")
        with tempfile.TemporaryDirectory() as directory:
            result = analyze_readiness(
                research,
                browser,
                Path(directory),
                now=datetime(2026, 8, 18, tzinfo=timezone.utc),
            )
            self.assertEqual(result.outcome, "PASSED")
            self.assertEqual(result.score, 100)


if __name__ == "__main__":
    unittest.main()
