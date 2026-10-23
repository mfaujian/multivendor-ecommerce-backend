"""Address schemas — saved delivery addresses."""
from marshmallow import Schema, fields, validate


class AddressCreateSchema(Schema):
    label = fields.Str(required=True, validate=validate.Length(min=1, max=60))
    recipient_name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    phone = fields.Str(required=True, validate=validate.Length(min=6, max=30))
    address_line = fields.Str(required=True, validate=validate.Length(min=5, max=500))
    city = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    province = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    postal_code = fields.Str(required=True, validate=validate.Length(min=4, max=10))
    is_default = fields.Bool(load_default=False)



class AddressUpdateSchema(Schema):
    label = fields.Str(validate=validate.Length(min=1, max=60))
    recipient_name = fields.Str(validate=validate.Length(min=2, max=100))
    phone = fields.Str(validate=validate.Length(min=6, max=30))
    address_line = fields.Str(validate=validate.Length(min=5, max=500))
    city = fields.Str(validate=validate.Length(min=2, max=100))
    province = fields.Str(validate=validate.Length(min=2, max=100))
    postal_code = fields.Str(validate=validate.Length(min=4, max=10))
    is_default = fields.Bool()



class AddressResponseSchema(Schema):
    id = fields.Int(dump_only=True)
    label = fields.Str()
    recipient_name = fields.Str()
    phone = fields.Str()
    address_line = fields.Str()
    city = fields.Str()
    province = fields.Str()
    postal_code = fields.Str()
    is_default = fields.Bool()