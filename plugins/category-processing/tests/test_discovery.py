"""Verify structural gap discovery retains complete evidence and exact boundaries."""

from copy import deepcopy

from category_processing.archive import pointer_value
from category_processing.discovery import discover_fields, discovery_policy


class RawFieldDiscoveryTests:
    def capture(self, information=None):
        return {
            "capture_id": "capture-fixture",
            "information": {"duplicate_capture_information": "Do not rediscover this."},
            "source_artifacts": [{"status": "saved", "sha256": "checksum"}],
            "images": [{"status": "saved"}],
            "source_catalogs": [{"status": "saved"}],
            "raw_record": {
                "product_id": "fixture-product", "source_key": "fixture-seller",
                "source_url": "https://fixture.example.test/product",
                "identity": {"name": "Fixture entity", "brand": "Fixture brand",
                             "source_product_id": "source-product", "source_variant_id": "source-variant"},
                "information": {} if information is None else information,
                "source_artifacts": [{"kind": "page", "content": "Raw artifact content"}],
                "images": [{"alt": "Source image"}],
                "source_catalog": {"status": "supplied"},
                "source_catalogs": [{"url": "https://fixture.example.test/catalog"}],
                "collection_notes": ["Capture metadata"],
            },
        }

    def fields(self, capture, recipe=None, handled=()):
        return discover_fields(capture, recipe or {}, handled)

    def test_default_excludes_only_known_control_paths_and_capture_envelope(self):
        capture = self.capture()
        capture["raw_record"].update(
            status="preorder", metadata={"care": "wipe clean"},
            id="Business-specific ID", custom_entity={"source_url": "Business evidence"},
        )
        rows = self.fields(capture)
        assert ([row["field_pointer"] for row in rows]) == ([
            "/raw_record/custom_entity", "/raw_record/id", "/raw_record/metadata", "/raw_record/status",
        ])
        assert (rows[0]["raw_value"]) == ({"source_url": "Business evidence"})
        assert (discovery_policy({})["roots"]) == (["/raw_record"])

    def test_wholly_unhandled_object_preserves_internal_relationships_and_nulls(self):
        original = {"new_measure": {"value": 12.5, "unit": "cm", "qualifier": None,
                                    "components": [None, {"name": "Original material", "share": 0}]}}
        capture = self.capture(original)
        rows = self.fields(capture)
        assert (rows) == ([{"field_pointer": "/raw_record/information",
                                 "raw_value": original, "value_type": "object"}])
        rows[0]["raw_value"]["new_measure"]["value"] = 999
        assert (capture["raw_record"]["information"]["new_measure"]["value"]) == (12.5)

    def test_partial_handling_recurses_only_into_unhandled_siblings(self):
        capture = self.capture({"known": "mapped", "properties": {
            "known": 1, "new": {"value": 0, "unit": "source unit", "basis": None},
        }, "new_array": [None, False, {"source_text": "Original wording"}]})
        handled = ("/raw_record/information/known", "/raw_record/information/properties/known")
        rows = self.fields(capture, handled=handled)
        assert ([row["field_pointer"] for row in rows]) == ([
            "/raw_record/information/new_array", "/raw_record/information/properties/new",
        ])
        assert (rows[0]["value_type"]) == ("array")
        assert (rows[0]["raw_value"]) == ([None, False, {"source_text": "Original wording"}])
        assert rows[1]["raw_value"]["basis"] is None

    def test_array_partial_handling_retains_unhandled_element_and_siblings(self):
        capture = self.capture({"sections": [
            {"known": "used", "unfamiliar": "New source fact"},
            {"heading": "Unrecognized section", "text": "Complete original section"},
        ]})
        rows = self.fields(capture, handled=("/raw_record/information/sections/0/known",))
        assert ([row["field_pointer"] for row in rows]) == ([
            "/raw_record/information/sections/0/unfamiliar", "/raw_record/information/sections/1",
        ])
        assert (rows[1]["raw_value"]) == (capture["raw_record"]["information"]["sections"][1])

    def test_configured_fields_skip_values_price_context_and_section_children_are_covered(self):
        capture = self.capture({
            "title": "Default Title", "weight": 250,
            "existing": {"recognized": "source value", "unknown_child": {"source_value": 3}},
            "price": {"amount": 4.99, "currency": "GBP", "observed_at": "source time", "new_context": "New basis"},
            "outside_sections": {"new_fact": "Preserve this."},
        })
        recipe = {
            "fields": [{"attribute": "identity.variant_name", "pointer": "/raw_record/information/title",
                        "skip_values": ["Default Title"]},
                       {"attribute": "quantity.mass", "pointer": "/raw_record/information/weight"}],
            "sections": {"/raw_record/information/existing": "existing"},
            "price": {"amount_pointer": "/raw_record/information/price/amount",
                      "currency_pointer": "/raw_record/information/price/currency",
                      "observed_at_pointer": "/raw_record/information/price/observed_at", "price_unit": "major"},
        }
        rows = self.fields(capture, recipe)
        assert ([row["field_pointer"] for row in rows]) == ([
            "/raw_record/information/outside_sections", "/raw_record/information/price/new_context",
        ])

    def test_malformed_configured_section_is_discovered_after_extraction_failure(self):
        capture = self.capture({"known": "used", "existing": ["Unexpected section format"]})
        recipe = {"fields": [{"attribute": "known", "pointer": "/raw_record/information/known"}],
                  "sections": {"/raw_record/information/existing": "existing"}}
        rows = self.fields(capture, recipe)
        assert (rows) == ([{"field_pointer": "/raw_record/information/existing",
                                 "raw_value": ["Unexpected section format"], "value_type": "array"}])

    def test_absent_configured_descendant_does_not_split_wholly_unhandled_subtree(self):
        capture = self.capture({"new": {"source_value": 3, "basis": None}})
        recipe = {"fields": [{"attribute": "known", "pointer": "/raw_record/information/absent"}]}
        rows = self.fields(capture, recipe)
        assert ([row["field_pointer"] for row in rows]) == (["/raw_record/information"])

    def test_null_and_empty_missingness_is_omitted_but_zero_and_false_are_exact(self):
        capture = self.capture({"known": "used", "null": None, "empty_text": "", "empty_list": [],
                                "empty_object": {}, "only_missing": {"x": [None, "", {}, []]},
                                "zero": 0, "false": False, "decimal_zero": 0.0})
        rows = self.fields(capture, handled=("/raw_record/information/known",))
        assert ({row["field_pointer"].rsplit("/", 1)[1]: (row["raw_value"], row["value_type"])
                          for row in rows}) == ({
                              "zero": (0, "integer"), "false": (False, "boolean"), "decimal_zero": (0.0, "number"),
                          })
        assert (self.fields(self.capture({"only_missing": [None, {}, ""]}))) == ([])

    def test_unicode_and_escaped_key_pointers_resolve_without_rewriting_evidence(self):
        capture = self.capture({"used": "mapped", "材料/声明~原文": "实木", "a": "A", "a/b": "B"})
        before = deepcopy(capture)
        rows = self.fields(capture, handled=("/raw_record/information/used", "/raw_record/information/a"))
        assert ([row["field_pointer"] for row in rows]) == ([
            "/raw_record/information/a~1b", "/raw_record/information/材料~1声明~0原文",
        ])
        for row in rows:
            assert (pointer_value(capture, row["field_pointer"])) == (row["raw_value"])
        assert (capture) == (before)

    def test_explicit_policy_narrows_roots_and_adds_exact_ignore_paths(self):
        capture = self.capture({"status": "Business status", "group": {"new": "Source fact", "ignored": "Context"},
                                "outside": "Outside selected boundary"})
        recipe = {"discovery": {"roots": ["/raw_record/information/group", "/raw_record/information/group/new"],
                                "ignore_pointers": ["/raw_record/information/group/ignored"]}}
        policy = discovery_policy(recipe)
        assert (policy["roots"]) == (["/raw_record/information/group"])
        assert ("/raw_record/source_artifacts") in (policy["ignore_pointers"])
        rows = self.fields(capture, recipe)
        assert (rows) == ([{"field_pointer": "/raw_record/information/group/new",
                                 "raw_value": "Source fact", "value_type": "string"}])
        assert (self.fields(capture, {"discovery": {"enabled": False}})) == ([])

    def test_handled_pointer_boundaries_do_not_suppress_similar_key_names(self):
        capture = self.capture({"part": "Known", "partial": "New", "nested": {"known": "Known", "new": "New"}})
        rows = self.fields(capture, handled=("/raw_record/information/part", "/raw_record/information/nested"))
        assert (rows) == ([{"field_pointer": "/raw_record/information/partial",
                                 "raw_value": "New", "value_type": "string"}])

    def test_overlapping_roots_and_reordered_inputs_produce_identical_candidates(self):
        capture = self.capture({"b": {"y": "Y", "x": "X"}, "a": "A"})
        recipe = {"discovery": {"roots": ["/raw_record/information/b", "/raw_record/information",
                                           "/raw_record/information"]}}
        first = self.fields(capture, recipe, handled=("/raw_record/information/a",))
        capture["raw_record"]["information"] = {"a": "A", "b": {"x": "X", "y": "Y"}}
        assert (self.fields(capture, recipe, handled=("/raw_record/information/a",))) == (first)
        assert (len(first)) == (1)

    def test_large_unknown_evidence_is_not_truncated(self):
        source_text = "Complete original source paragraph. " * 2000
        source = {"known": "mapped", "new": {"source_text": source_text, "values": list(range(1000))}}
        capture = self.capture(source)
        rows = self.fields(capture, handled=("/raw_record/information/known",))
        assert (rows[0]["raw_value"]) == (source["new"])
        assert (len(rows[0]["raw_value"]["values"])) == (1000)
