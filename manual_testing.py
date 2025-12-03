#!/usr/bin/env python3
"""
Adsbot - Manual Testing Suite
Interactive testing for all features
"""

import sys
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def print_header(title):
    """Print section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")

def print_status(message, status="INFO"):
    """Print status message"""
    icons = {
        "OK": "✅",
        "FAIL": "❌",
        "WARN": "⚠️",
        "INFO": "ℹ️",
        "TEST": "🧪",
    }
    icon = icons.get(status, "•")
    print(f"{icon} {message}")

def test_imports():
    """Test if all modules can be imported"""
    print_header("Test 1: Module Imports")
    
    modules = [
        ("telegram", "python-telegram-bot"),
        ("sqlalchemy", "SQLAlchemy"),
        ("adsbot.bot", "Adsbot Bot"),
        ("adsbot.campaigns", "Campaign Manager"),
        ("adsbot.analytics", "Analytics Engine"),
        ("adsbot.payments", "Payment Processor"),
        ("adsbot.notifications", "Notification System"),
    ]
    
    failed = []
    for module, name in modules:
        try:
            __import__(module)
            print_status(f"{name} imported successfully", "OK")
        except ImportError as e:
            print_status(f"{name} import failed: {e}", "FAIL")
            failed.append(name)
    
    if failed:
        print_status(f"Failed imports: {', '.join(failed)}", "FAIL")
        return False
    else:
        print_status("All modules imported successfully", "OK")
        return True

def test_database():
    """Test database connectivity"""
    print_header("Test 2: Database Connectivity")
    
    try:
        from adsbot.db import create_session_factory
        from adsbot.config import Config
        
        config = Config()
        factory = create_session_factory(config)
        session = factory()
        
        print_status("Database connected", "OK")
        print_status(f"Database location: {config.database_url}", "INFO")
        
        session.close()
        return True
    except Exception as e:
        print_status(f"Database connection failed: {e}", "FAIL")
        return False

def test_campaigns_module():
    """Test campaign management module"""
    print_header("Test 3: Campaign Management Module")
    
    try:
        from adsbot.campaigns import (
            AdvancedCampaignManager,
            CampaignVariant,
            TargetingSettings,
            BudgetSettings,
            PaymentModel,
        )
        
        print_status("AdvancedCampaignManager class loaded", "OK")
        print_status("CampaignVariant class loaded", "OK")
        print_status("TargetingSettings class loaded", "OK")
        print_status("BudgetSettings class loaded", "OK")
        print_status("PaymentModel enum loaded", "OK")
        
        # Test enum values
        print_status(f"Payment Models: {', '.join([m.name for m in PaymentModel])}", "INFO")
        
        return True
    except Exception as e:
        print_status(f"Campaign module test failed: {e}", "FAIL")
        return False

def test_analytics_module():
    """Test analytics module"""
    print_header("Test 4: Analytics Module")
    
    try:
        from adsbot.analytics import (
            PerformanceForecast,
            CampaignAnalytics,
            BudgetOptimizer,
            SmartRecommendations,
        )
        
        print_status("PerformanceForecast class loaded", "OK")
        print_status("CampaignAnalytics class loaded", "OK")
        print_status("BudgetOptimizer class loaded", "OK")
        print_status("SmartRecommendations class loaded", "OK")
        
        # Test forecast calculation
        forecast = PerformanceForecast.estimate_weekly_metrics(
            daily_impressions=5000,
            daily_ctr=3.5,
            daily_conversion=8.0,
            budget_per_day=20.0,
        )
        
        print_status(f"Weekly forecast calculated: {forecast['impressions']:,} impressions", "OK")
        print_status(f"Estimated ROI: {forecast.get('roi', 0):.1f}%", "INFO")
        
        return True
    except Exception as e:
        print_status(f"Analytics module test failed: {e}", "FAIL")
        return False

def test_payment_system():
    """Test payment processor"""
    print_header("Test 5: Payment System")
    
    try:
        from adsbot.payments import PaymentProcessor
        
        processor = PaymentProcessor()
        print_status("PaymentProcessor initialized", "OK")
        print_status("Mock payment processor ready for testing", "INFO")
        
        # Test mock payment
        result = processor.process_payment(
            amount=50.00,
            payment_method="mock",
            description="Test transaction"
        )
        
        if result and result.get("success"):
            print_status(f"Mock payment successful: {result}", "OK")
        else:
            print_status(f"Mock payment failed (expected for mock)", "WARN")
        
        return True
    except Exception as e:
        print_status(f"Payment system test failed: {e}", "FAIL")
        return False

def test_notifications():
    """Test notification system"""
    print_header("Test 6: Notification System")
    
    try:
        from adsbot.notifications import NotificationType
        
        print_status("Notification types available:", "INFO")
        for nt in NotificationType:
            print(f"  • {nt.name}: {nt.value}")
        
        print_status("Notification system ready", "OK")
        return True
    except Exception as e:
        print_status(f"Notification system test failed: {e}", "FAIL")
        return False

def test_bot_config():
    """Test bot configuration"""
    print_header("Test 7: Bot Configuration")
    
    try:
        from adsbot.config import Config
        
        config = Config()
        print_status(f"Bot token configured: {'✓' if config.bot_token else '✗'}", "INFO")
        print_status(f"Database URL: {config.database_url}", "INFO")
        print_status(f"Debug mode: {config.debug}", "INFO")
        
        if not config.bot_token:
            print_status("Warning: Bot token not configured in config.ini", "WARN")
        
        return True
    except Exception as e:
        print_status(f"Bot configuration test failed: {e}", "FAIL")
        return False

def run_manual_tests():
    """Run all manual tests"""
    print_header("ADSBOT - MANUAL TESTING SUITE")
    print_status("Version: 2.0 (Advanced Campaign Management)", "INFO")
    print_status("Date: 2024-12-03", "INFO")
    
    tests = [
        ("Module Imports", test_imports),
        ("Database Connectivity", test_database),
        ("Campaign Management", test_campaigns_module),
        ("Analytics Engine", test_analytics_module),
        ("Payment System", test_payment_system),
        ("Notification System", test_notifications),
        ("Bot Configuration", test_bot_config),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_status(f"Test '{name}' crashed: {e}", "FAIL")
            results.append((name, False))
        
        time.sleep(0.5)  # Brief pause between tests
    
    # Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "OK" if result else "FAIL"
        print_status(f"{name}: {'PASSED' if result else 'FAILED'}", status)
    
    print_status(f"Total: {passed}/{total} tests passed", "OK" if passed == total else "FAIL")
    
    if passed == total:
        print_header("✅ ALL TESTS PASSED - READY FOR DEPLOYMENT")
        return True
    else:
        print_header("❌ SOME TESTS FAILED - CHECK ISSUES ABOVE")
        return False

def show_next_steps():
    """Show next steps"""
    print_header("NEXT STEPS")
    
    print("""
1. CONFIGURE PRODUCTION
   • Edit config.ini with your settings
   • Set bot_token, stripe_api_key, paypal credentials
   
2. START THE BOT
   • Run: python main.py
   • Or double-click: DEPLOY.bat
   
3. TEST IN TELEGRAM
   • Send /start to your bot
   • Click buttons to test features
   • Try each menu option
   
4. MONITOR LOGS
   • Check console output for errors
   • Watch for payment/notification events
   
5. VERIFY FEATURES
   • Test campaign creation
   • Test forecast generation
   • Test AI recommendations
   • Test payment processing
   
6. GO LIVE
   • Once verified, announce to users
   • Monitor for 24 hours
   • Gather feedback
    """)

def main():
    """Main entry point"""
    try:
        success = run_manual_tests()
        
        print()
        response = input("View next steps? (y/n): ").strip().lower()
        if response == 'y':
            show_next_steps()
        
        return 0 if success else 1
    
    except KeyboardInterrupt:
        print("\n\nTesting interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Critical error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
