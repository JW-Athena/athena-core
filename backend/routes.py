from fastapi import FastAPI

from capability_004_routes import router as capability_004_router
from capability_005_routes import router as capability_005_router
from capability_006_routes import router as capability_006_router
from capability_007_routes import router as capability_007_router

from engine_008_routes import router as engine_008_router
from engine_009_routes import router as engine_009_router

from developer_dashboard import router as developer_dashboard_router

from document_intelligence_routes import router as document_intelligence_router
from entity_intelligence_routes import router as entity_intelligence_router
from entity_database_routes import router as entity_database_router

from product_profile_routes import router as product_profile_router
from supplier_profile_routes import router as supplier_profile_router
from tender_profile_routes import router as tender_profile_router
from tender_index_routes import router as tender_index_router
from tender_comparison_routes import router as tender_comparison_router

from executive_decision_routes import router as executive_decision_router
from executive_decision_brief_routes import router as executive_decision_brief_router
from bid_no_bid_routes import router as bid_no_bid_router
from risk_register_routes import router as risk_register_router
from commercial_exposure_routes import router as commercial_exposure_router
from executive_action_plan_routes import router as executive_action_plan_router
from business_memory_routes import router as business_memory_router

from module_registry_routes import router as module_registry_router

from dashboard_routes import router as dashboard_router


def register_routes(app: FastAPI):

    app.include_router(capability_004_router)
    app.include_router(capability_005_router)
    app.include_router(capability_006_router)
    app.include_router(capability_007_router)

    app.include_router(engine_008_router)
    app.include_router(engine_009_router)

    app.include_router(developer_dashboard_router)

    app.include_router(document_intelligence_router)
    app.include_router(entity_intelligence_router)
    app.include_router(entity_database_router)

    app.include_router(product_profile_router)
    app.include_router(supplier_profile_router)
    app.include_router(tender_profile_router)
    app.include_router(tender_index_router)
    app.include_router(tender_comparison_router)

    app.include_router(executive_decision_router)
    app.include_router(executive_decision_brief_router)
    app.include_router(bid_no_bid_router)
    app.include_router(risk_register_router)
    app.include_router(commercial_exposure_router)
    app.include_router(executive_action_plan_router)
    app.include_router(business_memory_router)

    app.include_router(module_registry_router)

    app.include_router(dashboard_router)
