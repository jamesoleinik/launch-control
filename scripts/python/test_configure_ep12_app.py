"""Offline tests for live-template transformations used by Episode 12."""

import unittest
from unittest.mock import Mock, patch
from xml.etree import ElementTree as ET

from configure_ep12_app import CLASS_IDS, matches, native_form, native_view, plan


class NativeSurfacesTests(unittest.TestCase):
    def setUp(self):
        self.form = (
            '<form><tabs><tab id="pcf"><labels><label description="Readiness" />'
            '</labels><columns><column><sections><section><rows><row><cell>'
            '<control id="pcf" datafieldname="lc_name" uniqueid="binding" />'
            '</cell></row></rows></section></sections></column></columns></tab>'
            '<tab id="general"><labels><label description="General" /></labels>'
            '<columns><column><sections><section><rows><row><cell id="owner">'
            '<labels><label description="Owner" /></labels>'
            f'<control id="ownerid" classid="{CLASS_IDS["Lookup"]}" datafieldname="ownerid" />'
            '</cell></row></rows></section></sections></column></columns></tab>'
            '</tabs><controlDescriptions><controlDescription forControl="binding" />'
            '</controlDescriptions></form>'
        )
        self.entry = {
            "table": "lc_task",
            "fields": {"lc_title": "Task title", "lc_isblocked": "Task is blocked"},
            "view_fields": ["lc_title", "lc_isblocked"],
            "sort_field": "lc_title",
        }
        self.columns = {
            "lc_title": {"AttributeType": "String"},
            "lc_isblocked": {"AttributeType": "Boolean"},
        }
        self.view = {
            "fetchxml": '<fetch savedqueryid="source"><entity name="lc_task">'
            '<attribute name="lc_taskid" /><attribute name="old" />'
            '<order attribute="old" /><filter type="and">'
            '<condition attribute="statecode" operator="eq" value="0" />'
            '</filter></entity></fetch>',
            "layoutxml": '<grid object="123" jump="lc_title"><row id="lc_taskid">'
            '<cell name="old" width="100" /></row></grid>',
        }

    def test_native_fields_first_and_pcf_preserved(self):
        root = ET.fromstring(native_form(self.form, self.entry, self.columns))
        tabs = root.findall("./tabs/tab")
        self.assertEqual([tab.get("id") for tab in tabs], ["general", "pcf"])
        self.assertEqual(
            [c.get("datafieldname") for c in tabs[0].findall(".//control")],
            ["lc_title", "lc_isblocked", "ownerid"],
        )
        before = ET.fromstring(self.form)
        self.assertEqual(ET.tostring(tabs[1]), ET.tostring(before.find("./tabs/tab")))
        self.assertEqual(
            ET.tostring(root.find("controlDescriptions")),
            ET.tostring(before.find("controlDescriptions")),
        )

    def test_form_is_idempotent(self):
        first = native_form(self.form, self.entry, self.columns)
        self.assertEqual(first, native_form(first, self.entry, self.columns))

    def test_missing_native_tab_fails(self):
        with self.assertRaisesRegex(RuntimeError, "native tab"):
            native_form("<form><tabs /></form>", self.entry, self.columns)

    def test_view_keeps_active_filter_and_primary_key(self):
        result = native_view(self.view, self.entry)
        fetch = ET.fromstring(result["fetchxml"])
        self.assertNotIn("savedqueryid", fetch.attrib)
        self.assertEqual(
            fetch.find("./entity/filter/condition").attrib,
            {"attribute": "statecode", "operator": "eq", "value": "0"},
        )
        self.assertEqual(
            [a.get("name") for a in fetch.findall("./entity/attribute")],
            ["lc_taskid", "lc_title", "lc_isblocked"],
        )
        self.assertEqual(ET.fromstring(result["layoutxml"]).get("object"), "123")
        self.assertEqual(result, native_view(result, self.entry))

    def test_update_sort_is_newest_first(self):
        result = native_view(self.view, {**self.entry, "sort_descending": True})
        self.assertEqual(
            ET.fromstring(result["fetchxml"]).find("./entity/order").get("descending"),
            "true",
        )

    def test_wrong_table_template_fails(self):
        with self.assertRaisesRegex(RuntimeError, "wrong table"):
            native_view(self.view, {**self.entry, "table": "lc_launch"})

    def test_server_view_id_does_not_force_update(self):
        body = native_view(self.view, self.entry)
        stored = {**body, "fetchxml": body["fetchxml"].replace("<fetch ", '<fetch savedqueryid="new" ')}
        self.assertTrue(matches(stored, body))
        stored["fetchxml"] = stored["fetchxml"].replace('value="0"', 'value="1"')
        self.assertFalse(matches(stored, body))

    def test_plan_preserves_live_source_presentation(self):
        client = Mock()
        client.tables.list_columns.return_value = [
            {"LogicalName": name, **metadata} for name, metadata in self.columns.items()
        ]
        entry = {
            **self.entry, "form": "Evidence", "view": "Active Evidence",
            "source_view": "Active tasks", "evidence_description": "Task evidence",
        }
        source = {"formxml": self.form, "formpresentation": 1, "formactivationstate": 1}
        current = {**source, "formpresentation": 0}
        with patch("configure_ep12_app.form", side_effect=[current, source]), \
                patch("configure_ep12_app.view", side_effect=[None, self.view]):
            changes = plan(client, {"navigation": [entry]})
        self.assertEqual(changes[0][4]["formpresentation"], 1)
        self.assertEqual(changes[0][4]["formactivationstate"], 1)


if __name__ == "__main__":
    unittest.main()
