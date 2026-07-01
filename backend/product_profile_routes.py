from fastapi import APIRouter

from product_profile_engine import ProductProfileEngine


router = APIRouter(
    prefix="/product-profiles",
    tags=["Product Profile Engine"],
)

engine = ProductProfileEngine()


@router.get("/{product_name}")
async def get_product_profile(product_name: str):
    result = engine.get_profile(product_name=product_name)

    return {
        "engine": "product_profile_engine",
        "name": "Product Profile Engine",
        "status": result.get("status", "success"),
        "result": result,
    }