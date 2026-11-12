"""A small starting test suite for the order desk."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from supplydesk.menu import read_request
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

    #AI developed tests
    # def test_menu_collects_quantity_after_product_id(self):
    #         with patch("builtins.input", side_effect=["regular", "notebook", "2", "", "pickup"]):
    #             request = read_request(self.service)
    #         self.assertEqual(
    #             request,
    #             ("regular", [{"product_id": "notebook", "quantity": 2}], "pickup"),
    #         )
    
    # def test_invalid_quantity_is_rejected_by_service(self):
    #     for quantity in (0, 100, True, 1.5, "2"):
    #         with self.subTest(quantity=quantity):
    #             with self.assertRaisesRegex(ValueError, "Quantity must be an integer"):
    #                 self.service.quote(
    #                     "regular", [{"product_id": "notebook", "quantity": quantity}]
    #                 )
    
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
