from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Auth ----
class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserOut(ORM):
    id: int
    name: str
    email: EmailStr
    is_admin: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---- Catálogo ----
class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class CategoryOut(ORM):
    id: int
    name: str


class ProductBase(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = ""
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock: int = Field(ge=0, default=0)
    category_id: int | None = None
    active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)
    category_id: int | None = None
    active: bool | None = None


class ProductOut(ORM, ProductBase):
    id: int


class Page(BaseModel):
    total: int
    items: list[ProductOut]


# ---- Carrinho ----
class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=100)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0, le=100)


class CartItemOut(ORM):
    product_id: int
    quantity: int
    product: ProductOut
    subtotal: Decimal


class CartOut(BaseModel):
    items: list[CartItemOut]
    total: Decimal


# ---- Pedidos ----
class OrderItemOut(ORM):
    product_id: int
    name: str
    unit_price: Decimal
    quantity: int


class OrderOut(ORM):
    id: int
    status: str
    total: Decimal
    created_at: datetime
    items: list[OrderItemOut]


class OrderStatusUpdate(BaseModel):
    status: Literal["paid", "shipped", "delivered", "cancelled"]
