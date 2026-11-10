import unittest

from app.calculations import calculate_ownership_cost


class OwnershipCostTests(unittest.TestCase):
    def setUp(self):
        self.inputs = {
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

    def calculate(self, **changes):
        return calculate_ownership_cost(
            **{**self.inputs, **changes}
        )

    def test_complete_scenario(self):
        result = self.calculate()

        self.assertTrue(result["complete"])
        self.assertEqual(result["missing_inputs"], [])
        self.assertEqual(result["loan_amount"], 280000)
        self.assertEqual(
            result["monthly_components"]["principal_and_interest"],
            1678.74,
        )
        self.assertEqual(result["monthly_housing_cost"], 2228.74)
        self.assertEqual(
            result["monthly_cost_with_reserve"], 2428.74
        )

    def test_missing_insurance_keeps_total_unknown(self):
        result = self.calculate(
            purchase_price=375000,
            down_payment=75000,
            annual_property_tax=5400,
            annual_insurance=None,
            monthly_hoa=50,
        )

        self.assertFalse(result["complete"])
        self.assertEqual(
            result["missing_inputs"], ["homeowners_insurance"]
        )
        self.assertIsNone(
            result["monthly_components"]["homeowners_insurance"]
        )
        self.assertEqual(
            result["known_monthly_subtotal"], 2298.65
        )
        self.assertIsNone(result["monthly_housing_cost"])
        self.assertIsNone(result["monthly_cost_with_reserve"])

    def test_each_unknown_cost_makes_total_incomplete(self):
        for field in (
            "annual_property_tax",
            "annual_insurance",
            "monthly_hoa",
            "monthly_mortgage_insurance",
        ):
            with self.subTest(field=field):
                result = self.calculate(**{field: None})

                self.assertFalse(result["complete"])
                self.assertIsNone(result["monthly_housing_cost"])
                self.assertIsNone(
                    result["monthly_cost_with_reserve"]
                )

    def test_explicit_zero_is_different_from_unknown(self):
        unknown = self.calculate(
            monthly_mortgage_insurance=None
        )
        explicit_zero = self.calculate(
            monthly_mortgage_insurance=0
        )

        self.assertFalse(unknown["complete"])
        self.assertTrue(explicit_zero["complete"])
        self.assertEqual(
            explicit_zero["monthly_components"]["mortgage_insurance"],
            0,
        )

    def test_zero_interest(self):
        result = self.calculate(
            purchase_price=150000,
            down_payment=30000,
            annual_interest_rate_percent=0,
            loan_term_years=10,
        )

        self.assertEqual(
            result["monthly_components"]["principal_and_interest"],
            1000,
        )

    def test_cash_purchase_has_no_loan_payment(self):
        result = self.calculate(down_payment=350000)

        self.assertEqual(result["loan_amount"], 0)
        self.assertEqual(
            result["monthly_components"]["principal_and_interest"],
            0,
        )
        self.assertEqual(result["monthly_housing_cost"], 550)

    def test_reserve_is_separate_from_housing_cost(self):
        without_reserve = self.calculate(
            monthly_maintenance_reserve=0
        )
        with_reserve = self.calculate(
            monthly_maintenance_reserve=200
        )

        self.assertEqual(
            without_reserve["monthly_housing_cost"],
            with_reserve["monthly_housing_cost"],
        )
        self.assertEqual(
            with_reserve["monthly_cost_with_reserve"],
            2428.74,
        )

    def test_invalid_inputs_are_rejected(self):
        invalid_cases = [
            {"down_payment": 400000},
            {"purchase_price": 0},
            {"loan_term_years": 0},
            {"loan_term_years": 30.5},
            {"loan_term_years": True},
            {"annual_interest_rate_percent": -1},
            {"annual_property_tax": -100},
            {"annual_insurance": float("nan")},
            {"monthly_hoa": float("inf")},
        ]

        for changes in invalid_cases:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    self.calculate(**changes)


if __name__ == "__main__":
    unittest.main()