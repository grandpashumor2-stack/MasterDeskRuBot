from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.infrastructure.database.connection import get_db
from app.core.security import get_current_owner
from app.domain.repositories.client import ClientRepository
from app.domain.models.campaign import Campaign, CampaignStatus
from app.domain.services.subscription_checker import SubscriptionChecker
from sqlalchemy import select

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    name: str
    text: str
    segment_filter: dict = {}
    scheduled_at: Optional[datetime] = None


@router.get("/{company_id}")
async def list_campaigns(
    company_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    result = await session.execute(
        select(Campaign).where(Campaign.company_id == company_id).order_by(Campaign.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/{company_id}")
async def create_campaign(
    company_id: UUID,
    data: CampaignCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    checker = SubscriptionChecker(session)
    if not await checker.has_feature(company_id, "has_campaigns"):
        raise HTTPException(status_code=403, detail="Upgrade to BUSINESS plan to use campaigns")
    
    campaign = Campaign(
        company_id=company_id,
        name=data.name,
        text=data.text,
        segment_filter=data.segment_filter,
        scheduled_at=data.scheduled_at,
        status=CampaignStatus.DRAFT,
    )
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/send")
async def send_campaign(
    campaign_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    campaign = await session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == CampaignStatus.SENT:
        raise HTTPException(status_code=400, detail="Campaign already sent")
    
    background_tasks.add_task(_send_campaign_bg, campaign_id)
    campaign.status = CampaignStatus.SENDING
    await session.commit()
    return {"status": "sending", "campaign_id": str(campaign_id)}


async def _send_campaign_bg(campaign_id: UUID):
    """Background task to send campaign to all matching clients."""
    from app.infrastructure.database.connection import AsyncSessionLocal
    from aiogram import Bot
    import asyncio
    
    async with AsyncSessionLocal() as session:
        campaign = await session.get(Campaign, campaign_id)
        if not campaign:
            return
        
        company = await session.get(
            __import__("app.domain.models.company", fromlist=["Company"]).Company,
            campaign.company_id
        )
        if not company:
            return
        from app.core.config import settings
        token = company.telegram_bot_token or settings.BOT_TOKEN
        if not token:
            return
        
        client_repo = ClientRepository(session)
        clients = await client_repo.get_by_segment(campaign.company_id, campaign.segment_filter)
        
        try:
            bot = Bot(token=token)
            sent = 0
            for client in clients:
                try:
                    await bot.send_message(client.telegram_id, campaign.text)
                    sent += 1
                    await asyncio.sleep(0.05)  # 20 msg/sec limit
                except Exception:
                    pass
            await bot.session.close()
            
            campaign.status = CampaignStatus.SENT
            campaign.sent_at = datetime.utcnow()
            campaign.sent_count = sent
            await session.commit()
        except Exception as e:
            campaign.status = CampaignStatus.CANCELLED
            await session.commit()
