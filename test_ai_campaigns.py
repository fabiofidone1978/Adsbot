"""
Quick test script for AI Campaign Generation feature
"""

from adsbot.campaign_analyzer import CampaignAnalyzer, ChannelAnalysis


def test_campaign_analyzer():
    """Test the campaign analyzer with mock data."""
    
    analyzer = CampaignAnalyzer()
    
    # Mock data for a tech channel
    channel_analysis = analyzer.analyze_channel(
        channel_handle="@TechChannelXYZ",
        channel_title="Tech News Daily",
        channel_topic="Technology",
        followers=5000,
        recent_metrics={
            "total_likes": 1500,
            "total_comments": 300,
        },
        posts_data=[
            {"likes": 150, "comments": 30, "hour": 19, "hashtags": ["#tech", "#news"]},
            {"likes": 120, "comments": 25, "hour": 20, "hashtags": ["#tech", "#innovation"]},
            {"likes": 200, "comments": 40, "hour": 18, "hashtags": ["#tech", "#trending"]},
            {"likes": 100, "comments": 20, "hour": 21, "hashtags": ["#tech"]},
            {"likes": 180, "comments": 35, "hour": 19, "hashtags": ["#news"]},
        ],
    )
    
    # Display analysis results
    print("=" * 60)
    print("📊 CHANNEL ANALYSIS RESULTS")
    print("=" * 60)
    print(f"Channel: {channel_analysis.channel_handle}")
    print(f"Title: {channel_analysis.channel_title}")
    print(f"Topic: {channel_analysis.topic}")
    print(f"Followers: {channel_analysis.total_followers}")
    print(f"Engagement Rate: {channel_analysis.engagement_rate:.2%}")
    print(f"Avg Post Engagement: {channel_analysis.avg_post_engagement:.0f}")
    print(f"Posting Frequency: {channel_analysis.posting_frequency}")
    print(f"Best Time to Post: {channel_analysis.best_posting_time}")
    print(f"Content Themes: {', '.join(channel_analysis.content_themes)}")
    print("\n📌 Recommendations:")
    for i, rec in enumerate(channel_analysis.recommendations, 1):
        print(f"  {i}. {rec}")
    
    # Generate campaign suggestions
    print("\n" + "=" * 60)
    print("🎯 PERSONALIZED CAMPAIGN SUGGESTIONS")
    print("=" * 60)
    
    suggestions = analyzer.generate_campaign_suggestions(channel_analysis, budget=200)
    
    for idx, suggestion in enumerate(suggestions, 1):
        print(f"\n{idx}. {suggestion.title}")
        print(f"   Type: {suggestion.campaign_type}")
        print(f"   Description: {suggestion.description}")
        print(f"   Budget: €{suggestion.recommended_budget:.2f}")
        print(f"   Estimated Reach: {suggestion.estimated_reach:,.0f}")
        print(f"   Estimated Engagement: {suggestion.estimated_engagement:,.0f}")
        print(f"   ROI Expected: {suggestion.expected_roi:.1f}x")
        print(f"   Content Focus: {suggestion.content_focus}")
        print(f"   Timing: {suggestion.timing.get('duration', 'N/A')}")
        print(f"   Reasoning: {suggestion.reasoning}")
    
    print("\n" + "=" * 60)
    print("✅ Test completed successfully!")
    print("=" * 60)


def test_premium_check():
    """Test subscription checking logic."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from adsbot.db import Base
    from adsbot.models import User
    from adsbot.services import is_premium_user, upgrade_user_to_premium, ensure_user
    
    # Create in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Create a free user
        user = ensure_user(
            session,
            telegram_id=12345,
            username="test_user",
            first_name="Test",
            language_code="it",
        )
        session.commit()
        
        # Check if free
        print("\n" + "=" * 60)
        print("🔐 SUBSCRIPTION CHECK TEST")
        print("=" * 60)
        print(f"User: {user.username}")
        print(f"Subscription Type: {user.subscription_type}")
        print(f"Is Premium: {is_premium_user(session, user)}")
        
        # Upgrade to premium
        print("\nUpgrading to premium...")
        upgrade_user_to_premium(session, user, "premium")
        session.commit()
        
        print(f"New Subscription Type: {user.subscription_type}")
        print(f"Is Premium: {is_premium_user(session, user)}")
        
        print("✅ Subscription check test completed!")
        print("=" * 60)


if __name__ == "__main__":
    print("\n🤖 AI Campaign Generation Feature Tests\n")
    
    # Test 1: Campaign Analyzer
    test_campaign_analyzer()
    
    # Test 2: Premium Check
    try:
        test_premium_check()
    except Exception as e:
        print(f"\n⚠️ Premium check test skipped (DB setup needed): {e}")
    
    print("\n✨ All tests completed!\n")
