from fastapi import APIRouter
from app.api.v1.endpoints import auth, company, services, appointments, analytics, campaigns, clients, admin

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(company.router)
api_router.include_router(services.router)
api_router.include_router(appointments.router)
api_router.include_router(analytics.router)
api_router.include_router(campaigns.router)
api_router.include_router(clients.router)
api_router.include_router(admin.router)
from app.api.v1.endpoints import payments
api_router.include_router(payments.router)
