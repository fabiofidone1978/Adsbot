"""FASE 4-7 Integration tests for new functionality."""

import pytest
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from adsbot.db import create_session_factory
from adsbot.models import (
    User, Channel, Campaign, MarketplaceOrder, ChannelListing,
    UserRole, OrderState, OrderStatus, UserState,
    DisputeStatus, DisputeTicket
)
from adsbot.analytics import (
    EditorAnalytics, AdvertiserAnalytics, PlatformAnalytics, ReportExporter
)
from adsbot.verification import (
    IdentityVerification, RiskScorer, DisputeResolver, AccountSecurity
)
from adsbot.scheduler import SchedulerConfig
from scripts.seed_database import DatabaseSeeder


logger = logging.getLogger(__name__)


@pytest.fixture
def session():
    """Create test database session."""
    session_factory = create_session_factory()
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def test_data(session):
    """Create test data."""
    # Create users
    editor = User(
        username="test_editor",
        email="editor@test.it",
        first_name="Test",
        last_name="Editor",
        role=UserRole.EDITOR,
        state=UserState.editor_active,
        password_hash="hash",
        rating=4.5,
        rating_count=50,
        admin_verified_at=datetime.now(),
    )
    
    advertiser = User(
        username="test_advertiser",
        email="advertiser@test.it",
        first_name="Test",
        last_name="Advertiser",
        role=UserRole.ADVERTISER,
        state=UserState.advertiser_active,
        password_hash="hash",
        wallet_balance=1000.0,
    )
    
    session.add(editor)
    session.add(advertiser)
    session.commit()
    
    # Create channel
    channel = Channel(
        owner_id=editor.id,
        channel_name="TestChannel",
        telegram_channel_id="-100123456789",
        category="test",
        language="Italian",
        subscribers_count=10000,
        is_approved=True,
    )
    session.add(channel)
    session.commit()
    
    # Create channel listing
    listing = ChannelListing(
        channel_id=channel.id,
        user_id=editor.id,
        price=100.0,
        subscribers=10000,
        quality_score=0.8,
    )
    session.add(listing)
    session.commit()
    
    # Create campaign
    campaign = Campaign(
        advertiser_id=advertiser.id,
        campaign_name="TestCampaign",
        budget=1000.0,
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=30),
        is_active=True,
    )
    session.add(campaign)
    session.commit()
    
    # Create marketplace orders
    for i in range(3):
        order = MarketplaceOrder(
            seller_id=editor.id,
            buyer_id=advertiser.id,
            channel_id=channel.id,
            channel_listing_id=listing.id,
            price=100.0,
            duration_hours=24,
            status=OrderStatus.completed if i < 2 else OrderStatus.pending,
            seller_earned=70.0,
            platform_fee=30.0,
        )
        session.add(order)
    session.commit()
    
    return {
        "editor": editor,
        "advertiser": advertiser,
        "channel": channel,
        "campaign": campaign,
        "listing": listing,
    }


# ============================================================================
# FASE 4: Analytics Tests
# ============================================================================

class TestEditorAnalytics:
    """Test editor analytics functionality."""
    
    def test_editor_analytics_dashboard(self, session, test_data):
        """Test editor analytics dashboard generation."""
        editor_id = test_data["editor"].id
        
        dashboard = EditorAnalytics.editor_analytics_dashboard(session, editor_id)
        
        assert dashboard["editor_id"] == editor_id
        assert dashboard["channels_count"] == 1
        assert dashboard["total_subscribers"] == 10000
        assert dashboard["total_campaigns"] == 1
        assert dashboard["total_earnings"] > 0
        logger.info(f"Editor analytics dashboard: {dashboard}")
    
    def test_editor_earnings_report(self, session, test_data):
        """Test editor earnings report."""
        editor_id = test_data["editor"].id
        
        report = EditorAnalytics.editor_earnings_report(session, editor_id, days=30)
        
        assert report["editor_id"] == editor_id
        assert report["total_earnings"] > 0
        assert "daily_breakdown" in report
        logger.info(f"Editor earnings report total: {report['total_earnings']}")
    
    def test_editor_channel_performance(self, session, test_data):
        """Test editor channel performance analysis."""
        editor_id = test_data["editor"].id
        
        performance = EditorAnalytics.editor_channel_performance(session, editor_id)
        
        assert performance["editor_id"] == editor_id
        assert performance["channels_count"] == 1
        assert len(performance["channels"]) == 1
        logger.info(f"Channel performance metrics: {performance['channels'][0]}")


class TestAdvertiserAnalytics:
    """Test advertiser analytics functionality."""
    
    def test_advertiser_analytics_dashboard(self, session, test_data):
        """Test advertiser analytics dashboard."""
        advertiser_id = test_data["advertiser"].id
        
        dashboard = AdvertiserAnalytics.advertiser_analytics_dashboard(session, advertiser_id)
        
        assert dashboard["advertiser_id"] == advertiser_id
        assert dashboard["campaigns_total"] == 1
        assert dashboard["total_spent"] > 0
        logger.info(f"Advertiser dashboard spent: {dashboard['total_spent']}")
    
    def test_advertiser_campaign_report(self, session, test_data):
        """Test advertiser campaign report."""
        advertiser_id = test_data["advertiser"].id
        
        report = AdvertiserAnalytics.advertiser_campaign_report(session, advertiser_id)
        
        assert report["advertiser_id"] == advertiser_id
        assert report["campaigns_count"] == 1
        assert len(report["campaigns"]) == 1
        logger.info(f"Campaign report: {report['campaigns'][0]}")


class TestPlatformAnalytics:
    """Test platform-wide analytics."""
    
    def test_platform_dashboard_stats(self, session, test_data):
        """Test platform dashboard statistics."""
        stats = PlatformAnalytics.platform_dashboard_stats(session)
        
        assert "users" in stats
        assert "channels" in stats
        assert "campaigns" in stats
        assert "orders" in stats
        assert stats["users"]["total"] >= 2
        logger.info(f"Platform stats: {stats}")


class TestReportExporter:
    """Test report export functionality."""
    
    def test_csv_header_generation(self):
        """Test CSV header generation."""
        header = ReportExporter.export_csv_header("editor_earnings")
        
        assert "Date" in header
        assert "Earnings" in header
    
    def test_text_report_generation(self):
        """Test text report generation."""
        test_data = {
            "total_users": 100,
            "total_revenue": 5000.0,
            "nested": {"value": 123}
        }
        
        report = ReportExporter.generate_text_report(test_data, "Test Report")
        
        assert "Test Report" in report
        assert "total_users: 100" in report
        assert "5000" in report


# ============================================================================
# FASE 5: Scheduler Configuration Tests
# ============================================================================

class TestSchedulerConfig:
    """Test scheduler configuration."""
    
    def test_scheduler_config_jobs(self):
        """Test scheduler has all required jobs configured."""
        required_jobs = [
            "order_expiration",
            "order_timeout",
            "metrics_update",
            "daily_report",
            "dispute_auto_resolve",
            "campaign_expiration"
        ]
        
        for job in required_jobs:
            assert job in SchedulerConfig.JOBS
            assert "job_func" in SchedulerConfig.JOBS[job]
            assert "trigger" in SchedulerConfig.JOBS[job]
        
        logger.info(f"Scheduler has {len(SchedulerConfig.JOBS)} configured jobs")


# ============================================================================
# FASE 6: Verification & Risk Tests
# ============================================================================

class TestIdentityVerification:
    """Test identity verification system."""
    
    def test_start_verification(self, session, test_data):
        """Test starting verification process."""
        editor_id = test_data["editor"].id
        
        verification_data = {
            "full_name": "Test Editor",
            "date_of_birth": "1990-01-01",
            "country": "Italy",
            "document_type": "passport",
            "document_number": "AB123456",
        }
        
        result = IdentityVerification.start_verification(session, editor_id, verification_data)
        
        assert result["status"] == "pending"
        assert result["user_id"] == editor_id
        logger.info(f"Verification started: {result}")
    
    def test_verify_user(self, session, test_data):
        """Test admin verification approval."""
        editor = test_data["editor"]
        admin = User(
            username="admin",
            email="admin@test.it",
            role=UserRole.ADMIN,
            password_hash="hash",
        )
        session.add(admin)
        session.commit()
        
        result = IdentityVerification.verify_user(
            session, editor.id, admin.id, approved=True, notes="Approved"
        )
        
        assert result["status"] == "approved"
        assert result["user_id"] == editor.id


class TestRiskScorer:
    """Test risk scoring system."""
    
    def test_calculate_risk_score(self, session, test_data):
        """Test risk score calculation."""
        editor_id = test_data["editor"].id
        
        risk = RiskScorer.calculate_risk_score(session, editor_id)
        
        assert "risk_score" in risk
        assert "risk_level" in risk
        assert risk["user_id"] == editor_id
        assert risk["risk_score"] >= 0
        logger.info(f"Risk score: {risk['risk_score']} ({risk['risk_level']})")
    
    def test_flag_suspicious_activity(self, session, test_data):
        """Test suspicious activity flagging."""
        editor_id = test_data["editor"].id
        
        result = RiskScorer.flag_suspicious_activity(
            session, editor_id, "rapid_orders", {"count": 50, "period": "1h"}
        )
        
        assert result["status"] == "flagged"
        logger.info(f"Activity flagged: {result}")

class TestDisputeResolver:
    """Test dispute resolution system."""
    
    def test_analyze_dispute(self, session, test_data):
        """Test dispute analysis."""
        # Create a dispute
        order = session.query(MarketplaceOrder).filter(MarketplaceOrder.buyer_id == test_data["advertiser"].id).first()
        
        dispute = DisputeTicket(
            order_id=order.id,
            initiator_id=test_data["editor"].id,
            initiator_role="editor",
            description="Test dispute",
            status=DisputeStatus.open,
        )
        session.add(dispute)
        session.commit()
        
        analysis = DisputeResolver.analyze_dispute(session, dispute.id)
        
        assert "fraud_score" in analysis
        assert "recommendation" in analysis
        assert analysis["dispute_id"] == dispute.id
        logger.info(f"Dispute analysis: {analysis}")

# ============================================================================
# FASE 7: Seed Data Tests
# ============================================================================

class TestDatabaseSeeder:
    """Test database seeding functionality."""
    
    def test_seeder_creates_data(self, session):
        """Test that seeder creates appropriate data."""
        stats = DatabaseSeeder.seed_database(
            session,
            num_editors=2,
            num_advertisers=2,
            num_campaigns_per_advertiser=1,
            num_orders_per_campaign=1
        )
        
        assert stats["users"] >= 4  # At least 2 editors + 2 advertisers
        assert stats["channels"] >= 2
        assert stats["campaigns"] >= 2
        assert stats["orders"] >= 1
        
        logger.info(f"Seeder created: {stats}")


# ============================================================================
# Integration Tests
# ============================================================================

class TestFase47Integration:
    """Integration tests for FASE 4-7."""
    
    def test_complete_workflow(self, session, test_data):
        """Test complete workflow: analytics -> verification -> risk -> dispute."""
        editor_id = test_data["editor"].id
        advertiser_id = test_data["advertiser"].id
        
        # Step 1: Analytics
        editor_dashboard = EditorAnalytics.editor_analytics_dashboard(session, editor_id)
        assert editor_dashboard["total_earnings"] > 0
        
        # Step 2: Verification
        verify_result = IdentityVerification.verify_user(session, editor_id, 1, approved=True)
        assert verify_result["status"] == "approved"
        
        # Step 3: Risk Scoring
        risk = RiskScorer.calculate_risk_score(session, editor_id)
        assert "risk_level" in risk
        
        # Step 4: Advertiser Analytics
        advertiser_dashboard = AdvertiserAnalytics.advertiser_analytics_dashboard(session, advertiser_id)
        assert advertiser_dashboard["total_spent"] > 0
        
        logger.info("Complete workflow test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
