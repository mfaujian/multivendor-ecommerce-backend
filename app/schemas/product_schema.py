"""Product schemas — create/update request DTOs and response DTO."""
from marshmallow import Schema, fields, validate


class ProductCreateSchema(Schema):
    category_id = fields.Int(required=True, strict=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(load_default=None, allow_none=True)
    price = fields.Float(required=True, validate=validate.Range(min=0))
    stock = fields.Int(load_default=0, strict=True, validate=validate.Range(min=0))
    image_url = fields.Str(load_default=None, allow_none=True)


class ProductUpdateSchema(Schema):
    category_id = fields.Int(strict=True)
    name = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str(allow_none=True)
    price = fields.Float(validate=validate.Range(min=0))
    stock = fields.Int(strict=True, validate=validate.Range(min=0))
    image_url = fields.Str(allow_none=True)


class ProductCategorySummarySchema(Schema):
    id = fields.Int()
    name = fields.Str()


class ProductSellerSummarySchema(Schema):
    id = fields.Int()
    store_name = fields.Str()


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
    is_active = fields.Bool()
    created_at = fields.DateTime(format="iso")
    updated_at = fields.DateTime(format="iso")
    category = fields.Nested(ProductCategorySummarySchema, dump_only=True)
    seller = fields.Nested(ProductSellerSummarySchema, dump_only=True)
