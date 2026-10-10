"""Order schemas — checkout/status-update request DTOs and response DTOs."""
from marshmallow import Schema, fields, validate

VALID_ORDER_STATUSES = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']


class CheckoutSchema(Schema):
    shipping_address = fields.Str(required=True, validate=validate.Length(min=1))


class OrderStatusUpdateSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf(VALID_ORDER_STATUSES))


class OrderItemResponseSchema(Schema):
    product_id = fields.Int()
    product_name = fields.Function(lambda item: item.product.name if item.product else None)
    quantity = fields.Int()
    unit_price = fields.Float()
    subtotal = fields.Function(lambda item: float(item.unit_price) * item.quantity)


class OrderResponseSchema(Schema):
    id = fields.UUID(dump_only=True)
    user_id = fields.Int()
    seller_id = fields.Int()
    status = fields.Str()
    total_amount = fields.Float()
    shipping_address = fields.Str()
    order_items = fields.List(fields.Nested(OrderItemResponseSchema))
    created_at = fields.DateTime(format="iso")
    updated_at = fields.DateTime(format="iso")