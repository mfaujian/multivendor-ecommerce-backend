"""Order schemas — checkout/status-update request DTOs and response DTOs."""
from marshmallow import Schema, fields, validate

VALID_ORDER_STATUSES = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
PAYMENT_METHODS = ['bank_transfer', 'request_terms']
PAYMENT_STATUSES = ['unpaid', 'paid', 'terms_requested', 'terms_approved']


class CheckoutSchema(Schema):
    shipping_address = fields.Str(required=True, validate=validate.Length(min=1))


class OrderLineSchema(Schema):
    product_id = fields.Int(required=True, strict=True)
    quantity = fields.Int(required=True, strict=True, validate=validate.Range(min=1, max=1000000))


class CreateOrderSchema(Schema):
    items = fields.List(fields.Nested(OrderLineSchema), required=True, validate=validate.Length(min=1, max=100))
    shipping_address_id = fields.Int(load_default=None, allow_none=True, strict=True)
    shipping_address = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=1000))
    po_number = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=60))
    notes = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=1000))
    payment_method = fields.Str(load_default='bank_transfer', validate=validate.OneOf(PAYMENT_METHODS))
    requested_delivery_date = fields.Date(load_default=None, allow_none=True)


class OrderStatusUpdateSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf(VALID_ORDER_STATUSES))


class PaymentUpdateSchema(Schema):
    payment_status = fields.Str(required=True, validate=validate.OneOf(PAYMENT_STATUSES))


class OrderItemResponseSchema(Schema):
    product_id = fields.Int()
    sku = fields.Function(lambda item: item.sku or (item.product.sku if item.product else None))
    product_name = fields.Function(lambda item: item.product_name or (item.product.name if item.product else None))
    unit = fields.Function(lambda item: item.product.unit if item.product else None)
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
    po_number = fields.Str(allow_none=True)
    notes = fields.Str(allow_none=True)
    payment_method = fields.Str()
    payment_status = fields.Str()
    requested_delivery_date = fields.Date(allow_none=True)
    buyer = fields.Function(lambda order: {
        "id": order.buyer.id, "full_name": order.buyer.full_name, "email": order.buyer.email
    } if order.buyer else None)
    seller = fields.Function(lambda order: {
        "id": order.seller.id, "store_name": order.seller.store_name
    } if order.seller else None)
    order_items = fields.List(fields.Nested(OrderItemResponseSchema))
    created_at = fields.DateTime(format="iso")
    updated_at = fields.DateTime(format="iso")