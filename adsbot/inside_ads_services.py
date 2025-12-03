"""Services for InsideAds monetization and campaign management."""

from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from .models import (
    User,
    Channel,
    Campaign,
    PromoOffer,
    UserBalance,
    Transaction,
    AdvertisementMetrics,
)


def get_or_create_balance(session: Session, user: User) -> UserBalance:
    """Get or create user balance record."""
    balance = session.query(UserBalance).filter_by(user_id=user.id).first()
    if not balance:
        balance = UserBalance(user_id=user.id, balance=0.0)
        session.add(balance)
        session.commit()
    return balance


def get_user_balance(session: Session, user: User) -> float:
    """Get user current balance."""
    balance = get_or_create_balance(session, user)
    return balance.balance


def add_transaction(
    session: Session,
    user: User,
    transaction_type: str,
    amount: float,
    description: str,
    reference_id: int | None = None,
) -> Transaction:
    """Create a transaction record and update user balance."""
    balance = get_or_create_balance(session, user)
    
    # Update balance (earn/refund = positive, spend = negative)
    if transaction_type in ("earn", "refund"):
        balance.balance += amount
    elif transaction_type == "spend":
        balance.balance -= amount
    elif transaction_type == "withdrawal":
        balance.balance -= amount
    
    balance.updated_at = datetime.utcnow()
    
    # Create transaction record
    transaction = Transaction(
        user_id=user.id,
        transaction_type=transaction_type,
        amount=amount,
        description=description,
        reference_id=reference_id,
    )
    session.add(transaction)
    session.commit()
    return transaction


def get_recent_transactions(session: Session, user: User, days: int = 30) -> list[Transaction]:
    """Get user transactions from last N days."""
    since = datetime.utcnow() - timedelta(days=days)
    return (
        session.query(Transaction)
        .filter(and_(Transaction.user_id == user.id, Transaction.created_at >= since))
        .order_by(desc(Transaction.created_at))
        .all()
    )


def get_user_campaigns(session: Session, user: User) -> list[Campaign]:
    """Get all campaigns for user's channels."""
    return (
        session.query(Campaign)
        .join(Channel)
        .filter(Channel.user_id == user.id)
        .order_by(desc(Campaign.created_at))
        .all()
    )


def get_user_offers(session: Session, user: User) -> list[PromoOffer]:
    """Get all offers for user's channels."""
    return (
        session.query(PromoOffer)
        .join(Channel)
        .filter(Channel.user_id == user.id)
        .order_by(desc(PromoOffer.created_at))
        .all()
    )


def record_metrics(
    session: Session,
    channel: Channel,
    followers: int = 0,
    clicks: int = 0,
    impressions: int = 0,
    campaign_id: int | None = None,
) -> AdvertisementMetrics:
    """Record advertisement metrics for a channel/campaign."""
    metrics = AdvertisementMetrics(
        campaign_id=campaign_id,
        channel_id=channel.id,
        followers=followers,
        clicks=clicks,
        impressions=impressions,
    )
    session.add(metrics)
    session.commit()
    return metrics


def get_channel_metrics(
    session: Session, channel: Channel, days: int = 7
) -> dict:
    """Get aggregated metrics for a channel in last N days."""
    since = datetime.utcnow() - timedelta(days=days)
    metrics = (
        session.query(AdvertisementMetrics)
        .filter(
            and_(
                AdvertisementMetrics.channel_id == channel.id,
                AdvertisementMetrics.date >= since,
            )
        )
        .all()
    )
    
    if not metrics:
        return {"followers": 0, "clicks": 0, "impressions": 0}
    
    return {
        "followers": sum(m.followers for m in metrics),
        "clicks": sum(m.clicks for m in metrics),
        "impressions": sum(m.impressions for m in metrics),
    }


def get_user_statistics(session: Session, user: User) -> dict:
    """Get aggregated user statistics."""
    channels = session.query(Channel).filter_by(user_id=user.id).all()
    campaigns = get_user_campaigns(session, user)
    offers = get_user_offers(session, user)
    balance = get_user_balance(session, user)
    
    # Aggregate metrics across all channels
    total_followers = 0
    total_clicks = 0
    total_impressions = 0
    
    for channel in channels:
        metrics = get_channel_metrics(session, channel, days=7)
        total_followers += metrics["followers"]
        total_clicks += metrics["clicks"]
        total_impressions += metrics["impressions"]
    
    return {
        "channels": len(channels),
        "campaigns": len(campaigns),
        "offers": len(offers),
        "balance": balance,
        "followers": total_followers,
        "clicks": total_clicks,
        "impressions": total_impressions,
    }


def create_campaign_purchase(
    session: Session,
    buyer: User,
    seller_channel: Channel,
    campaign_name: str,
    budget: float,
    duration_days: int = 7,
) -> dict | None:
    """Create a campaign purchase (advertiser buys ad space on seller's channel)."""
    # Deduct budget from buyer's balance
    buyer_balance = get_or_create_balance(session, buyer)
    if buyer_balance.balance < budget:
        return None  # Insufficient funds

    # Deduct from buyer
    add_transaction(
        session,
        buyer,
        "spend",
        budget,
        f"Campaign purchase on {seller_channel.handle}",
        reference_id=seller_channel.id,
    )

    # Add to seller (commission-based, e.g., 80% to seller, 20% platform)
    seller = seller_channel.owner
    seller_earning = budget * 0.8
    add_transaction(
        session,
        seller,
        "earn",
        seller_earning,
        f"Ad revenue from campaign '{campaign_name}' on {seller_channel.handle}",
        reference_id=seller_channel.id,
    )

    return {
        "campaign_name": campaign_name,
        "seller_channel": seller_channel.handle,
        "budget": budget,
        "seller_earning": seller_earning,
        "status": "purchased",
    }


def list_available_channels_for_ads(session: Session, min_subscribers: int = 100) -> list[Channel]:
    """List channels available for advertising (with monetization enabled)."""
    # In a real scenario, filter by channels that opted into ad network
    # For now, return all channels with multiple subscribers
    channels = session.query(Channel).filter(Channel.id.isnot(None)).all()
    return channels[:10]  # Return top 10


def get_campaign_performance(session: Session, campaign_id: int) -> dict:
    """Get performance metrics for a campaign."""
    campaign = session.query(Campaign).filter_by(id=campaign_id).first()
    if not campaign:
        return {}

    metrics = (
        session.query(AdvertisementMetrics)
        .filter_by(campaign_id=campaign_id)
        .all()
    )

    if not metrics:
        return {
            "campaign_id": campaign_id,
            "name": campaign.name,
            "followers": 0,
            "clicks": 0,
            "impressions": 0,
            "ctr": 0.0,  # Click-through rate
        }

    total_followers = sum(m.followers for m in metrics)
    total_clicks = sum(m.clicks for m in metrics)
    total_impressions = sum(m.impressions for m in metrics)
    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0

    return {
        "campaign_id": campaign_id,
        "name": campaign.name,
        "followers": total_followers,
        "clicks": total_clicks,
        "impressions": total_impressions,
        "ctr": ctr,
    }
