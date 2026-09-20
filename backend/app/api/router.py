"""
Main API router.

Public: health, version and the sign-in routes. Everything else hangs under protected_router,
which requires a signed-in user (401 otherwise); tests/api/test_route_protection.py walks every
route and fails when one is reachable without a session and is not on its short public list.

Roles: every signed-in member may read (GET). Calculating and saving studies needs OWNER or
ENGINEER; changing the shared reference data (units, standards) needs OWNER.
"""

from fastapi import APIRouter, Depends

from app.api.authentication import engineer_writes, owner_writes, require_user
from app.api.v1.auth import router as auth_router
from app.api.v1.cable import router as cable_router
from app.api.v1.cable_run import router as cable_run_router
from app.api.v1.fault import router as fault_router
from app.api.v1.fault_run import router as fault_run_router
from app.api.v1.generator_sizing import router as generator_sizing_router
from app.api.v1.ht_panel import router as ht_panel_router
from app.api.v1.load_calculation_run import router as load_calculation_run_router
from app.api.v1.load_demand import router as load_demand_router
from app.api.v1.lt_pcc import router as lt_pcc_router
from app.api.v1.standard import router as standard_router
from app.api.v1.transformer_sizing import router as transformer_sizing_router
from app.api.v1.unit import router as unit_router

api_router = APIRouter()


@api_router.get(
    "/health",
    tags=["System"],
)
async def health_check() -> dict[str, str]:
    """Return application health status."""

    return {
        "status": "healthy",
        "application": "KES Electrical OS API",
    }


@api_router.get(
    "/version",
    tags=["System"],
)
async def version() -> dict[str, str]:
    """Return application version information."""

    return {
        "application": "KES Electrical OS API",
        "version": "0.1.0",
    }


api_router.include_router(auth_router)

protected_router = APIRouter(dependencies=[Depends(require_user)])

REFERENCE_DATA_ROUTERS = (unit_router, standard_router)
STUDY_ROUTERS = (
    fault_router,
    load_demand_router,
    transformer_sizing_router,
    generator_sizing_router,
    ht_panel_router,
    lt_pcc_router,
    load_calculation_run_router,
    cable_router,
    cable_run_router,
    fault_run_router,
)

for reference_data_router in REFERENCE_DATA_ROUTERS:
    protected_router.include_router(reference_data_router, dependencies=[Depends(owner_writes)])

for study_router in STUDY_ROUTERS:
    protected_router.include_router(study_router, dependencies=[Depends(engineer_writes)])

api_router.include_router(protected_router)
