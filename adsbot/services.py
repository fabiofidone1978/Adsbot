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


def is_premium_user(session: Session, user: User) -> bool:
    """Check if user has premium subscription."""
    return user.subscription_type != "gratis"


def upgrade_user_to_premium(session: Session, user: User, plan_type: str = "premium") -> User:
    """Upgrade user to premium plan."""
    user.subscription_type = plan_type
    session.add(user)
    session.flush()
    return user


# ============================================================================
# MARKETPLACE V2 - BUSINESS LOGIC SERVICES
# ============================================================================

import re
from typing import Tuple, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class PriceCalculator:
    """Calcola prezzi suggeriti e range in base a metriche del canale."""
    
    # Category multipliers (per adjust price based on category value)
    CATEGORY_MULTIPLIERS = {
        "crypto": 1.5,        # Premium category
        "tech": 1.3,
        "business": 1.2,
        "lifestyle": 0.9,
        "news": 0.8,
        "general": 1.0,
    }
    
    # Base price per reach point (in EUR cents)
    BASE_PRICE_PER_REACH = 0.0005  # €0.0005 per reach
    MIN_PRICE = 0.50  # €0.50 minimum
    MAX_PRICE = 500.0  # €500 maximum
    
    @staticmethod
    def calculate_reach_estimate(subscribers: int) -> int:
        """Stima il reach 24h basato su numero iscritti (20% engagement)."""
        if subscribers < 100:
            return 100  # Minimum threshold
        return max(subscribers // 5, 100)
    
    @classmethod
    def suggest_price(
        cls,
        reach_24h: int,
        category: str = "general",
        conversion_rate: float = 1.0,
        quality_score: float = 0.7,
    ) -> Tuple[float, float, float]:
        """
        Calcola prezzo suggerito.
        
        Returns: (suggested_price, min_price, max_price)
        """
        base_price = reach_24h * cls.BASE_PRICE_PER_REACH
        category_mult = cls.CATEGORY_MULTIPLIERS.get(category.lower(), 1.0)
        category_adjusted = base_price * category_mult
        quality_adjusted = category_adjusted * quality_score
        final_price = quality_adjusted * conversion_rate
        
        suggested_price = max(cls.MIN_PRICE, min(cls.MAX_PRICE, final_price))
        min_price = max(cls.MIN_PRICE, suggested_price * 0.8)
        max_price = min(cls.MAX_PRICE, suggested_price * 1.2)
        
        return round(suggested_price, 2), round(min_price, 2), round(max_price, 2)


class ContentValidator:
    """Valida contenuti per spam, scam, e violazioni."""
    
    SPAM_KEYWORDS = [
        "click here", "clicca qui", "earn money", "guadagna soldi",
        "free money", "soldi gratis", "bitcoin easy", "crypto fast",
        "guaranteed", "garantito 100%", "not a scam", "work from home",
        "mlm", "pyramid", "scheme",
    ]
    
    BANNED_SHORTENERS = [
        "bit.ly", "tinyurl", "goo.gl", "short.link", "ow.ly"
    ]
    
    EMOJI_REGEX = r'[\U0001F600-\U0001F64F]|[\U0001F300-\U0001F5FF]|[\U0001F680-\U0001F6FF]|[\U0001F700-\U0001F77F]|[\U0001F780-\U0001F7FF]|[\U0001F800-\U0001F8FF]|[\U0001F900-\U0001F9FF]'
    MAX_EMOJI_RATIO = 0.15
    MAX_CAPS_RATIO = 0.40
    
    @staticmethod
    def validate(
        text: Optional[str],
        media_urls: Optional[List[str]] = None,
        strict: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Valida contenuto per spam/scam."""
        if not text and not media_urls:
            return False, "Contenuto vuoto"
        
        if text:
            is_valid, msg = ContentValidator._check_text(text, strict)
            if not is_valid:
                return False, msg
        
        if media_urls:
            is_valid, msg = ContentValidator._check_urls(media_urls)
            if not is_valid:
                return False, msg
        
        return True, None
    
    @staticmethod
    def _check_text(text: str, strict: bool = False) -> Tuple[bool, Optional[str]]:
        """Verifica il testo per spam patterns."""
        text_lower = text.lower()
        
        for keyword in ContentValidator.SPAM_KEYWORDS:
            if keyword in text_lower and strict:
                return False, f"Parola vietata: '{keyword}'"
        
        emoji_count = len(re.findall(ContentValidator.EMOJI_REGEX, text))
        emoji_ratio = emoji_count / len(text) if text else 0
        if emoji_ratio > ContentValidator.MAX_EMOJI_RATIO:
            return False, f"Troppi emoji ({emoji_ratio:.0%})"
        
        if text:
            caps_count = sum(1 for c in text if c.isupper())
            caps_ratio = caps_count / len(text)
            if caps_ratio > ContentValidator.MAX_CAPS_RATIO:
                return False, f"Troppi maiuscoli ({caps_ratio:.0%})"
        
        if re.search(r'(.)\1{4,}', text):
            return False, "Ripetizione eccessiva"
        
        return True, None
    
    @staticmethod
    def _check_urls(urls: List[str]) -> Tuple[bool, Optional[str]]:
        """Verifica gli URL."""
        for url in urls:
            url_lower = url.lower()
            for shortener in ContentValidator.BANNED_SHORTENERS:
                if shortener in url_lower:
                    return False, f"URL shortener vietato: {shortener}"
        return True, None


class ReputationManager:
    """Gestisce calcolo e aggiornamento della reputazione."""
    
    FACTORS = {
        "order_completed": 0.2,
        "order_cancelled_by_other": 0.1,
        "order_cancelled_by_self": -0.3,
        "dispute_lost": -0.5,
        "dispute_won": 0.3,
        "dispute_resolved_split": 0.0,
        "content_flagged": -0.2,
        "late_publication": -0.1,
        "early_removal": -0.05,
    }
    
    MIN_SCORE = 1.0
    MAX_SCORE = 5.0
    
    @classmethod
    def apply_adjustment(
        cls,
        current_score: float,
        factor_name: str,
        admin_override: Optional[float] = None
    ) -> float:
        """Applica adjustment al reputation score."""
        if admin_override is not None:
            return max(cls.MIN_SCORE, min(cls.MAX_SCORE, admin_override))
        
        adjustment = cls.FACTORS.get(factor_name, 0)
        new_score = current_score + adjustment
        return max(cls.MIN_SCORE, min(cls.MAX_SCORE, new_score))
    
    @staticmethod
    def get_rating_label(score: float) -> str:
        """Ritorna etichetta per score."""
        if score >= 4.5:
            return "⭐⭐⭐⭐⭐ Eccellente"
        elif score >= 4.0:
            return "⭐⭐⭐⭐ Molto buono"
        elif score >= 3.0:
            return "⭐⭐⭐ Buono"
        elif score >= 2.0:
            return "⭐⭐ Accettabile"
        else:
            return "⭐ Basso"


class PaymentProcessor:
    """Gestisce calcoli e processing dei pagamenti."""
    
    PLATFORM_COMMISSION_RATE = 0.10  # 10%
    
    @staticmethod
    def calculate_split(
        total_amount: float,
        commission_rate: float = PLATFORM_COMMISSION_RATE
    ) -> Tuple[float, float]:
        """Calcola divisione tra editore e piattaforma."""
        platform_fee = total_amount * commission_rate
        seller_amount = total_amount - platform_fee
        return round(seller_amount, 2), round(platform_fee, 2)


def format_currency(amount: float, currency: str = "EUR") -> str:
    """Formatta importo in valuta."""
    if currency.upper() == "EUR":
        return f"€{amount:.2f}"
    elif currency.upper() == "USD":
        return f"${amount:.2f}"
    else:
        return f"{amount:.2f} {currency}"
