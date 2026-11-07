import csv
import fcntl
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Path as PathParameter, Query, status
from pydantic import BaseModel, Field, field_validator


ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_FILE = ROOT / "products.csv"
ALERT_THRESHOLD = int(os.getenv("INVENTORY_ALERT_THRESHOLD", "10"))
if ALERT_THRESHOLD < 0:
    raise ValueError("INVENTORY_ALERT_THRESHOLD debe ser un entero no negativo")

app = FastAPI(title="Inventory API")


class NewProduct(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=0, strict=True)
    unit: str = Field(min_length=1, max_length=50)

    @field_validator("name", "unit")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El texto no puede estar vacio")
        return value


class Product(NewProduct):
    id: int = Field(gt=0, strict=True)


class StockChange(BaseModel):
    delta: int = Field(strict=True)


@contextmanager
def inventory_lock():
    try:
        with PRODUCTS_FILE.with_suffix(".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
    except (OSError, ValueError, KeyError, csv.Error) as error:
        raise HTTPException(
            status_code=500,
            detail="No se pudo leer o guardar el inventario; comprueba el CSV y sus permisos.",
        ) from error


def read_products() -> list[Product]:
    if not PRODUCTS_FILE.exists():
        write_products([])
    with PRODUCTS_FILE.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != ["id", "name", "quantity", "unit"]:
            raise ValueError("Cabecera de inventario no valida")
        products = [
            Product(
                id=int(row["id"]), name=row["name"],
                quantity=int(row["quantity"]), unit=row["unit"],
            )
            for row in reader
        ]
    if len({product.id for product in products}) != len(products):
        raise ValueError("IDs duplicados en el inventario")
    return products


def write_products(products: list[Product]) -> None:
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", newline="", encoding="utf-8", dir=PRODUCTS_FILE.parent,
            delete=False,
        ) as destination:
            temporary_path = Path(destination.name)
            writer = csv.DictWriter(destination, fieldnames=["id", "name", "quantity", "unit"])
            writer.writeheader()
            writer.writerows(product.model_dump() for product in products)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary_path, PRODUCTS_FILE)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@app.get("/inventory", response_model=list[Product])
def get_inventory():
    with inventory_lock():
        return read_products()


@app.post("/inventory", response_model=Product, status_code=status.HTTP_201_CREATED)
def add_product(product: NewProduct):
    with inventory_lock():
        products = read_products()
        created = Product(id=max((item.id for item in products), default=0) + 1, **product.model_dump())
        products.append(created)
        write_products(products)
        return created


@app.patch("/inventory/{product_id}", response_model=Product)
def update_stock(change: StockChange, product_id: int = PathParameter(gt=0)):
    with inventory_lock():
        products = read_products()
        for product in products:
            if product.id == product_id:
                if product.quantity + change.delta < 0:
                    raise HTTPException(status_code=409, detail="Stock insuficiente para esta salida.")
                product.quantity += change.delta
                write_products(products)
                return product
        raise HTTPException(status_code=404, detail=f"El producto {product_id} no existe.")


@app.get("/inventory/alerts", response_model=list[Product])
def get_alerts(threshold: int = Query(default=ALERT_THRESHOLD, ge=0)):
    with inventory_lock():
        return [product for product in read_products() if product.quantity < threshold]