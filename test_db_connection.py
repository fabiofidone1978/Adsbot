#!/usr/bin/env python
"""Quick test to verify bot starts and database works."""

import logging
from adsbot.config import Config
from adsbot.db import create_session_factory, session_scope
from adsbot.services import ensure_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("🧪 Testing bot database connectivity...")
    
    config = Config.load()
    session_factory = create_session_factory(config)
    
    # Test 1: Create a session
    logger.info("✅ Session factory created")
    
    # Test 2: Try ensure_user (the function that was failing)
    try:
        with session_scope(session_factory) as session:
            # Simulate a user query
            user = ensure_user(session, telegram_id=123456789, username="test_user", first_name="Test", language_code="en")
            logger.info(f"✅ User created/retrieved: ID={user.id}, role={user.role}, state={user.state}")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    
    logger.info("\n✨ All tests passed! Database is working correctly.")
