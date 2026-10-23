"""Product schemas — create/update request DTOs and response DTO."""
from marshmallow import Schema, fields, validate, validates_schema, ValidationError

FULFILLMENT_TYPES = ['stock', 'indent']

class PriceTierSchema(Schema):
    """One volume-price row: 'from min_qty units, each costs unit_price'."""
    min_qty = fields.Int(required=True, strict=True, validate=validate.Range(min=2))
    unit_price = fields.Float(required=True, validate=validate.Range(min=0))


class ProductCreateSchema(Schema):
    category_id = fields.Int(required=True, strict=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(load_default=None, allow_none=True)
    price = fields.Float(required=True, validate=validate.Range(min=0))
    stock = fields.Int(load_default=0, strict=True, validate=validate.Range(min=0))
    image_url = fields.Str(load_default=None, allow_none=True)

    sku = fields.Str(load_default=None, allow_none=True, validate=validate.Length(min=1, max=64))
    brand = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=100))
    unit = fields.Str(load_default='pcs', validate=validate.Length(min=1, max=20))
    min_order_qty = fields.Int(load_default=1, strict=True, validate=validate.Range(min=1))
    tkdn_percent = fields.Float(load_default=None, allow_none=True, validate=validate.Range(min=0, max=100))
    datasheet_url = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=500))
    fulfillment_type = fields.Str(load_default='stock', validate=validate.OneOf(FULFILLMENT_TYPES))
    lead_time_days = fields.Int(load_default=None, allow_none=True, strict=True, validate=validate.Range(min=0, max=365))
    price_tiers = fields.List(fields.Nested(PriceTierSchema), load_default=list)

    seller_id = fields.Int(load_default=None, allow_none=True, strict=True)

    @validates_schema
    def validate_indent(self, data, **kwargs):
        if data.get('fulfillment_type') == 'indent' and not data.get('lead_time_days'):
            raise ValidationError('Lead time (days) is required for made-to-order (indent) products.', 'lead_time_days')


class ProductUpdateSchema(Schema):
    category_id = fields.Int(strict=True)
    name = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str(allow_none=True)
    price = fields.Float(validate=validate.Range(min=0))
    stock = fields.Int(strict=True, validate=validate.Range(min=0))
    image_url = fields.Str(allow_none=True)
    sku = fields.Str(allow_none=True, validate=validate.Length(min=1, max=64))
    brand = fields.Str(allow_none=True, validate=validate.Length(max=100))
    unit = fields.Str(validate=validate.Length(min=1, max=20))
    min_order_qty = fields.Int(strict=True, validate=validate.Range(min=1))
    tkdn_percent = fields.Float(allow_none=True, validate=validate.Range(min=0, max=100))
    datasheet_url = fields.Str(allow_none=True, validate=validate.Length(max=500))
    fulfillment_type = fields.Str(validate=validate.OneOf(FULFILLMENT_TYPES))
    lead_time_days = fields.Int(allow_none=True, strict=True, validate=validate.Range(min=0, max=365))
    price_tiers = fields.List(fields.Nested(PriceTierSchema))


class ProductCategorySummarySchema(Schema):
    id = fields.Int()
    name = fields.Str()


class ProductSellerSummarySchema(Schema):
    id = fields.Int()
    store_name = fields.Str()


class PriceTierResponseSchema(Schema):
    min_qty = fields.Int()
    unit_price = fields.Float()


class ProductResponseSchema(Schema):
    id = fields.Int(dump_only=True)
    category_id = fields.Int()
    seller_id = fields.Int()
    name = fields.Str()
    slug = fields.Str()
    description = fields.Str(allow_none=True)
    price = fields.Float()
    stock = fields.Int()
    image_url = fields.Str(allow_none=True)
    sku = fields.Str(allow_none=True)
    brand = fields.Str(allow_none=True)
    unit = fields.Str()
    min_order_qty = fields.Int()
    tkdn_percent = fields.Float(allow_none=True)
    datasheet_url = fields.Str(allow_none=True)
    fulfillment_type = fields.Str()
    lead_time_days = fields.Int(allow_none=True)
    is_active = fields.Bool()
    created_at = fields.DateTime(format="iso")
    updated_at = fields.DateTime(format="iso")
    category = fields.Nested(ProductCategorySummarySchema, dump_only=True)
    seller = fields.Nested(ProductSellerSummarySchema, dump_only=True)
    price_tiers = fields.List(fields.Nested(PriceTierResponseSchema), dump_only=True)
