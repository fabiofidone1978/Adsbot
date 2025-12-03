#!/usr/bin/env python3
"""
Integration test script for advanced features.
Tests payments, metrics, notifications, and campaign purchase flow.
"""

import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_payment_processor():
    """Test payment processor with both Stripe and PayPal."""
    logger.info("Testing PaymentProcessor...")
    
    from adsbot.payments import PaymentProcessor
    
    processor = PaymentProcessor()
    
    # Test Stripe
    logger.info("  Testing Stripe payment...")
    stripe_result = processor.process_payment(
        provider="stripe",
        amount=5000,  # $50.00
        currency="usd",
        description="Test Campaign - MyAd",
        customer_email="test@example.com"
    )
    
    if stripe_result:
        logger.info(f"    ✓ Stripe: {stripe_result.get('status', 'unknown')}")
    else:
        logger.info("    ⚠ Stripe not configured (API key not set)")
    
    # Test PayPal
    logger.info("  Testing PayPal payment...")
    paypal_result = processor.process_payment(
        provider="paypal",
        amount=50,  # $50.00
        currency="USD",
        description="Test Campaign - MyAd",
        customer_email="test@example.com",
        return_url="https://example.com/success",
        cancel_url="https://example.com/cancel"
    )
    
    if paypal_result:
        logger.info(f"    ✓ PayPal: {paypal_result.get('status', 'unknown')}")
    else:
        logger.info("    ⚠ PayPal not configured (client ID not set)")
    
    logger.info("✓ PaymentProcessor test completed\n")


async def test_notification_system():
    """Test notification system components."""
    logger.info("Testing Notification System...")
    
    from adsbot.notifications import (
        NotificationDispatcher,
        NotificationPreferences,
        NotificationType,
        NotificationLog,
    )
    
    # Test NotificationPreferences
    logger.info("  Testing NotificationPreferences...")
    prefs = NotificationPreferences()
    
    prefs.set_preference(123, NotificationType.CAMPAIGN_PURCHASED, True)
    assert prefs.is_enabled(123, NotificationType.CAMPAIGN_PURCHASED) == True
    
    prefs.set_preference(123, NotificationType.CAMPAIGN_PURCHASED, False)
    assert prefs.is_enabled(123, NotificationType.CAMPAIGN_PURCHASED) == False
    
    logger.info("    ✓ Preferences working correctly")
    
    # Test NotificationLog
    logger.info("  Testing NotificationLog...")
    log = NotificationLog()
    
    log.log_notification(123, NotificationType.CAMPAIGN_PURCHASED, "sent")
    log.log_notification(123, NotificationType.PAYMENT_RECEIVED, "sent")
    
    user_logs = log.get_user_notifications(123)
    assert len(user_logs) >= 2
    
    logger.info(f"    ✓ Logged {len(user_logs)} notifications")
    
    # Test message formatting
    logger.info("  Testing message formatting...")
    message = NotificationDispatcher._format_message(
        NotificationType.CAMPAIGN_PURCHASED,
        {
            "campaign_name": "Test Campaign",
            "channel_handle": "test_channel",
        }
    )
    
    assert "Test Campaign" in message
    assert "test_channel" in message
    
    logger.info("    ✓ Message formatting working")
    
    logger.info("✓ Notification System test completed\n")


async def test_telegram_metrics():
    """Test Telegram metrics collector structure."""
    logger.info("Testing Telegram Metrics...")
    
    from adsbot.telegram_metrics import TelegramMetricsCollector
    
    # Create a mock bot object (won't make real requests)
    class MockBot:
        async def get_chat(self, chat_id):
            raise Exception("Mock bot - no real API calls")
        
        async def get_chat_member(self, chat_id, user_id):
            raise Exception("Mock bot - no real API calls")
    
    collector = TelegramMetricsCollector(MockBot())
    
    # Verify methods exist
    assert hasattr(collector, 'get_channel_member_count')
    assert hasattr(collector, 'get_channel_info')
    assert hasattr(collector, 'get_user_member_status')
    assert hasattr(collector, 'estimate_channel_metrics')
    
    logger.info("  ✓ All metric methods defined")
    logger.info("✓ Telegram Metrics test completed (structure validation)\n")


async def test_inside_ads_services():
    """Test inside ads services functions."""
    logger.info("Testing Inside Ads Services...")
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from adsbot.models import Base, User, Channel, UserBalance
    from adsbot.inside_ads_services import (
        get_or_create_balance,
        get_user_balance,
        add_transaction,
    )
    
    # Create in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Create test user
        user = User(telegram_id=123, username="testuser")
        session.add(user)
        session.commit()
        
        logger.info("  Testing balance operations...")
        
        # Test get_or_create_balance
        balance = get_or_create_balance(session, user)
        assert balance is not None
        assert balance.user_id == user.id
        
        logger.info(f"    ✓ Created balance for user {user.id}")
        
        # Test add_transaction
        logger.info("  Testing transaction operations...")
        
        add_transaction(session, user, "earn", 50.0, "Test earn")
        balance_amount = get_user_balance(session, user)
        assert balance_amount == 50.0
        
        logger.info(f"    ✓ Added earn transaction, balance: ${balance_amount:.2f}")
        
        add_transaction(session, user, "spend", 20.0, "Test spend")
        balance_amount = get_user_balance(session, user)
        assert balance_amount == 30.0
        
        logger.info(f"    ✓ Added spend transaction, balance: ${balance_amount:.2f}")
    
    logger.info("✓ Inside Ads Services test completed\n")


async def test_purchase_campaign_flow():
    """Test purchase campaign flow structure."""
    logger.info("Testing Campaign Purchase Flow...")
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from adsbot.models import Base, User, Channel
    from adsbot.inside_ads_services import (
        list_available_channels_for_ads,
    )
    
    # Create in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Create test data
        buyer = User(telegram_id=123, username="buyer")
        seller = User(telegram_id=456, username="seller")
        
        session.add_all([buyer, seller])
        session.commit()
        
        channel = Channel(
            handle="test_channel",
            title="Test Channel",
            user_id=seller.id,
            topic="test"
        )
        
        session.add(channel)
        session.commit()
        
        logger.info("  Testing available channels...")
        
        available = list_available_channels_for_ads(session)
        assert len(available) > 0
        
        logger.info(f"    ✓ Found {len(available)} available channel(s)")
        logger.info(f"    ✓ Channel: @{available[0].handle}")
    
    logger.info("✓ Campaign Purchase Flow test completed\n")


async def main():
    """Run all integration tests."""
    logger.info("=" * 60)
    logger.info("Starting Advanced Features Integration Tests")
    logger.info("=" * 60 + "\n")
    
    try:
        await test_payment_processor()
        await test_notification_system()
        await test_telegram_metrics()
        await test_inside_ads_services()
        await test_purchase_campaign_flow()
        
        logger.info("=" * 60)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
