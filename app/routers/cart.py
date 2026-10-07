from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..security import current_user

router = APIRouter(prefix="/cart", tags=["Carrinho"])


def _build(items: list[models.CartItem]) -> schemas.CartOut:
    out = [
        schemas.CartItemOut(product_id=i.product_id, quantity=i.quantity,
                            product=i.product, subtotal=i.product.price * i.quantity)
        for i in items
    ]
    return schemas.CartOut(items=out, total=sum((i.subtotal for i in out), Decimal("0")))


def _items(db: Session, user: models.User):
    return db.scalars(select(models.CartItem).where(models.CartItem.user_id == user.id)).all()


@router.get("", response_model=schemas.CartOut)
def get_cart(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    return _build(_items(db, user))


@router.post("/items", response_model=schemas.CartOut, status_code=201)
def add_item(data: schemas.CartItemIn, user: models.User = Depends(current_user),
             db: Session = Depends(get_db)):
    product = db.get(models.Product, data.product_id)
    if not product or not product.active:
        raise HTTPException(404, "Produto não encontrado")
    item = db.scalar(select(models.CartItem).where(
        models.CartItem.user_id == user.id, models.CartItem.product_id == product.id))
    new_qty = data.quantity + (item.quantity if item else 0)
    if new_qty > product.stock:
        raise HTTPException(409, f"Estoque insuficiente (disponível: {product.stock})")
    if item:
        item.quantity = new_qty
    else:
        db.add(models.CartItem(user_id=user.id, product_id=product.id, quantity=new_qty))
    db.commit()
    return _build(_items(db, user))


@router.patch("/items/{product_id}", response_model=schemas.CartOut)
def update_item(product_id: int, data: schemas.CartItemUpdate,
                user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(models.CartItem).where(
        models.CartItem.user_id == user.id, models.CartItem.product_id == product_id))
    if not item:
        raise HTTPException(404, "Item não está no carrinho")
    if data.quantity > item.product.stock:
        raise HTTPException(409, f"Estoque insuficiente (disponível: {item.product.stock})")
    item.quantity = data.quantity
    db.commit()
    return _build(_items(db, user))


@router.delete("/items/{product_id}", response_model=schemas.CartOut)
def remove_item(product_id: int, user: models.User = Depends(current_user),
                db: Session = Depends(get_db)):
    item = db.scalar(select(models.CartItem).where(
        models.CartItem.user_id == user.id, models.CartItem.product_id == product_id))
    if not item:
        raise HTTPException(404, "Item não está no carrinho")
    db.delete(item)
    db.commit()
    return _build(_items(db, user))
