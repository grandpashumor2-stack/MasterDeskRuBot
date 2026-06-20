from fastapi import APIRouter

web_router = APIRouter(prefix="/panel", tags=["panel"])

@web_router.get("/")
async def panel_index():
    return {"status": "ok", "panel": "MasterDesk"}
