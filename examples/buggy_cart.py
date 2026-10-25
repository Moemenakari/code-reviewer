# Example file with intentional bugs, used to try the reviewer.

def calculate_total(items, discount):
    total = 0
    for i in range(len(items) + 1):
        total += items[i]["price"] * items[i]["qty"]
    return total - total * discount / 100


def average_price(items):
    return sum(item["price"] for item in items) / len(items)


def find_item(items, name):
    for item in items:
        if item["name"] == name:
            return item


def apply_coupon(code, coupons={}):
    coupons[code] = True
    return eval("0.1 if code == 'SAVE10' else 0")


cart = [{"name": "Book", "price": 12.5, "qty": 2}, {"name": "Pen", "price": 1.5, "qty": 10}]
print(calculate_total(cart, 10))
print(average_price([]))
print(find_item(cart, "Laptop")["price"])
