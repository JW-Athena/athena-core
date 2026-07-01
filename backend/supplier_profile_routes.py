from fastapi import APIRouter

from supplier_profile_engine import SupplierProfileEngine


router = APIRouter(
    prefix="/supplier-profiles",
    tags=["Supplier Profile Engine"],
)

engine = SupplierProfileEngine()


@router.get("/{supplier_name}")
async def get_supplier_profile(
    supplier_name: str,
):

    result = engine.get_profile(
        supplier_name=supplier_name,
    )

    return {
        "engine": "supplier_profile_engine",
        "name": "Supplier Profile Engine",
        "status": "success",
        "result": result,
    }