"""Operations used by the command-line order desk."""

from supplydesk.storage import JsonStore


class OrderService:
    def __init__(self, state_path=".supplydesk/state.json"):
        self.store = JsonStore(state_path)

    def catalog(self):
        return self.store.load()["catalog"]

    # def quote(self, customer_type, items, fulfillment="pickup"):
    #     state = self.store.load()
    #     if customer_type not in ("regular", "student"):
    #         raise ValueError("Customer type must be regular or student.")
    #     if fulfillment not in ("pickup", "delivery"):
    #         raise ValueError("Fulfillment must be pickup or delivery.")
    #     if not isinstance(items, list) or not items:
    #         raise ValueError("An order must contain at least one item.")
    #     lines = []
    #     subtotal = 0
    #     for item in items:
    #         if not isinstance(item, dict):
    #             raise ValueError("Each item must contain a product_id and quantity.")
    #         product = None
    #         for candidate in state["catalog"]:
    #             if candidate["product_id"] == item.get("product_id"):
    #                 product = candidate
    #                 break
    #         if product is None:
    #             raise ValueError("Unknown product.")
    #         quantity = item.get("quantity")
    #         if type(quantity) is not int or quantity < 1 or quantity > 99:
    #             raise ValueError("Quantity must be an integer from 1 to 99.")
    #         if quantity > product["stock"]:
    #             raise ValueError("Not enough stock for " + product["product_id"] + ".")
    #         line_total = product["unit_price_cents"] * quantity
    #         subtotal += line_total
    #         lines.append({
    #             "product_id": product["product_id"],
    #             "name": product["name"],
    #             "unit_price_cents": product["unit_price_cents"],
    #             "quantity": quantity,
    #             "line_total_cents": line_total,
    #         })
    #     discount = 0
    #     if customer_type == "student" and subtotal > 5000:
    #         discount = (subtotal * 10 + 50) // 100
    #     delivery = 0
    #     if fulfillment == "delivery" and subtotal - discount < 10000:
    #         delivery = 600
    #     return {
    #         "customer_type": customer_type,
    #         "fulfillment": fulfillment,
    #         "items": lines,
    #         "subtotal_cents": subtotal,
    #         "discount_cents": discount,
    #         "delivery_cents": delivery,
    #         "total_cents": subtotal - discount + delivery,
    #     }

    # def place_order(self, customer_type, items, fulfillment="pickup"):
    #     state = self.store.load()
    #     if customer_type not in ("regular", "student"):
    #         raise ValueError("Customer type must be regular or student.")
    #     if fulfillment not in ("pickup", "delivery"):
    #         raise ValueError("Fulfillment must be pickup or delivery.")
    #     if not isinstance(items, list) or not items:
    #         raise ValueError("An order must contain at least one item.")
    #     lines = []
    #     subtotal = 0
    #     for item in items:
    #         if not isinstance(item, dict):
    #             raise ValueError("Each item must contain a product_id and quantity.")
    #         product = None
    #         for candidate in state["catalog"]:
    #             if candidate["product_id"] == item.get("product_id"):
    #                 product = candidate
    #                 break
    #         if product is None:
    #             raise ValueError("Unknown product.")
    #         quantity = item.get("quantity")
    #         if type(quantity) is not int or quantity < 1 or quantity > 99:
    #             raise ValueError("Quantity must be an integer from 1 to 99.")
    #         if quantity > product["stock"]:
    #             raise ValueError("Not enough stock for " + product["product_id"] + ".")
    #         line_total = product["unit_price_cents"] * quantity
    #         subtotal += line_total
    #         lines.append({
    #             "product_id": product["product_id"],
    #             "name": product["name"],
    #             "unit_price_cents": product["unit_price_cents"],
    #             "quantity": quantity,
    #             "line_total_cents": line_total,
    #         })
    #     discount = 0
    #     if customer_type == "student" and subtotal > 5000:
    #         discount = (subtotal * 10 + 50) // 100
    #     delivery = 0
    #     if fulfillment == "delivery" and subtotal - discount < 10000:
    #         delivery = 600
    #     order = {
    #         "order_id": "ORD-" + str(state["next_order_number"]).zfill(4),
    #         "status": "placed",
    #         "customer_type": customer_type,
    #         "fulfillment": fulfillment,
    #         "items": lines,
    #         "subtotal_cents": subtotal,
    #         "discount_cents": discount,
    #         "delivery_cents": delivery,
    #         "total_cents": subtotal - discount + delivery,
    #     }
    #     for line in lines:
    #         for product in state["catalog"]:
    #             if product["product_id"] == line["product_id"]:
    #                 product["stock"] -= line["quantity"]
    #     state["next_order_number"] += 1
    #     state["orders"].append(order)
    #     self.store.save(state)
    #     return order

    def list_orders(self):
        return self.store.load()["orders"]

    def get_order(self, order_id):
        state = self.store.load()
        for order in state["orders"]:
            if order["order_id"] == order_id:
                return order
        raise ValueError("Unknown order: " + order_id)

    def cancel_order(self, order_id):
        state = self.store.load()
        order = None
        for candidate in state["orders"]:
            if candidate["order_id"] == order_id:
                order = candidate
                break
        if order is None:
            raise ValueError("Unknown order: " + order_id)
        for line in order["items"]:
            for product in state["catalog"]:
                if product["product_id"] == line["product_id"]:
                    product["stock"] += line["quantity"]
        order["status"] = "cancelled"
        self.store.save(state)
        return order

    def fulfillment_validation(self, fulfillment):
        #add express delivery here
        if fulfillment not in ("pickup", "delivery", "express"):
            raise ValueError("Fulfillment must be pickup, delivery, or express.")

    def customer_type_validation(self, customer_type):
        if customer_type not in ("regular", "student"):
            raise ValueError("Customer type must be regular or student.")

    def quantity_validation(self, quantity):
        if type(quantity) is not int or not 1 <= quantity <= 99:
            raise ValueError("Quantity must be an integer from 1 to 99.")

    def items_validation(self, items):
        if not isinstance(items, list) or not items:
            raise ValueError("An order must contain at least one item.")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Each item must contain a product_id and quantity.")
            product_id = item.get("product_id")
            if not isinstance(product_id, str) or not product_id:
                raise ValueError("Each item must contain a product_id.")
            quantity = item.get("quantity")
            self.quantity_validation(quantity)

    def service_error_check(self, customer_type, fulfillment, items):
        self.customer_type_validation(customer_type)
        self.fulfillment_validation(fulfillment)
        self.items_validation(items)
        self.quantity_validation(self, quantity)
        state = self.store.load()
        product_lookup = {product["product_id"]: product for product in state["catalog"]}
        requested_quantities = {}
        for item in items:
            product_id = item["product_id"]
            if product_id not in product_lookup:
                raise ValueError("Unknown product: " + product_id)
            requested_quantities[product_id] = (
                requested_quantities.get(product_id, 0) + item["quantity"]
            )
        for product_id, quantity in requested_quantities.items():
            if quantity > product_lookup[product_id]["stock"]:
                raise ValueError("Not enough stock for " + product_id + ".")
        return state

    def product_lookup(self, product_id, catalog=None):
        if catalog is None:
            catalog = self.store.load()["catalog"]
        for candidate in catalog:
            if candidate["product_id"] == product_id:
                return candidate
        raise ValueError("Unknown product.")

    def order_calculation(self, customer_type, fulfillment, items, state):
        lines = []
        subtotal = 0
        for item in items:
            product = self.product_lookup(item["product_id"], state["catalog"])
            quantity = item.get("quantity")
            line_total = product["unit_price_cents"] * quantity
            subtotal += line_total
            lines.append({
                "product_id": product["product_id"],
                "name": product["name"],
                "unit_price_cents": product["unit_price_cents"],
                "quantity": quantity,
                "line_total_cents": line_total,
            })
        discount = self.discount_calculation(customer_type, subtotal)
        delivery = 0
        if fulfillment == "delivery" and subtotal - discount < 10000:
            delivery = 600
        if fulfillment == "express":
            delivery = 1200
        return {
            "customer_type": customer_type,
            "fulfillment": fulfillment,
            "items": lines,
            "subtotal_cents": subtotal,
            "discount_cents": discount,
            "delivery_cents": delivery,
            "total_cents": subtotal - discount + delivery,
        }

    def quote(self, customer_type, items, fulfillment):
        state = self.service_error_check(customer_type, fulfillment, items)
        return self.order_calculation(customer_type, fulfillment, items, state)

    def place_order(self, customer_type, items, fulfillment):
        state = self.service_error_check(customer_type, fulfillment, items)
        order = self.order_calculation(customer_type, fulfillment, items, state)
        order = {
            "order_id": "ORD-" + str(state["next_order_number"]).zfill(4),
            "status": "placed",
            **order,
        }
        for line in order["items"]:
            product = self.product_lookup(line["product_id"], state["catalog"])
            product["stock"] -= line["quantity"]
        state["next_order_number"] += 1
        state["orders"].append(order)
        self.store.save(state)
        return order

    def discount_calculation(self, customer_type, subtotal):
        discount = 0
        if customer_type == "student" and subtotal >= 5000:
            discount = (subtotal * 10 + 50) // 100
        return discount



