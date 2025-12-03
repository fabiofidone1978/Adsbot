from __future__ import annotations

import enum
from datetime import datetime, date
from typing import Optional

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class OfferType(str, enum.Enum):
    """Supported promotion offer types."""

    shoutout = "shoutout"
    post = "post"
    pinned = "pinned"
    takeover = "takeover"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    subscription_type: Mapped[str] = mapped_column(String(50), default="gratis")  # "gratis" o "premium"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    channels: Mapped[list["Channel"]] = relationship("Channel", back_populates="owner")
    templates: Mapped[list["BroadcastTemplate"]] = relationship("BroadcastTemplate", back_populates="owner")


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    handle: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped[User] = relationship("User", back_populates="channels")
    goals: Mapped[list["GrowthGoal"]] = relationship("GrowthGoal", back_populates="channel")
    campaigns: Mapped[list["Campaign"]] = relationship("Campaign", back_populates="channel")
    offers: Mapped[list["PromoOffer"]] = relationship("PromoOffer", back_populates="channel")


class GrowthGoal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"))
    target_members: Mapped[int] = mapped_column(Integer)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    channel: Mapped[Channel] = relationship("Channel", back_populates="goals")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"))
    name: Mapped[str] = mapped_column(String(255))
    budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    call_to_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    channel: Mapped[Channel] = relationship("Channel", back_populates="campaigns")


class PromoOffer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"))
    offer_type: Mapped[OfferType] = mapped_column(Enum(OfferType))
    price: Mapped[float] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    channel: Mapped[Channel] = relationship("Channel", back_populates="offers")


class BroadcastTemplate(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped[User] = relationship("User", back_populates="templates")


class UserBalance(Base):
    """Saldo e portafoglio dell'utente."""
    __tablename__ = "user_balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship("User")


class Transaction(Base):
    """Cronologia transazioni (guadagni, spese, pagamenti)."""
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(50))  # "earn", "spend", "refund", "withdrawal"
    amount: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text)
    reference_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # campaign_id, offer_id, ecc.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship("User")


class AdvertisementMetrics(Base):
    """Metriche di campagne e offerte pubblicitarie."""
    __tablename__ = "ad_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("campaigns.id"), nullable=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)
    followers: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    campaign: Mapped[Optional[Campaign]] = relationship("Campaign")
    channel: Mapped[Channel] = relationship("Channel")


async def stats(update: Update, context: CallbackContext) -> None:
    try:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, reply_markup=MENU_BUTTONS)
        else:
            await update.message.reply_text(text, reply_markup=MENU_BUTTONS)
    except telegram.error.BadRequest as e:
        if "Message is not modified" not in str(e):
            raise