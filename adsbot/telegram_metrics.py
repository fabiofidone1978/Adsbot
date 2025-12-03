"""Fetch real metrics from Telegram API."""

from __future__ import annotations

import logging
from typing import Optional

from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramMetricsCollector:
    """Collect real metrics from Telegram channels."""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def get_channel_member_count(self, channel_username: str) -> Optional[int]:
        """Get member count for a channel."""
        try:
            chat = await self.bot.get_chat(f"@{channel_username}")
            return chat.get_member_count()
        except TelegramError as e:
            logger.error(f"Error fetching member count for {channel_username}: {e}")
            return None

    async def get_channel_info(self, channel_username: str) -> Optional[dict]:
        """Get detailed channel information."""
        try:
            chat = await self.bot.get_chat(f"@{channel_username}")
            return {
                "id": chat.id,
                "title": chat.title,
                "members": chat.get_member_count(),
                "description": chat.description,
                "type": chat.type,
            }
        except TelegramError as e:
            logger.error(f"Error fetching channel info for {channel_username}: {e}")
            return None

    async def get_user_member_status(self, channel_username: str, user_id: int) -> Optional[str]:
        """Check if user is member of channel."""
        try:
            status = await self.bot.get_chat_member(f"@{channel_username}", user_id)
            return status.status  # "member", "administrator", "creator", "left", "kicked"
        except TelegramError as e:
            logger.warning(f"Error checking membership for user {user_id} in {channel_username}: {e}")
            return None

    async def get_chat_administrators(self, channel_username: str) -> Optional[list]:
        """Get list of administrators."""
        try:
            admins = await self.bot.get_chat_administrators(f"@{channel_username}")
            return [{"id": a.user.id, "username": a.user.username} for a in admins]
        except TelegramError as e:
            logger.error(f"Error fetching admins for {channel_username}: {e}")
            return None

    async def estimate_channel_metrics(
        self, channel_username: str, user_id: int
    ) -> Optional[dict]:
        """Estimate channel metrics (members, potential reach, etc.)."""
        try:
            # Get basic info
            chat = await self.bot.get_chat(f"@{channel_username}")
            member_count = chat.get_member_count()

            # Check user status
            member_status = await self.get_user_member_status(channel_username, user_id)

            return {
                "channel": channel_username,
                "members": member_count,
                "user_is_member": member_status in ("member", "administrator", "creator"),
                "estimated_reach": int(member_count * 0.6),  # Assume 60% engagement
                "is_channel": chat.type in ("channel", "supergroup"),
            }
        except TelegramError as e:
            logger.error(f"Error estimating metrics for {channel_username}: {e}")
            return None
