from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from engine_020_organization_model import organization_model


router = APIRouter(tags=["ATHENA Organization Operating Model"])


@router.get("/athena/organization")
async def organization():
    return organization_model.organization_summary()


@router.get("/athena/organization/summary")
async def organization_summary():
    return organization_model.organization_summary()


@router.get("/athena/organization/departments")
async def list_departments():
    return organization_model.list_departments()


@router.post("/athena/organization/departments")
async def create_department(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = organization_model.create_department(
        name=str(payload.get("name", "") or ""),
        description=str(payload.get("description", "") or ""),
    )
    return _raise_on_failure(result)


@router.get("/athena/organization/people")
async def list_people():
    return organization_model.list_people()


@router.post("/athena/organization/people")
async def create_person(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = organization_model.create_person(
        name=str(payload.get("name", "") or ""),
        title=str(payload.get("title", "") or ""),
        department=str(payload.get("department", "") or ""),
        responsibilities=payload.get("responsibilities", []),
    )
    return _raise_on_failure(result)


@router.get("/athena/organization/suppliers")
async def list_suppliers():
    return organization_model.list_suppliers()


@router.post("/athena/organization/suppliers")
async def create_supplier(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = organization_model.create_supplier(
        name=str(payload.get("name", "") or ""),
        status=str(payload.get("status", "active") or "active"),
        risk_level=str(payload.get("risk_level", "medium") or "medium"),
        products=payload.get("products", []),
    )
    return _raise_on_failure(result)


def _raise_on_failure(result: Dict[str, Any]) -> Dict[str, Any]:
    if result.get("status") != "failed":
        return result
    raise HTTPException(status_code=400, detail=result)
