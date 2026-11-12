"""A small starting test suite for the order desk."""

import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from supplydesk.cli import main
from supplydesk.menu import read_request, run_menu
from supplydesk.service import OrderService


class OrderSmokeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "state.json"
        self.service = OrderService(self.path)

    def test_regular_pickup_quote(self):
        quote = self.service.quote("regular", [{"product_id": "notebook", "quantity": 2}])
        self.assertEqual(quote["subtotal_cents"], 1000)
        self.assertEqual(quote["discount_cents"], 0)
        self.assertEqual(quote["delivery_cents"], 0)
        self.assertEqual(quote["total_cents"], 1000)

    def test_student_delivery_quote(self):
        quote = self.service.quote("student", [{"product_id": "hoodie", "quantity": 2}], "delivery")
        self.assertEqual(quote["discount_cents"], 800)
        self.assertEqual(quote["delivery_cents"], 600)
        self.assertEqual(quote["total_cents"], 7800)

    def test_student_discount_boundary(self):
        below_threshold = self.service.quote(
            "student",
            [
                {"product_id": "hoodie", "quantity": 1},
                {"product_id": "pen-pack", "quantity": 1},
            ],
        )
        at_threshold = self.service.quote(
            "student", [{"product_id": "notebook", "quantity": 10}]
        )

        self.assertEqual(below_threshold["subtotal_cents"], 4750)
        self.assertEqual(below_threshold["discount_cents"], 0)
        self.assertEqual(at_threshold["subtotal_cents"], 5000)
        self.assertEqual(at_threshold["discount_cents"], 500)

    def test_student_discount_rounds_half_cent_up(self):
        self.assertEqual(self.service.discount_calculation("student", 5005), 501)

    def test_standard_delivery_price_boundary(self):
        below_threshold = self.service.quote(
            "regular",
            [
                {"product_id": "hoodie", "quantity": 2},
                {"product_id": "mug", "quantity": 1},
            ],
            "delivery",
        )
        at_threshold = self.service.quote(
            "regular",
            [
                {"product_id": "hoodie", "quantity": 2},
                {"product_id": "mug", "quantity": 1},
                {"product_id": "notebook", "quantity": 1},
            ],
            "delivery",
        )

        self.assertEqual(below_threshold["subtotal_cents"], 9500)
        self.assertEqual(below_threshold["delivery_cents"], 600)
        self.assertEqual(at_threshold["subtotal_cents"], 10000)
        self.assertEqual(at_threshold["delivery_cents"], 0)

    def test_express_fee_is_not_waived_at_free_delivery_threshold(self):
        quote = self.service.quote(
            "regular",
            [
                {"product_id": "hoodie", "quantity": 2},
                {"product_id": "mug", "quantity": 1},
                {"product_id": "notebook", "quantity": 1},
            ],
            "express",
        )

        self.assertEqual(quote["subtotal_cents"], 10000)
        self.assertEqual(quote["delivery_cents"], 1200)
        self.assertEqual(quote["total_cents"], 11200)

    def test_order_can_be_reopened(self):
        order = self.service.place_order("regular", [{"product_id": "mug", "quantity": 1}])
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["status"], "placed")
        self.assertEqual(OrderService(self.path).get_order(order["order_id"]), order)

    def test_cancel_order_restores_stock(self):
        before = self.service.catalog()
        order = self.service.place_order("regular", [{"product_id": "pen-pack", "quantity": 2}])
        cancelled = self.service.cancel_order(order["order_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(self.service.catalog(), before)
    #normal behaviour tests
    def test_normal_input(self):
        order = self.service.place_order("regular", [{"product_id": "mug", "quantity": 1}])
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["status"], "placed")
        self.assertEqual(OrderService(self.path).get_order(order["order_id"]), order)
    #boundary behaviour tests
    def test_boundary_empty_stock(self):
        order = self.service.place_order("regular", [{"product_id": "notebook", "quantity": 20}])
        stock = self.service.catalog()
        notebook = next((item for item in stock if item["product_id"] == "notebook"), None)
        self.assertIsNotNone(notebook)
        self.assertEqual(notebook["stock"], 0)
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["status"], "placed")
        self.assertEqual(OrderService(self.path).get_order(order["order_id"]), order)
    #exceptional behaviour tests
    def test_invalid_input(self):
        with self.assertRaisesRegex(ValueError, "Unknown product"):
            self.service.place_order(
                "regular", [{"product_id": "invalid-product", "quantity": 1}]
            )
    def test_cancel_nonexistent_order(self):
        with self.assertRaisesRegex(ValueError, "Unknown order"):
            self.service.cancel_order("ORD-9999")
    #existing functionality tests
    def test_order_can_be_placed(self):
        order = self.service.place_order("regular", [{"product_id": "mug", "quantity": 1}])
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["status"], "placed")
        self.assertEqual(OrderService(self.path).get_order(order["order_id"]), order)
    def test_order_can_be_cancelled(self):
        order = self.service.place_order("regular", [{"product_id": "pen-pack", "quantity": 2}])
        cancelled = self.service.cancel_order(order["order_id"])
        self.assertEqual(cancelled["status"], "cancelled")

    def test_cli_defaults_to_pickup_and_accepts_express(self):
        for fulfillment, expected_delivery in (("pickup", 0), ("express", 1200)):
            with self.subTest(fulfillment=fulfillment):
                output = StringIO()
                args = ["--data", str(self.path)]
                if fulfillment == "express":
                    args.extend(["quote", "--fulfillment", "express"])
                else:
                    args.append("quote")
                args.extend(["--item", "notebook:2"])

                with redirect_stdout(output):
                    exit_code = main(args)

                result = json.loads(output.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertEqual(result["fulfillment"], fulfillment)
                self.assertEqual(result["delivery_cents"], expected_delivery)

    def test_cli_rejected_request_returns_nonzero_and_reports_error(self):
        output = StringIO()
        errors = StringIO()

        with redirect_stdout(output), redirect_stderr(errors):
            exit_code = main(
                ["--data", str(self.path), "place", "--item", "notebook:99"]
            )

        self.assertEqual(exit_code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("Not enough stock", errors.getvalue())
        self.assertEqual(self.service.list_orders(), [])

    def test_menu_quote_uses_defaults_and_does_not_save(self):
        output = StringIO()
        answers = ["2", "", "notebook", "2", "", "", "0"]

        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            exit_code = run_menu(self.service)

        self.assertEqual(exit_code, 0)
        self.assertIn("Customer: regular | Fulfillment: pickup", output.getvalue())
        self.assertIn("Total: $10.00", output.getvalue())
        self.assertFalse(self.path.exists())

    def test_menu_reprompts_for_invalid_quantity(self):
        output = StringIO()
        answers = ["2", "", "notebook", "two", "notebook", "1", "", "", "0"]

        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            run_menu(self.service)

        self.assertIn("Please enter a whole number. Re-enter this item.", output.getvalue())
        self.assertIn("Total: $5.00", output.getvalue())

    def test_menu_quote_accepts_express_fulfillment(self):
        output = StringIO()
        answers = ["2", "student", "hoodie", "2", "", "express", "0"]

        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            run_menu(self.service)

        self.assertIn("Customer: student | Fulfillment: express", output.getvalue())
        self.assertIn("Delivery: $12.00", output.getvalue())
        self.assertIn("Total: $84.00", output.getvalue())

    def test_menu_declined_placement_leaves_data_unchanged(self):
        output = StringIO()
        stock_before = self.service.catalog()
        answers = ["3", "", "mug", "1", "", "", "n", "0"]

        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            run_menu(self.service)

        self.assertIn("Order not placed.", output.getvalue())
        self.assertEqual(self.service.catalog(), stock_before)
        self.assertEqual(self.service.list_orders(), [])
        self.assertFalse(self.path.exists())

    def test_menu_reports_request_error_and_returns_to_menu(self):
        output = StringIO()
        answers = ["2", "", "unknown-product", "1", "", "", "0"]

        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            exit_code = run_menu(self.service)

        self.assertEqual(exit_code, 0)
        self.assertIn("Error: Unknown product: unknown-product", output.getvalue())
        self.assertIn("Returning to the menu.", output.getvalue())

    #AI developed tests
    # def test_menu_collects_quantity_after_product_id(self):
    #         with patch("builtins.input", side_effect=["regular", "notebook", "2", "", "pickup"]):
    #             request = read_request(self.service)
    #         self.assertEqual(
    #             request,
    #             ("regular", [{"product_id": "notebook", "quantity": 2}], "pickup"),
    #         )
    
    
    # def test_duplicate_item_lines_cannot_exceed_stock(self):
    #     with self.assertRaisesRegex(ValueError, "Not enough stock"):
    #         self.service.quote(
    #             "regular",
    #             [
    #                 {"product_id": "notebook", "quantity": 11},
    #                 {"product_id": "notebook", "quantity": 10},
    #             ],
    #         )
if __name__ == "__main__":
    unittest.main()
