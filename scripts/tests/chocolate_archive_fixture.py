"""Shared preserved archive fixture without any collected tests or lifecycle hooks."""

import json

from category_research import import_document
from dataset_contracts import resolve_contract_root


class ChocolateArchiveFixture:
    def initialize(self, base):
        self.base = base
        self.archive = self.base / "collections"
        self.deduplicated = self.base / "deduplicated"
        self.output = self.base / "standardized"
        self.schema_root = resolve_contract_root(offline=True)
        self.profile = json.loads((self.schema_root / "profile.json").read_text())
        self.design = json.loads((self.schema_root / "model-design.json").read_text())

    def product(
        self,
        listing="example",
        source="chocolate-shop",
        weight=200,
        price="04.00",
        observed_at="2026-10-03T07:00:00Z",
    ):
        return {
            "product_id": listing,
            "source_key": source,
            "source_url": "https://" + source + ".example.test/products/shared-product",
            "identity": {
                "name": "Fixture Dark Chocolate Bar " + str(weight) + "g",
                "brand": "Fixture Chocolate Maker",
                "source_product_id": "shared-product",
                "source_variant_id": "shared-variant",
            },
            "information": {
                "selected_variant": {
                    "id": "shared-variant",
                    "price": price,
                    "grams": 999,
                    "available": True,
                    "compare_at_price": None,
                    "title": "Default Title",
                },
                "catalogue_retrieval_currency": "GBP",
                "catalogue_collected_at": observed_at,
                "product_type": "Bar",
                "body_html": "<p>Original wording: chocolat noir; café.</p>\n",
                "review_fixture": {
                    "identity.product_group": "bar",
                    "identity.source_role": "retail",
                    "identity.brand": "Fixture Chocolate Maker",
                    "identity.retailer": "The Chocolate Shop",
                    "composition.chocolate_type": "dark",
                    "composition.cocoa_percentage": 70,
                    "composition.nuts_presence": "absent",
                    "dietary.vegan_claim": "present",
                    "certifications.fairtrade_claim": "absent",
                    "certifications.organic_claim": "absent",
                    "quantity.total_edible_weight_g": weight,
                },
            },
            "source_artifacts": [
                {
                    "kind": "page",
                    "content": "Original wording: chocolat noir; café.\n",
                    "url": "https://"
                    + source
                    + ".example.test/products/shared-product",
                }
            ],
            "images": [],
        }

    def collect(self, products):
        return import_document(
            {
                "contract_version": "1",
                "study": {
                    "study_id": "chocolate-standardization-test",
                    "category": "chocolate",
                    "market": "uk",
                },
                "products": products,
            },
            self.archive,
            workers=1,
        )

    def snapshot(self, directory):
        return {
            str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob("*")
            if path.is_file()
        }
