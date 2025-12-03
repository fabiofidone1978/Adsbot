from __future__ import annotations

from datetime import date
from typing import Iterable, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .models import (
    BroadcastTemplate,
    Campaign,
    Channel,
    GrowthGoal,
    OfferType,
    PromoOffer,
    User,
)


def ensure_user(session: Session, telegram_id: int, username: str | None, first_name: str | None, language_code: str | None) -> User:
    """Create or return an existing user by telegram id."""

    user = session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user:
        user.username = username
        user.first_name = first_name
        user.language_code = language_code
        return user

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        language_code=language_code,
    )
    session.add(user)
    session.flush()
    return user


def add_channel(session: Session, user: User, handle: str, title: str | None = None, topic: str | None = None) -> Channel:
    """Register a channel for the given user."""

    handle = handle.strip()
    existing = session.scalar(
        select(Channel).where(Channel.user_id == user.id, Channel.handle == handle)
    )
    if existing:
        return existing

    channel = Channel(user_id=user.id, handle=handle, title=title, topic=topic)
    session.add(channel)
    session.flush()
    return channel


def list_channels(session: Session, user: User) -> list[Channel]:
    """Return channels owned by the user."""

    return list(session.scalars(select(Channel).where(Channel.user_id == user.id)).all())


def add_goal(session: Session, channel: Channel, target_members: int, deadline: Optional[date], description: str | None = None) -> GrowthGoal:
    goal = GrowthGoal(channel_id=channel.id, target_members=target_members, deadline=deadline, description=description)
    session.add(goal)
    session.flush()
    return goal


def add_offer(session: Session, channel: Channel, offer_type: OfferType, price: float, notes: str | None = None) -> PromoOffer:
    offer = PromoOffer(channel_id=channel.id, offer_type=offer_type, price=price, notes=notes)
    session.add(offer)
    session.flush()
    return offer


def add_campaign(session: Session, channel: Channel, name: str, budget: float | None, call_to_action: str | None) -> Campaign:
    campaign = Campaign(channel_id=channel.id, name=name, budget=budget, call_to_action=call_to_action)
    session.add(campaign)
    session.flush()
    return campaign


def add_template(session: Session, user: User, name: str, content: str) -> BroadcastTemplate:
    template = BroadcastTemplate(user_id=user.id, name=name, content=content)
    session.add(template)
    session.flush()
    return template


def summarize_user(session: Session, user: User) -> dict[str, int]:
    """Return quick stats for a user."""

    channel_count = session.scalar(select(func.count(Channel.id)).where(Channel.user_id == user.id)) or 0
    goal_count = session.scalar(
        select(func.count(GrowthGoal.id)).join(Channel).where(Channel.user_id == user.id)
    ) or 0
    offer_count = session.scalar(
        select(func.count(PromoOffer.id)).join(Channel).where(Channel.user_id == user.id)
    ) or 0
    template_count = session.scalar(
        select(func.count(BroadcastTemplate.id)).where(BroadcastTemplate.user_id == user.id)
    ) or 0
    return {
        "channels": channel_count,
        "goals": goal_count,
        "offers": offer_count,
        "templates": template_count,
    }
