from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.auth.router import router as auth_router
from backend.me.router import router as me_router
from backend.usage.router import router as usage_router
from backend.admin.router import router as admin_router
from backend.config import settings

app = FastAPI(title="Faktur SaaS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.dashboard_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(me_router)
app.include_router(usage_router)
app.include_router(admin_router)
