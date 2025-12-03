"""Notification system for Inside Ads transactions and events."""

import logging
from enum import Enum
from typing import Optional
from datetime import datetime

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications."""

    CAMPAIGN_PURCHASED = "campaign_purchased"
    CAMPAIGN_EARNED = "campaign_earned"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    WITHDRAWAL_SUCCESS = "withdrawal_success"
    WITHDRAWAL_FAILED = "withdrawal_failed"
    NEW_OFFER = "new_offer"
    OFFER_ACCEPTED = "offer_accepted"


class NotificationDispatcher:
    """Handles sending notifications to users."""

    def __init__(self, bot: Bot):
        """Initialize with Telegram bot instance."""
        self.bot = bot

    async def send_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        data: dict,
    ) -> bool:
        """Send a notification to user."""
        try:
            message = self._format_message(notification_type, data)
            if not message:
                return False

            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.HTML,
            )
            logger.info(f"Notification sent to {user_id}: {notification_type.value}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send notification to {user_id}: {e}")
            return False

    @staticmethod
    def _format_message(notification_type: NotificationType, data: dict) -> Optional[str]:
        """Format notification message based on type."""
        if notification_type == NotificationType.CAMPAIGN_PURCHASED:
            campaign_name = data.get("campaign_name", "Unknown")
            channel_handle = data.get("channel_handle", "Unknown")
            return (
                f"✅ <b>Campaign Purchased!</b>\n\n"
                f"Campaign: {campaign_name}\n"
                f"Channel: {channel_handle}\n"
                f"Your ads are now live!"
            )

        elif notification_type == NotificationType.CAMPAIGN_EARNED:
            amount = data.get("amount", 0)
            channel_handle = data.get("channel_handle", "Unknown")
            return (
                f"💰 <b>Earnings Received!</b>\n\n"
                f"Channel: {channel_handle}\n"
                f"Amount: ${amount:.2f}\n"
                f"Your audience is growing your income!"
            )

        elif notification_type == NotificationType.PAYMENT_RECEIVED:
            amount = data.get("amount", 0)
            provider = data.get("provider", "payment processor")
            return (
                f"✅ <b>Payment Confirmed!</b>\n\n"
                f"Amount: ${amount:.2f}\n"
                f"Provider: {provider}\n"
                f"Status: Successfully processed"
            )

        elif notification_type == NotificationType.PAYMENT_FAILED:
            amount = data.get("amount", 0)
            reason = data.get("reason", "Unknown reason")
            return (
                f"❌ <b>Payment Failed!</b>\n\n"
                f"Amount: ${amount:.2f}\n"
                f"Reason: {reason}\n"
                f"Please try again."
            )

        elif notification_type == NotificationType.WITHDRAWAL_SUCCESS:
            amount = data.get("amount", 0)
            account = data.get("account", "your account")
            return (
                f"✅ <b>Withdrawal Successful!</b>\n\n"
                f"Amount: ${amount:.2f}\n"
                f"To: {account}\n"
                f"Transaction ID: {data.get('transaction_id', 'N/A')}"
            )

        elif notification_type == NotificationType.WITHDRAWAL_FAILED:
            amount = data.get("amount", 0)
            reason = data.get("reason", "Unknown reason")
            return (
                f"❌ <b>Withdrawal Failed!</b>\n\n"
                f"Amount: ${amount:.2f}\n"
                f"Reason: {reason}\n"
                f"Please contact support."
            )

        elif notification_type == NotificationType.NEW_OFFER:
            offer_name = data.get("offer_name", "Unknown")
            offered_by = data.get("offered_by", "Unknown user")
            return (
                f"📢 <b>New Offer!</b>\n\n"
                f"Offer: {offer_name}\n"
                f"From: {offered_by}\n"
                f"Check the offers section to view details."
            )

        elif notification_type == NotificationType.OFFER_ACCEPTED:
            offer_name = data.get("offer_name", "Unknown")
            accepted_by = data.get("accepted_by", "Unknown user")
            return (
                f"✅ <b>Offer Accepted!</b>\n\n"
                f"Offer: {offer_name}\n"
                f"By: {accepted_by}\n"
                f"Great news! Your offer has been accepted."
            )

        return None


class NotificationPreferences:
    """Manages user notification preferences (could be extended with DB storage)."""

    def __init__(self):
        """Initialize preferences storage."""
        self.user_preferences = {}

    def set_preference(self, user_id: int, notification_type: NotificationType, enabled: bool):
        """Enable or disable specific notification type for user."""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        self.user_preferences[user_id][notification_type] = enabled

    def is_enabled(self, user_id: int, notification_type: NotificationType) -> bool:
        """Check if notification type is enabled for user."""
        if user_id not in self.user_preferences:
            return True  # Default: all enabled
        return self.user_preferences[user_id].get(notification_type, True)

    def toggle_all(self, user_id: int, enabled: bool):
        """Enable/disable all notifications for user."""
        self.user_preferences[user_id] = {ntype: enabled for ntype in NotificationType}


class NotificationLog:
    """Simple in-memory log of sent notifications (would use DB in production)."""

    def __init__(self):
        """Initialize log storage."""
        self.logs = []

    def log_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        status: str = "sent",
    ):
        """Log a notification event."""
        self.logs.append(
            {
                "user_id": user_id,
                "type": notification_type.value,
                "status": status,
                "timestamp": datetime.now(),
            }
        )

    def get_user_notifications(self, user_id: int, limit: int = 50) -> list[dict]:
        """Get recent notifications for a user."""
        user_logs = [log for log in self.logs if log["user_id"] == user_id]
        return sorted(
            user_logs,
            key=lambda x: x["timestamp"],
            reverse=True,
        )[:limit]
