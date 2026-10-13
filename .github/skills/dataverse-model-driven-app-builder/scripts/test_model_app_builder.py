import contextlib
import io
import unittest
from unittest.mock import Mock, patch

import model_app_builder as builder


class TableComponentTests(unittest.TestCase):
    def setUp(self):
        self.spec = {
            "name": "Demo",
            "unique_name": "demo_App",
            "description": "Demo app",
            "solution": "Demo",
            "navigation": [{"table": "demo_launch"}],
        }
        self.app = {
            "appmoduleid": "app-id",
            "appmoduleidunique": "app-unique-id",
            "name": "Demo",
            "description": "Demo app",
            "publishedon": "2026-01-01",
        }
        self.site_map = {
            "sitemapid": "map-id",
            "sitemapxml": builder.sitemap_xml(self.spec),
        }
        self.resolved = (
            self.app, self.site_map, {"solutionid": "solution-id"},
            {"demo_launch": "launch-metadata-id"}, {}, {}, {},
        )

    def test_add_uses_table_type_and_resolved_primary_key(self):
        dv = Mock()
        dv.request.return_value.json.return_value = {
            "PrimaryIdAttribute": "demo_customprimarykey"
        }
        with (
            patch.object(builder, "resolve", return_value=self.resolved),
            patch.object(builder, "resolve_icon", return_value="icon-id"),
            patch.object(builder, "ensure_solution_component"),
        ):
            builder.apply(dv, self.spec)
            builder.apply(dv, self.spec)
        additions = [
            call.kwargs["body"]["Components"]
            for call in dv.request.call_args_list
            if call.args == ("POST", "AddAppComponents")
        ]
        expected = [
            {"@odata.id": "sitemaps(map-id)"},
            {
                "@odata.type": "Microsoft.Dynamics.CRM.demo_launch",
                "demo_customprimarykey": "launch-metadata-id",
            },
        ]
        self.assertEqual(additions, [expected, expected])
        dv.request.assert_any_call(
            "GET",
            "EntityDefinitions(launch-metadata-id)?$select=PrimaryIdAttribute",
        )

    def verify_tables(self, table_ids):
        dv = Mock()
        dv.rows.side_effect = [
            [
                {"objectid": "map-id", "componenttype": 62},
                *[
                    {"objectid": value, "componenttype": 1}
                    for value in table_ids
                ],
            ],
            [
                {"objectid": "app-id", "componenttype": 80},
                {"objectid": "map-id", "componenttype": 62},
            ],
        ]
        with (
            patch.object(builder, "resolve", return_value=self.resolved),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            return builder.verify(dv, self.spec)

    def test_rejects_wrong_table_even_when_count_matches(self):
        self.assertFalse(self.verify_tables(["generic-entity-metadata-id"]))

    def test_accepts_exact_table_metadata_id_case_insensitively(self):
        self.assertTrue(self.verify_tables(["LAUNCH-METADATA-ID"]))

    def test_rejects_extra_table(self):
        self.assertFalse(
            self.verify_tables(["launch-metadata-id", "generic-entity-metadata-id"])
        )

    def test_rejects_missing_table(self):
        self.assertFalse(self.verify_tables([]))


if __name__ == "__main__":
    unittest.main()
