import unittest

from fastapi.testclient import TestClient

from app.api import app
from unittest.mock import patch


def property_input(property_id, **changes):
    values = {
        "property_id": property_id,
        "purchase_price": 350000,
        "down_payment": 70000,
        "annual_interest_rate_percent": 6,
        "loan_term_years": 30,
        "annual_property_tax": 4800,
        "annual_insurance": 1800,
        "monthly_hoa": 0,
        "monthly_mortgage_insurance": 0,
        "monthly_maintenance_reserve": 200,
    }
    return {**values, **changes}


class ComparisonEndpointTests(unittest.TestCase):
    def setUp(self):
        property_lookup = patch(
            "app.api.get_existing_property_ids",
            return_value={"SYN-001", "SYN-002", "SYN-003"},
        )
        property_lookup.start()
        self.addCleanup(property_lookup.stop)
        self.client = TestClient(app)

        self.first = property_input("SYN-001")

        self.second = property_input(
            "SYN-002",
            purchase_price=325000,
            down_payment=65000,
            annual_property_tax=4200,
            annual_insurance=1500,
            monthly_hoa=325,
        )

        self.third = property_input(
            "SYN-003",
            purchase_price=375000,
            down_payment=75000,
            annual_property_tax=5400,
            annual_insurance=None,
            monthly_hoa=50,
        )

    def tearDown(self):
        self.client.close()

    def compare(self, *properties):
        return self.client.post(
            "/comparisons",
            json={"properties": list(properties)},
        )

    def test_two_properties(self):
        response = self.compare(self.first, self.second)

        self.assertEqual(response.status_code, 200)
        properties = response.json()["properties"]

        self.assertEqual(
            [item["property_id"] for item in properties],
            ["SYN-001", "SYN-002"],
        )
        self.assertEqual(
            properties[0]["calculation"]["monthly_cost_with_reserve"],
            2428.74,
        )
        self.assertEqual(
            properties[1]["calculation"]["monthly_cost_with_reserve"],
            2558.83,
        )

    def test_three_properties(self):
        response = self.compare(
            self.first, self.second, self.third
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.json()["properties"]), 3
        )

    def test_missing_insurance_remains_unknown(self):
        response = self.compare(self.first, self.third)

        self.assertEqual(response.status_code, 200)
        result = response.json()["properties"][1]["calculation"]

        self.assertFalse(result["complete"])
        self.assertEqual(
            result["missing_inputs"], ["homeowners_insurance"]
        )
        self.assertEqual(
            result["known_monthly_subtotal"], 2298.65
        )
        self.assertIsNone(result["monthly_housing_cost"])
        self.assertIsNone(result["monthly_cost_with_reserve"])

    def test_duplicate_property_is_rejected(self):
        response = self.compare(self.first, self.first)

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "Each property must appear only once.",
        )

    def test_unknown_property_is_rejected(self):
        unknown = property_input("SYN-999")
        response = self.compare(self.first, unknown)

        self.assertEqual(response.status_code, 422)
        self.assertIn(
            "Unknown property ID",
            response.json()["detail"],
        )

    def test_mismatched_loan_assumptions_are_rejected(self):
        for change in (
            {"annual_interest_rate_percent": 7},
            {"loan_term_years": 15},
        ):
            with self.subTest(change=change):
                response = self.compare(
                    self.first,
                    {**self.second, **change},
                )

                self.assertEqual(response.status_code, 422)
                self.assertIn(
                    "same interest rate and loan term",
                    response.json()["detail"],
                )

    def test_property_count_limits(self):
        for properties in (
            [],
            [self.first],
            [self.first, self.second, self.third, self.first],
        ):
            with self.subTest(count=len(properties)):
                response = self.compare(*properties)
                self.assertEqual(response.status_code, 422)

    def test_down_payment_above_price_is_rejected(self):
        invalid = {
            **self.second,
            "down_payment": 400000,
        }
        response = self.compare(self.first, invalid)

        self.assertEqual(response.status_code, 422)
        self.assertIn(
            "down_payment cannot exceed purchase_price",
            response.json()["detail"],
        )


if __name__ == "__main__":
    unittest.main()