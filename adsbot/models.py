from __future__ import annotations

import enum
from datetime import datetime, date
from typing import Optional

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


# ============================================================================
# ENUMS - STATE MACHINES
# ============================================================================

class UserRole(str, enum.Enum):
    """Ruolo dell'utente sulla piattaforma."""
    admin = "admin"
    editor = "editor"
    advertiser = "advertiser"
    user = "user"  # Default, non ancora scelto


class UserState(str, enum.Enum):
    """Stato del flusso registrazione/attivazione utente."""
    new_user = "new_user"
    editor_registering = "editor_registering"
    editor_active = "editor_active"
    advertiser_registering = "advertiser_registering"
    advertiser_active = "advertiser_active"
    suspended = "suspended"


class ChannelState(str, enum.Enum):
    """Stato del canale nel marketplace."""
    pending_review = "pending_review"  # Admin deve verificare admin
    active = "active"  # Disponibile per ordini
    suspended = "suspended"  # Sospeso per violazioni
    inactive = "inactive"  # Editore ha rimosso listing
    disputed = "disputed"  # In disputa


class OrderState(str, enum.Enum):
    """Stato dettagliato dell'ordine."""
    draft = "draft"  # Non ancora pagato
    pending_editor_confirmation = "pending_editor_confirmation"  # In attesa editore
    confirmed = "confirmed"  # Editore ha accettato
    published = "published"  # Post online
    completed = "completed"  # Pagato e chiuso
    disputed = "disputed"  # In contestazione
    cancelled = "cancelled"  # Cancellato


class DisputeStatus(str, enum.Enum):
    """Stato di una contestazione/reclamo."""
    open = "open"
    investigating = "investigating"
    resolved = "resolved"
    closed = "closed"


class PaymentStatus(str, enum.Enum):
    """Stato del pagamento."""
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"
    escrow_held = "escrow_held"  # In escrow, non ancora rilasciato


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
    
    # STATO MACHINE
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user)  # admin, editor, advertiser, user
    state: Mapped[UserState] = mapped_column(Enum(UserState), default=UserState.new_user)  # Fase registrazione
    
    # REPUTAZIONE
    reputation_score: Mapped[float] = mapped_column(Float, default=3.0)  # 1-5 stelle
    rating_count: Mapped[int] = mapped_column(Integer, default=0)  # Numero di valutazioni
    risk_flags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default={})  # {"disputed": 2, "refunded": 1}
    
    # TIMELINE
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    admin_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # Quando verificato da admin
    
    # SUSPENSION
    is_suspended: Mapped[bool] = mapped_column(default=False)
    suspended_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    suspended_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    channels: Mapped[list["Channel"]] = relationship("Channel", back_populates="owner")
    templates: Mapped[list["BroadcastTemplate"]] = relationship("BroadcastTemplate", back_populates="owner")
    editor_profile: Mapped[Optional["EditorProfile"]] = relationship("EditorProfile", back_populates="user", uselist=False)
    advertiser_profile: Mapped[Optional["AdvertiserProfile"]] = relationship("AdvertiserProfile", back_populates="user", uselist=False)


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    handle: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # MARKETPLACE STATE
    state: Mapped[ChannelState] = mapped_column(Enum(ChannelState), default=ChannelState.pending_review)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Note admin sulla verifica
    suspended_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    suspended_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # METRICHE
    subscribers: Mapped[int] = mapped_column(Integer, default=0)
    reach_24h: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # crypto, tech, lifestyle, ecc
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    metrics_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

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
    
    # Nuovi campi per campagne tipo Meta Ads
    payment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "per_clic", "per_iscritto", "massimo"
    weekly_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Budget settimanale
    interaction_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Prezzo per interazione
    target_languages: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Es: "it,en,es" (comma-separated)
    min_offer: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Offerta minima
    max_offer: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Offerta massima
    minimum_price_chosen: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Prezzo minimo scelto dall'utente (tolto per ogni post)
    remaining_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Budget rimanente dopo i post
    
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
    """Wallet e Saldo - Gestione fondi dell'utente."""
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


# ============================================================================
# REPUTATION & ANALYTICS MODELS
# ============================================================================

class EditorProfile(Base):
    """Profilo e statistiche dell'editore."""
    __tablename__ = "editor_profiles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    
    # Statistiche
    orders_received: Mapped[int] = mapped_column(Integer, default=0)
    orders_completed: Mapped[int] = mapped_column(Integer, default=0)
    orders_rejected: Mapped[int] = mapped_column(Integer, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1
    dispute_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1
    cancellation_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Finanze
    earnings_total: Mapped[float] = mapped_column(Float, default=0.0)
    earnings_month: Mapped[float] = mapped_column(Float, default=0.0)
    withdrawals_total: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Timeline
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    user: Mapped[User] = relationship("User", back_populates="editor_profile")


class AdvertiserProfile(Base):
    """Profilo e statistiche dell'inserzionista."""
    __tablename__ = "advertiser_profiles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    
    # Statistiche
    orders_placed: Mapped[int] = mapped_column(Integer, default=0)
    orders_completed: Mapped[int] = mapped_column(Integer, default=0)
    orders_disputed: Mapped[int] = mapped_column(Integer, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1
    
    # ROI & Performance
    total_spent: Mapped[float] = mapped_column(Float, default=0.0)
    total_new_subscribers: Mapped[int] = mapped_column(Integer, default=0)
    roi_average: Mapped[float] = mapped_column(Float, default=0.0)  # %
    cost_per_subscriber: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Risk Level
    risk_level: Mapped[str] = mapped_column(String(20), default="low")  # low, medium, high
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)  # Se high risk
    
    # Timeline
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    user: Mapped[User] = relationship("User", back_populates="advertiser_profile")


class ReputationScore(Base):
    """Storico delle modifiche di reputazione."""
    __tablename__ = "reputation_scores"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    
    score_change: Mapped[float] = mapped_column(Float)  # +0.5, -1.0, ecc
    reason: Mapped[str] = mapped_column(String(255))  # "completed_order", "dispute_resolved", ecc
    reference_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # order_id
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    user: Mapped[User] = relationship("User")


# ============================================================================
# PAYMENT & TRANSACTION MODELS
# ============================================================================

class Payment(Base):
    """Modello pagamento con escrow."""
    __tablename__ = "payments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("marketplace_orders.id"), unique=True)
    
    # Importi
    amount: Mapped[float] = mapped_column(Float)
    platform_fee: Mapped[float] = mapped_column(Float)  # 10%
    seller_amount: Mapped[float] = mapped_column(Float)  # 90%
    
    # Metodo pagamento
    payment_method: Mapped[str] = mapped_column(String(50))  # "telegram_stars", "stripe", ecc
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.pending)
    
    # Timeline
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    refunded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Reference
    transaction_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Da provider esterno
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    order: Mapped["MarketplaceOrder"] = relationship("MarketplaceOrder")


class MoneyTransaction(Base):
    """Tracciamento di OGNI movimento di denaro."""
    __tablename__ = "money_transactions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    
    transaction_type: Mapped[str] = mapped_column(String(50))  # "deposit", "withdrawal", "earn", "commission", "refund"
    amount: Mapped[float] = mapped_column(Float)
    balance_after: Mapped[float] = mapped_column(Float)  # Saldo dopo transazione
    
    # Reference
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketplace_orders.id"), nullable=True)
    payment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("payments.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    user: Mapped[User] = relationship("User")
    order: Mapped[Optional["MarketplaceOrder"]] = relationship("MarketplaceOrder")
    payment: Mapped[Optional["Payment"]] = relationship("Payment")


# ============================================================================
# DISPUTE & ADMIN MODELS
# ============================================================================

class DisputeTicket(Base):
    """Gestione contestazioni/reclami."""
    __tablename__ = "dispute_tickets"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("marketplace_orders.id"), index=True)
    
    # Chi apre la disputa
    initiator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # Editor o Advertiser
    initiator_role: Mapped[str] = mapped_column(String(50))  # "editor", "advertiser"
    
    # Contenuto
    description: Mapped[str] = mapped_column(Text)
    evidence_media_urls: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # Array di URL screenshot/prove
    
    # Status
    status: Mapped[DisputeStatus] = mapped_column(Enum(DisputeStatus), default=DisputeStatus.open)
    
    # Risoluzione
    admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    admin_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "favor_editor", "favor_advertiser", "split"
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refund_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Se rimborso parziale
    
    # Timeline
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    order: Mapped["MarketplaceOrder"] = relationship("MarketplaceOrder")
    initiator: Mapped[User] = relationship("User", foreign_keys=[initiator_id])


class AuditLog(Base):
    """Log di OGNI azione importante (compliance/debugging)."""
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    
    action: Mapped[str] = mapped_column(String(100))  # "register_channel", "create_order", "publish", "admin_override", ecc
    details: Mapped[dict] = mapped_column(JSON)  # {"channel_id": 123, "price": 50, ...}
    
    # Admin actions
    is_admin_action: Mapped[bool] = mapped_column(Boolean, default=False)
    admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    user: Mapped[User] = relationship("User", foreign_keys=[user_id])


# ============================================================================
# MARKETPLACE MODELS
# ============================================================================

class OrderStatus(str, enum.Enum):
    """Status of marketplace orders."""
    pending = "pending"  # Inserzionista ha ordinato, editore non ha confermato
    confirmed = "confirmed"  # Editore ha confermato
    published = "published"  # Post pubblicato
    completed = "completed"  # Scadenza raggiunta, pagamento inviato
    cancelled = "cancelled"  # Cancellato


class ChannelListing(Base):
    """Canale messo in vendita nel marketplace."""
    __tablename__ = "channel_listings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    # Pricing
    price: Mapped[float] = mapped_column(Float)  # Prezzo per post
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Es: "crypto", "tech"
    
    # Metrics snapshot
    subscribers: Mapped[int] = mapped_column(Integer, default=0)
    reach_24h: Mapped[int] = mapped_column(Integer, default=0)
    quality_score: Mapped[float] = mapped_column(Float, default=0.5)  # 0-1
    
    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    is_available: Mapped[bool] = mapped_column(default=True)  # False se ordine in corso
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    channel: Mapped[Channel] = relationship("Channel")
    user: Mapped[User] = relationship("User")


class MarketplaceOrder(Base):
    """Ordine di acquisto spazio pubblicitario."""
    __tablename__ = "marketplace_orders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Parti coinvolte
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # Editore
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # Inserzionista
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"))
    channel_listing_id: Mapped[int] = mapped_column(ForeignKey("channel_listings.id"))
    
    # Dettagli ordine
    price: Mapped[float] = mapped_column(Float)  # Prezzo al momento ordine
    duration_hours: Mapped[int] = mapped_column(Integer, default=24)  # 6, 12, 24 ore
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.pending)
    
    # Contenuto
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_media_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Timeline
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Payment
    payment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    seller_earned: Mapped[float] = mapped_column(Float, default=0)
    platform_fee: Mapped[float] = mapped_column(Float, default=0)  # 10% commissione nostra
    
    # Metrics
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    new_subscribers: Mapped[int] = mapped_column(Integer, default=0)
    
    seller: Mapped[User] = relationship("User", foreign_keys=[seller_id])
    buyer: Mapped[User] = relationship("User", foreign_keys=[buyer_id])
    channel: Mapped[Channel] = relationship("Channel")
    listing: Mapped[ChannelListing] = relationship("ChannelListing")


class ChannelMetrics(Base):
    """Metriche storiche del canale."""
    __tablename__ = "channel_metrics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)
    
    subscribers: Mapped[int] = mapped_column(Integer, default=0)
    reach_24h: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0)  # 0-1
    
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    channel: Mapped[Channel] = relationship("Channel")


class AdminAuditLog(Base):
    """Log di audit per azioni admin sulla piattaforma."""
    __tablename__ = "admin_audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    
    action: Mapped[str] = mapped_column(String(100), index=True)  # Es: "APPROVE_CHANNEL", "SUSPEND_USER", "OVERRIDE_PRICE"
    details: Mapped[str] = mapped_column(Text)  # JSON string con dettagli azione
    status: Mapped[str] = mapped_column(String(50))  # "SUCCESS" o "FAILED"
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    admin: Mapped[User] = relationship("User")


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