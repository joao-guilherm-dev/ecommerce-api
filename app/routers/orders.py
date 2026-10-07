from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..security import admin_only, current_user

router = APIRouter(prefix="/orders", tags=["Pedidos"])

TRANSITIONS = {
    "pending": {"paid", "cancelled"},
    "paid": {"shipped", "cancelled"},
    "shipped": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}


def _restock(db: Session, order: models.Order):
    for it in order.items:
        p = db.get(models.Product, it.product_id)
        if p:
            p.stock += it.quantity


@router.post("", response_model=schemas.OrderOut, status_code=201)
def checkout(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    cart = db.scalars(select(models.CartItem).where(models.CartItem.user_id == user.id)).all()
    if not cart:
        raise HTTPException(400, "Carrinho vazio")
    order = models.Order(user_id=user.id, total=Decimal("0"))
    for ci in cart:
        p = ci.product
        if not p.active or ci.quantity > p.stock:
            raise HTTPException(409, f"Estoque insuficiente para '{p.name}'")
        p.stock -= ci.quantity
        order.items.append(models.OrderItem(product_id=p.id, name=p.name,
                                            unit_price=p.price, quantity=ci.quantity))
        order.total += p.price * ci.quantity
        db.delete(ci)
    db.add(order)
    db.commit()  # transação única: estoque, pedido e carrinho juntos
    db.refresh(order)
    return order


@router.get("", response_model=list[schemas.OrderOut])
def my_orders(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(models.Order).where(models.Order.user_id == user.id)
                      .order_by(models.Order.id.desc())).all()


def _own_order(db: Session, user: models.User, order_id: int) -> models.Order:
    order = db.get(models.Order, order_id)
    if not order or (order.user_id != user.id and not user.is_admin):
        raise HTTPException(404, "Pedido não encontrado")
    return order


@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, user: models.User = Depends(current_user),
              db: Session = Depends(get_db)):
    return _own_order(db, user, order_id)


@router.post("/{order_id}/cancel", response_model=schemas.OrderOut)
def cancel(order_id: int, user: models.User = Depends(current_user),
           db: Session = Depends(get_db)):
    order = _own_order(db, user, order_id)
    if order.status != "pending":
        raise HTTPException(409, "Só pedidos pendentes podem ser cancelados pelo cliente")
    order.status = "cancelled"
    _restock(db, order)
    db.commit()
    db.refresh(order)
    return order


@router.patch("/{order_id}/status", response_model=schemas.OrderOut,
              dependencies=[Depends(admin_only)])
def set_status(order_id: int, data: schemas.OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(404, "Pedido não encontrado")
    if data.status not in TRANSITIONS[order.status]:
        raise HTTPException(409, f"Transição inválida: {order.status} → {data.status}")
    if data.status == "cancelled":
        _restock(db, order)
    order.status = data.status
    db.commit()
    db.refresh(order)
    return order
