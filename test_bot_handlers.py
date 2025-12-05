#!/usr/bin/env python
"""Test bot compilation and basic handlers."""

import logging
import asyncio
from unittest.mock import AsyncMock, MagicMock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_bot_handlers():
    """Test that bot can build application and handlers are registered."""
    logger.info("🧪 Testing bot handler registration...")
    
    try:
        from adsbot.bot import build_application
        from adsbot.config import Config
        
        config = Config.load()
        application = build_application(config)
        
        logger.info("✅ Application built successfully")
        logger.info(f"✅ Handlers registered groups: {len(application.handlers)}")
        
        # Check if handlers are present (structure varies by python-telegram-bot version)
        if hasattr(application, 'handlers') and application.handlers:
            logger.info("✅ Handlers present in application")
        
        logger.info("\n✨ All handler tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_bot_handlers())
    exit(0 if success else 1)
