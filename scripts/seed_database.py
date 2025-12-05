"""FASE 7: Database seed script for test data generation."""

import logging
from datetime import datetime, timedelta
import random
from typing import List, Dict

from sqlalchemy.orm import Session


from adsbot.models import (
    User, Channel, Campaign, MarketplaceOrder, BroadcastTemplate, DisputeTicket,
    UserRole, UserState, ChannelState, OrderState, DisputeStatus,
    PaymentStatus, OfferType
)
from adsbot.db import create_session_factory

logger = logging.getLogger(__name__)


class DatabaseSeeder:
    """Generate realistic test data for development and testing."""
    
    ITALIAN_CHANNELS = [
        "TechDaily", "GadgetReviews", "LifestyleIT", "FitnessITA", 
        "CookingChannel", "TravelVlog", "GamingPro", "BeautyTips",
        "MusicLounge", "EducationHub", "NewsToday", "EntertainmentZone",
        "SportsFans", "CarChannel", "BusinessInsights", "DIYChannel"
    ]
    
    CATEGORIES = ["technology", "lifestyle", "gaming", "beauty", "food", "travel", "sports", "news"]
    
    ADVERTISER_COMPANIES = [
        "TechCorp Ltd", "Fashion World", "Electronics Plus", "Health Pro",
        "Online Store", "Software Solutions", "Gaming Hub", "Food Delivery",
        "Travel Agency", "Fitness Club", "Beauty Studio", "Car Rental",
        "Insurance Co", "Bank Services", "E-Learning Pro", "Mobile Shop"
    ]
    
    CAMPAIGN_TYPES = [
        "Product Launch", "Brand Awareness", "Traffic Generation",
        "Lead Generation", "Conversion Campaign", "Seasonal Promotion",
        "App Download", "Event Promotion"
    ]
    
    @staticmethod
    def seed_database(session: Session, num_editors: int = 10, num_advertisers: int = 10,
                     num_campaigns_per_advertiser: int = 2, num_orders_per_campaign: int = 3) -> Dict:
        """Generate complete test dataset.
        
        Args:
            session: Database session
            num_editors: Number of editor users to create
            num_advertisers: Number of advertiser users to create
            num_campaigns_per_advertiser: Campaigns per advertiser
            num_orders_per_campaign: Orders per campaign
            
        Returns:
            Summary of created data
        """
        try:
            logger.info("Starting database seeding...")
            
            stats = {
                "users": 0,
                "channels": 0,
                "campaigns": 0,
                "orders": 0,
                "disputes": 0,
                "templates": 0,
                "total_time": 0,
            }
            
            start_time = datetime.now()
            
            # Clear existing data (optional, uncomment to reset)
            # session.query(Order).delete()
            # session.query(Dispute).delete()
            # session.query(Campaign).delete()
            # session.query(BroadcastTemplate).delete()
            # session.query(Channel).delete()
            # session.query(User).delete()
            # session.commit()
            
            # 1. Create Editor Users
            logger.info(f"Creating {num_editors} editor users...")
            editors = DatabaseSeeder._create_editors(session, num_editors)
            stats["users"] += len(editors)
            
            # 2. Create Channels for Editors
            logger.info(f"Creating channels for editors...")
            channels = DatabaseSeeder._create_channels(session, editors)
            stats["channels"] += len(channels)
            
            # 3. Create Advertiser Users
            logger.info(f"Creating {num_advertisers} advertiser users...")
            advertisers = DatabaseSeeder._create_advertisers(session, num_advertisers)
            stats["users"] += len(advertisers)
            
            # 4. Create Campaigns for Advertisers
            logger.info(f"Creating campaigns...")
            campaigns = DatabaseSeeder._create_campaigns(
                session, advertisers, num_campaigns_per_advertiser
            )
            stats["campaigns"] += len(campaigns)
            
            # 5. Create Orders (Channel x Campaign interactions)
            logger.info(f"Creating orders...")
            orders = DatabaseSeeder._create_orders(
                session, channels, campaigns, num_orders_per_campaign
            )
            stats["orders"] += len(orders)
            
            # 6. Create Broadcast Templates
            logger.info(f"Creating broadcast templates...")
            templates = DatabaseSeeder._create_templates(session, channels)
            stats["templates"] += len(templates)
            
            # 7. Create some Disputes (for realistic data)
            logger.info(f"Creating disputes...")
            disputes = DatabaseSeeder._create_disputes(session, orders)
            stats["disputes"] += len(disputes)
            
            stats["total_time"] = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Database seeding complete in {stats['total_time']:.2f}s")
            logger.info(f"Created: {stats['users']} users, {stats['channels']} channels, "
                       f"{stats['campaigns']} campaigns, {stats['orders']} orders, "
                       f"{stats['disputes']} disputes, {stats['templates']} templates")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error seeding database: {e}")
            session.rollback()
            raise
    
    @staticmethod
    def _create_editors(session: Session, count: int) -> List[User]:
        """Create editor users with realistic data."""
        editors = []
        
        for i in range(count):
            editor = User(
                username=f"editor_{i+1}",
                email=f"editor{i+1}@example.it",
                phone_number=f"+39{random.randint(100, 999)}{random.randint(100, 999)}{random.randint(1000, 9999)}",
                first_name=f"Editor{i+1}",
                last_name=f"Channel{i+1}",
                role=UserRole.editor,
                state=UserState.editor_active if i % 3 != 0 else UserState.editor_registering,
                password_hash="hashed_password_placeholder",
                rating=round(random.uniform(3.5, 5.0), 2),
                rating_count=random.randint(10, 200),
                admin_verified_at=datetime.now() - timedelta(days=random.randint(30, 200)) if i % 3 != 2 else None,
                is_suspended=False if i % 5 != 0 else True,
                created_at=datetime.now() - timedelta(days=random.randint(10, 365)),
            )
            session.add(editor)
            editors.append(editor)
        
        session.commit()
        return editors
    
    @staticmethod
    def _create_channels(session: Session, editors: List[User]) -> List[Channel]:
        """Create channels for editors."""
        channels = []
        
        for editor in editors:
            # Each editor gets 1-3 channels
            num_channels = random.randint(1, 3)
            
            for j in range(num_channels):
                channel_name = f"{DatabaseSeeder.ITALIAN_CHANNELS[random.randint(0, len(DatabaseSeeder.ITALIAN_CHANNELS)-1)]}{j+1}"
                
                channel = Channel(
                    owner_id=editor.id,
                    channel_name=channel_name,
                    telegram_channel_id=f"-100{random.randint(10000000, 99999999)}",
                    description=f"Italian channel about {random.choice(DatabaseSeeder.CATEGORIES)}",
                    category=random.choice(DatabaseSeeder.CATEGORIES),
                    language="Italian",
                    subscribers_count=random.randint(1000, 100000),
                    is_approved=random.random() > 0.2,  # 80% approved
                    state=ChannelState.ACTIVE if random.random() > 0.1 else ChannelState.SUSPENDED,
                    created_at=datetime.now() - timedelta(days=random.randint(10, 365)),
                )
                session.add(channel)
                channels.append(channel)
        
        session.commit()
        return channels
    
    @staticmethod
    def _create_advertisers(session: Session, count: int) -> List[User]:
        """Create advertiser users."""
        advertisers = []
        
        for i in range(count):
            advertiser = User(
                username=f"advertiser_{i+1}",
                email=f"advertiser{i+1}@company.it",
                phone_number=f"+39{random.randint(100, 999)}{random.randint(100, 999)}{random.randint(1000, 9999)}",
                first_name=DatabaseSeeder.ADVERTISER_COMPANIES[i % len(DatabaseSeeder.ADVERTISER_COMPANIES)],
                last_name="Company",
                role=UserRole.advertiser,
                state=UserState.advertiser_active,
                password_hash="hashed_password_placeholder",
                wallet_balance=random.uniform(100, 5000),
                admin_verified_at=datetime.now() - timedelta(days=random.randint(30, 200)) if i % 2 == 0 else None,
                is_suspended=False,
                created_at=datetime.now() - timedelta(days=random.randint(10, 365)),
            )
            session.add(advertiser)
            advertisers.append(advertiser)
        
        session.commit()
        return advertisers
    
    @staticmethod
    def _create_campaigns(session: Session, advertisers: List[User], campaigns_per_advertiser: int) -> List[Campaign]:
        """Create campaigns for advertisers."""
        campaigns = []
        
        for advertiser in advertisers:
            for j in range(campaigns_per_advertiser):
                start_date = datetime.now()
                duration_days = random.randint(7, 90)
                
                campaign = Campaign(
                    advertiser_id=advertiser.id,
                    campaign_name=f"{advertiser.first_name} {random.choice(DatabaseSeeder.CAMPAIGN_TYPES)} {j+1}",
                    description=f"Campaign targeting {random.choice(DatabaseSeeder.CATEGORIES)} channels",
                    budget=random.uniform(100, 5000),
                    start_date=start_date,
                    end_date=start_date + timedelta(days=duration_days),
                    is_active=random.random() > 0.3,  # 70% active
                    created_at=start_date - timedelta(days=random.randint(0, 10)),
                )
                session.add(campaign)
                campaigns.append(campaign)
        
        session.commit()
        return campaigns
    
    @staticmethod
    def _create_orders(session: Session, channels: List[Channel], campaigns: List[Campaign],
                      orders_per_campaign: int) -> List[MarketplaceOrder]:
        """Create orders (channel placements)."""
        orders = []
        
        for campaign in campaigns:
            # Each campaign gets placed on random channels
            selected_channels = random.sample(channels, min(orders_per_campaign, len(channels)))
            
            for channel in selected_channels:
                advertiser_cost = random.uniform(10, 500)
                editor_earnings = advertiser_cost * 0.7  # 70% goes to editor
                platform_fee = advertiser_cost * 0.3  # 30% platform fee
                
                order = MarketplaceOrder(
                    campaign_id=campaign.id,
                    channel_id=channel.id,
                    advertiser_id=campaign.advertiser_id,
                    editor_id=channel.owner_id,
                    state=random.choice([OrderState.completed, OrderState.completed, OrderState.processing, OrderState.pending]),
                    impressions_count=random.randint(1000, 100000),
                    clicks_count=random.randint(10, 5000),
                    conversions_count=random.randint(0, 500),
                    advertiser_cost=advertiser_cost,
                    editor_earnings=editor_earnings,
                    platform_fee=platform_fee,
                    payment_status=PaymentStatus.completed if random.random() > 0.1 else PaymentStatus.pending,
                    created_at=datetime.now() - timedelta(days=random.randint(0, 30)),
                    completed_at=datetime.now() - timedelta(days=random.randint(0, 30)) if random.random() > 0.4 else None,
                )
                session.add(order)
                orders.append(order)
        
        session.commit()
        return orders
    
    @staticmethod
    def _create_templates(session: Session, channels: List[Channel]) -> List[BroadcastTemplate]:
        """Create broadcast templates for channels."""
        templates = []
        
        for channel in channels:
            # Each channel gets 2-4 templates
            num_templates = random.randint(2, 4)
            
            for j in range(num_templates):
                template = BroadcastTemplate(
                    channel_id=channel.id,
                    name=f"Template {j+1} - {channel.channel_name}",
                    content=f"Promotional message for {channel.channel_name}",
                    media_urls=None,
                    is_active=True,
                    created_at=datetime.now() - timedelta(days=random.randint(0, 60)),
                )
                session.add(template)
                templates.append(template)
        
        session.commit()
        return templates
    
    @staticmethod
    def _create_disputes(session: Session, orders: List[MarketplaceOrder], dispute_rate: float = 0.05) -> List[DisputeTicket]:
        """Create disputes for realistic data (5% of orders disputed)."""
        disputes = []
        
        # Select random orders to have disputes
        orders_with_disputes = random.sample(orders, max(1, int(len(orders) * dispute_rate)))
        
        for order in orders_with_disputes:
            dispute = DisputeTicket(
                order_id=order.id,
                editor_id=order.editor_id,
                advertiser_id=order.advertiser_id,
                reason=random.choice([
                    "Content not delivered as promised",
                    "Audience mismatch",
                    "Poor engagement metrics",
                    "Ad placement issues",
                    "Refund request",
                ]),
                evidence=None,
                status=random.choice([DisputeStatus.open, DisputeStatus.open, DisputeStatus.resolved]),
                resolution=None if random.random() > 0.5 else "SPLIT_50_50",
                created_at=datetime.now() - timedelta(days=random.randint(0, 30)),
                resolved_at=None if random.random() > 0.5 else datetime.now() - timedelta(days=random.randint(0, 20)),
            )
            session.add(dispute)
            disputes.append(dispute)
        
        session.commit()
        return disputes


def seed_database_from_cli():
    """Command-line interface for seeding database."""
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Create session
        session_factory = create_session_factory()
        session = session_factory()
        
        # Parse command-line arguments
        num_editors = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        num_advertisers = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        num_campaigns = int(sys.argv[3]) if len(sys.argv) > 3 else 2
        num_orders = int(sys.argv[4]) if len(sys.argv) > 4 else 3
        
        logger.info(f"Seeding database with: {num_editors} editors, {num_advertisers} advertisers")
        
        stats = DatabaseSeeder.seed_database(
            session,
            num_editors=num_editors,
            num_advertisers=num_advertisers,
            num_campaigns_per_advertiser=num_campaigns,
            num_orders_per_campaign=num_orders
        )
        
        logger.info("\n" + "="*60)
        logger.info("DATABASE SEEDING COMPLETE")
        logger.info("="*60)
        for key, value in stats.items():
            logger.info(f"{key.upper()}: {value}")
        
        session.close()
        
    except Exception as e:
        logger.error(f"Failed to seed database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    seed_database_from_cli()
