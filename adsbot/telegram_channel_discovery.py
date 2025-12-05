"""Telegram channel discovery using Pyrogram Client API.

This module discovers channels where the user is an administrator
by querying the Telegram client directly (not through bot API).
"""

import logging
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class TelegramChannelDiscovery:
    """Discover Telegram channels where user is admin using Pyrogram."""
    
    def __init__(self, session_name: str = "adsbot_discovery", api_id: Optional[int] = None, api_hash: Optional[str] = None):
        """
        Initialize Pyrogram client for channel discovery.
        
        Args:
            session_name: Name of the session file
            api_id: Telegram API ID (from my.telegram.org)
            api_hash: Telegram API Hash (from my.telegram.org)
        """
        self.session_name = session_name
        self.api_id = api_id or self._get_api_id()
        self.api_hash = api_hash or self._get_api_hash()
        self.client = None
    
    def _get_api_id(self) -> int:
        """Get API ID from config or environment."""
        try:
            from .config import Config
            return Config.TELEGRAM_API_ID or 0
        except Exception:
            return int(__import__('os').getenv('TELEGRAM_API_ID', '0'))
    
    def _get_api_hash(self) -> str:
        """Get API Hash from config or environment."""
        try:
            from .config import Config
            return Config.TELEGRAM_API_HASH or ""
        except Exception:
            return __import__('os').getenv('TELEGRAM_API_HASH', "")
    
    async def discover_admin_channels(self) -> List[Dict]:
        """
        Discover all channels where the user is an administrator.
        
        Returns:
            List of dicts with channel info: {
                'id': chat_id,
                'title': str,
                'username': str or None,
                'description': str or None,
                'members_count': int,
                'is_admin': bool
            }
        """
        admin_channels = []
        
        if not self.api_id or not self.api_hash:
            logger.warning("API ID or API Hash not configured for channel discovery")
            return []
        
        try:
            from pyrogram import Client
            
            # Create temporary client for discovery
            async with Client(
                name=self.session_name,
                api_id=self.api_id,
                api_hash=self.api_hash,
                in_memory=True  # Don't persist session
            ) as client:
                
                logger.info("Querying Telegram for admin channels...")
                
                # Get all dialogs
                async for dialog in client.get_dialogs():
                    chat = dialog.chat
                    
                    # Filter only channels and supergroups
                    if chat.type not in ["channel", "supergroup"]:
                        continue
                    
                    # Check if user is admin
                    try:
                        member = await client.get_chat_member(chat.id, "self")
                        
                        # Check if admin
                        if member.privileges and (
                            member.privileges.can_manage_chat or
                            member.privileges.is_admin
                        ):
                            admin_channels.append({
                                "id": chat.id,
                                "title": chat.title or "Canale senza nome",
                                "username": chat.username or None,
                                "description": chat.description or None,
                                "members_count": chat.members_count or 0,
                                "is_admin": True
                            })
                            logger.info(f"Found admin channel: {chat.title} (@{chat.username})")
                    
                    except Exception as e:
                        logger.debug(f"Could not check membership for {chat.title}: {e}")
                        continue
        
        except ImportError:
            logger.error("Pyrogram not available for channel discovery")
            return []
        except Exception as e:
            logger.error(f"Error discovering admin channels: {e}")
            return []
        
        logger.info(f"Discovery complete: found {len(admin_channels)} admin channels")
        return admin_channels
    
    async def search_channel_by_username(self, username: str) -> Optional[Dict]:
        """
        Search for a specific channel by username.
        
        Args:
            username: Channel username (with or without @)
            
        Returns:
            Channel info dict or None if not found/not admin
        """
        if not self.api_id or not self.api_hash:
            logger.warning("API ID or API Hash not configured")
            return None
        
        # Normalize username
        username = username.lstrip("@").lower()
        
        try:
            from pyrogram import Client
            
            async with Client(
                name=self.session_name,
                api_id=self.api_id,
                api_hash=self.api_hash,
                in_memory=True
            ) as client:
                
                # Try to get chat by username
                try:
                    chat = await client.get_chat(f"@{username}")
                    
                    # Check if user is admin
                    member = await client.get_chat_member(chat.id, "self")
                    
                    if member.privileges and (
                        member.privileges.can_manage_chat or
                        member.privileges.is_admin
                    ):
                        return {
                            "id": chat.id,
                            "title": chat.title or username,
                            "username": chat.username or username,
                            "description": chat.description or None,
                            "members_count": chat.members_count or 0,
                            "is_admin": True
                        }
                    else:
                        logger.warning(f"User is not admin in @{username}")
                        return None
                
                except Exception as e:
                    logger.error(f"Could not find channel @{username}: {e}")
                    return None
        
        except ImportError:
            logger.error("Pyrogram not available")
            return None
        except Exception as e:
            logger.error(f"Error searching channel: {e}")
            return None


__all__ = ["TelegramChannelDiscovery"]
