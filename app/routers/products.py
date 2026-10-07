from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..security import admin_only

router = APIRouter(tags=["Catálogo"])


# ---- Categorias ----
@router.get("/categories", response_model=list[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(models.Category).order_by(models.Category.name)).all()


@router.post("/categories", response_model=schemas.CategoryOut, status_code=201,
             dependencies=[Depends(admin_only)])
def create_category(data: schemas.CategoryCreate, db: Session = Depends(get_db)):
    if db.scalar(select(models.Category).where(models.Category.name == data.name)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Categoria já existe")
    cat = models.Category(name=data.name)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


# ---- Produtos ----
@router.get("/products", response_model=schemas.Page)
def list_products(
    q: str | None = Query(None, description="Busca por nome"),
    category_id: int | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    in_stock: bool = False,
    sort: str = Query("id", pattern="^(id|name|price|-price|-id)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(models.Product).where(models.Product.active.is_(True))
    if q:
        stmt = stmt.where(models.Product.name.ilike(f"%{q}%"))
    if category_id:
        stmt = stmt.where(models.Product.category_id == category_id)
    if min_price is not None:
        stmt = stmt.where(models.Product.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(models.Product.price <= max_price)
    if in_stock:
        stmt = stmt.where(models.Product.stock > 0)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    col = getattr(models.Product, sort.lstrip("-"))
    stmt = stmt.order_by(col.desc() if sort.startswith("-") else col).offset(skip).limit(limit)
    return {"total": total, "items": db.scalars(stmt).all()}


@router.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Product, product_id)
    if not p or not p.active:
        raise HTTPException(404, "Produto não encontrado")
    return p


def _check_category(db: Session, category_id: int | None):
    if category_id and not db.get(models.Category, category_id):
        raise HTTPException(422, "Categoria inexistente")


@router.post("/products", response_model=schemas.ProductOut, status_code=201,
             dependencies=[Depends(admin_only)])
def create_product(data: schemas.ProductCreate, db: Session = Depends(get_db)):
    _check_category(db, data.category_id)
    p = models.Product(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.put("/products/{product_id}", response_model=schemas.ProductOut,
            dependencies=[Depends(admin_only)])
def update_product(product_id: int, data: schemas.ProductUpdate, db: Session = Depends(get_db)):
    p = db.get(models.Product, product_id)
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    changes = data.model_dump(exclude_unset=True)
    _check_category(db, changes.get("category_id"))
    for k, v in changes.items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/products/{product_id}", status_code=204, dependencies=[Depends(admin_only)])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Product, product_id)
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    p.active = False  # soft delete: preserva histórico de pedidos
    db.commit()
