# E-commerce API (FastAPI)

## Rodar
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Docs interativas: http://localhost:8000/docs

Variáveis opcionais: `SECRET_KEY`, `DATABASE_URL` (ex.: `postgresql+psycopg://...`), `TOKEN_MINUTES`.

## Testes
```bash
pytest -q
```

## Endpoints
| Método | Rota | Acesso |
|---|---|---|
| POST | /auth/register, /auth/login | público (1º usuário vira admin) |
| GET | /auth/me | logado |
| GET | /categories, /products, /products/{id} | público (filtros: q, category_id, min_price, max_price, in_stock, sort, skip, limit) |
| POST | /categories, /products | admin |
| PUT/DELETE | /products/{id} | admin (DELETE = soft delete) |
| GET | /cart | logado |
| POST | /cart/items | logado |
| PATCH/DELETE | /cart/items/{product_id} | logado |
| POST | /orders (checkout do carrinho) | logado |
| GET | /orders, /orders/{id} | dono ou admin |
| POST | /orders/{id}/cancel | dono (só pendente) |
| PATCH | /orders/{id}/status | admin (pending→paid→shipped→delivered) |
