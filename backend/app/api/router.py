


"""
Main API router.
"""

from fastapi import APIRouter

from app.api.v1.generator_sizing import (
    router as generator_sizing_router,
)
from app.api.v1.ht_panel import (
    router as ht_panel_router,
)
from app.api.v1.load_calculation_run import (
    router as load_calculation_run_router,
)
from app.api.v1.load_demand import (
    router as load_demand_router,
)
from app.api.v1.lt_pcc import (
    router as lt_pcc_router,
)
from app.api.v1.standard import (
    router as standard_router,
)
from app.api.v1.transformer_sizing import (
    router as transformer_sizing_router,
)
from app.api.v1.unit import (
    router as unit_router,
)


api_router = APIRouter()


@api_router.get(
    "/health",
    tags=["System"],
)
async def health_check():
    """Return application health status."""

    return {
        "status": "healthy",
        "application": "KES Electrical OS API",
    }


@api_router.get(
    "/version",
    tags=["System"],
)
async def version():
    """Return application version information."""

    return {
        "application": "KES Electrical OS API",
        "version": "0.1.0",
    }


api_router.include_router(unit_router)
api_router.include_router(standard_router)
api_router.include_router(load_demand_router)
api_router.include_router(transformer_sizing_router)
api_router.include_router(generator_sizing_router)
api_router.include_router(ht_panel_router)
api_router.include_router(lt_pcc_router)
api_router.include_router(load_calculation_run_router)
