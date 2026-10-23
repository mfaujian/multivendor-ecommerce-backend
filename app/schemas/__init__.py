"""
schemas/ — Marshmallow DTO (Data Transfer Object) layer.
"""
from app.schemas.auth_schema import LoginSchema
from app.schemas.user_schema import UserRegisterSchema, UserResponseSchema
from app.schemas.seller_schema import SellerCreateSchema, SellerUpdateSchema, SellerResponseSchema
from app.schemas.category_schema import CategoryCreateSchema, CategoryUpdateSchema, CategoryResponseSchema
from app.schemas.product_schema import ProductCreateSchema, ProductUpdateSchema, ProductResponseSchema
from app.schemas.address_schema import AddressCreateSchema, AddressUpdateSchema, AddressResponseSchema
from app.schemas.cart_schema import CartAddItemSchema, CartUpdateItemSchema, CartItemResponseSchema, CartResponseSchema
from app.schemas.order_schema import (
    CheckoutSchema, CreateOrderSchema, OrderStatusUpdateSchema, PaymentUpdateSchema,
    OrderItemResponseSchema, OrderResponseSchema,
)