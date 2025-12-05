"""Campaign analytics and forecasting system - FASE 4: Analytics & Reporting."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from adsbot.models import (
    User, Channel, Campaign, MarketplaceOrder, DisputeTicket,
    BroadcastTemplate, UserRole, OrderState, DisputeStatus
)

logger = logging.getLogger(__name__)


class PerformanceForecast:
    """Forecast campaign performance."""
    
    @staticmethod
    def estimate_weekly_metrics(
        daily_impressions: int,
        daily_ctr: float,
        daily_conversion: float,
        budget_per_day: float,
    ) -> Dict:
        """Estimate weekly performance.
        
        Args:
            daily_impressions: Estimated daily impressions
            daily_ctr: Click-through rate (%)
            daily_conversion: Conversion rate (%)
            budget_per_day: Daily budget in USD
            
        Returns:
            Weekly forecast
        """
        days = 7
        
        weekly_impressions = daily_impressions * days
        weekly_clicks = int(weekly_impressions * (daily_ctr / 100))
        weekly_conversions = int(weekly_clicks * (daily_conversion / 100))
        weekly_budget = budget_per_day * days
        
        cost_per_click = (weekly_budget / weekly_clicks) if weekly_clicks > 0 else 0
        cost_per_conversion = (weekly_budget / weekly_conversions) if weekly_conversions > 0 else 0
        
        return {
            "period": "weekly",
            "impressions": weekly_impressions,
            "clicks": weekly_clicks,
            "conversions": weekly_conversions,
            "budget": round(weekly_budget, 2),
            "cpc": round(cost_per_click, 2),
            "cpa": round(cost_per_conversion, 2),
            "estimated_reach": int(weekly_impressions * 0.7),
        }
    
    @staticmethod
    def estimate_monthly_metrics(
        daily_impressions: int,
        daily_ctr: float,
        daily_conversion: float,
        budget_per_day: float,
    ) -> Dict:
        """Estimate monthly performance."""
        days = 30
        
        weekly_forecast = PerformanceForecast.estimate_weekly_metrics(
            daily_impressions, daily_ctr, daily_conversion, budget_per_day
        )
        
        return {
            "period": "monthly",
            "impressions": weekly_forecast["impressions"] * 4,
            "clicks": weekly_forecast["clicks"] * 4,
            "conversions": weekly_forecast["conversions"] * 4,
            "budget": round(weekly_forecast["budget"] * 4, 2),
            "cpc": weekly_forecast["cpc"],
            "cpa": weekly_forecast["cpa"],
            "estimated_reach": weekly_forecast["estimated_reach"] * 4,
        }
    
    @staticmethod
    def break_even_analysis(
        total_budget: float,
        average_cpc: float,
        conversion_rate: float,
        customer_lifetime_value: float,
    ) -> Dict:
        """Calculate break-even point.
        
        Args:
            total_budget: Campaign budget
            average_cpc: Average cost per click
            conversion_rate: Conversion rate (%)
            customer_lifetime_value: CLV in USD
            
        Returns:
            Break-even analysis
        """
        # Break-even at revenue = budget
        revenue_per_conversion = customer_lifetime_value
        conversions_needed = total_budget / revenue_per_conversion
        clicks_needed = int(conversions_needed / (conversion_rate / 100))
        budget_to_break_even = clicks_needed * average_cpc
        
        return {
            "total_budget": total_budget,
            "conversions_needed": int(conversions_needed),
            "clicks_needed": clicks_needed,
            "budget_to_break_even": round(budget_to_break_even, 2),
            "roi_at_break_even": 0.0,
            "profit_potential": round(total_budget - budget_to_break_even, 2),
        }


class CampaignAnalytics:
    """Analyze campaign performance."""
    
    @staticmethod
    def calculate_roi(
        revenue: float,
        cost: float,
    ) -> float:
        """Calculate ROI percentage."""
        if cost == 0:
            return 0.0
        return ((revenue - cost) / cost) * 100
    
    @staticmethod
    def compare_variants(variants_data: List[Dict]) -> Dict:
        """Compare multiple variant performances.
        
        Args:
            variants_data: List of variant dicts with metrics
            
        Returns:
            Comparison analysis
        """
        if not variants_data:
            return {}
        
        best_ctr = max((v.get("ctr", 0) for v in variants_data), default=0)
        best_cpa = min((v.get("cpa", float('inf')) for v in variants_data if v.get("cpa") > 0), default=0)
        
        return {
            "total_variants": len(variants_data),
            "best_ctr": round(best_ctr, 2),
            "best_cpa": round(best_cpa, 2),
            "worst_ctr": round(min((v.get("ctr", float('inf')) for v in variants_data), default=0), 2),
            "worst_cpa": round(max((v.get("cpa", 0) for v in variants_data), default=0), 2),
            "average_ctr": round(sum(v.get("ctr", 0) for v in variants_data) / len(variants_data), 2),
            "variants_above_average_ctr": len([v for v in variants_data if v.get("ctr", 0) > best_ctr * 0.8]),
        }
    
    @staticmethod
    def performance_timeline(
        daily_metrics: List[Dict],
    ) -> Dict:
        """Analyze performance over time.
        
        Args:
            daily_metrics: List of daily metric dicts
            
        Returns:
            Timeline analysis
        """
        if not daily_metrics:
            return {}
        
        total_impressions = sum(m.get("impressions", 0) for m in daily_metrics)
        total_clicks = sum(m.get("clicks", 0) for m in daily_metrics)
        total_conversions = sum(m.get("conversions", 0) for m in daily_metrics)
        
        trend = "stable"
        if len(daily_metrics) > 1:
            latest_ctr = (daily_metrics[-1].get("clicks", 0) / daily_metrics[-1].get("impressions", 1)) * 100 if daily_metrics[-1].get("impressions") > 0 else 0
            previous_ctr = (daily_metrics[-2].get("clicks", 0) / daily_metrics[-2].get("impressions", 1)) * 100 if daily_metrics[-2].get("impressions") > 0 else 0
            
            if latest_ctr > previous_ctr * 1.1:
                trend = "improving"
            elif latest_ctr < previous_ctr * 0.9:
                trend = "declining"
        
        return {
            "days_tracked": len(daily_metrics),
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "average_daily_impressions": int(total_impressions / len(daily_metrics)) if daily_metrics else 0,
            "trend": trend,
        }
    
    @staticmethod
    def estimate_channel_compatibility(
        channel_stats: Dict,
        campaign_targeting: Dict,
    ) -> float:
        """Estimate how well campaign fits a channel (0-100).
        
        Args:
            channel_stats: Channel statistics
            campaign_targeting: Campaign targeting settings
            
        Returns:
            Compatibility score (0-100)
        """
        score = 0
        
        # Language match (weight: 30)
        channel_language = channel_stats.get("language", "Italian")
        target_languages = campaign_targeting.get("target_languages", ["Italian"])
        if channel_language in target_languages:
            score += 30
        
        # Subscriber range match (weight: 40)
        channel_subscribers = channel_stats.get("subscribers", 5000)
        min_subs = campaign_targeting.get("min_subscribers", 0)
        max_subs = campaign_targeting.get("max_subscribers", 1_000_000)
        
        if min_subs <= channel_subscribers <= max_subs:
            score += 40
        else:
            # Partial score if outside range
            if channel_subscribers > max_subs:
                score += 20  # Larger is better
            else:
                score += 10  # Smaller channels less ideal
        
        # Category match (weight: 30)
        channel_category = channel_stats.get("category", "general")
        target_categories = campaign_targeting.get("target_categories", [])
        
        if not target_categories or channel_category in target_categories:
            score += 30
        elif channel_category == "general":
            score += 15  # General category matches most
        
        return min(score, 100)


class BudgetOptimizer:
    """Optimize budget allocation across variants."""
    
    @staticmethod
    def allocate_budget_by_performance(
        total_budget: float,
        variants_performance: List[Dict],
    ) -> Dict[int, float]:
        """Allocate budget proportional to performance.
        
        Args:
            total_budget: Total budget to allocate
            variants_performance: List of variant performance dicts with variant_id
            
        Returns:
            Budget allocation by variant_id
        """
        if not variants_performance:
            return {}
        
        # Weight by CTR
        total_weight = sum(v.get("ctr", 0) for v in variants_performance)
        
        if total_weight == 0:
            # Equal allocation
            equal_share = total_budget / len(variants_performance)
            return {v.get("variant_id"): equal_share for v in variants_performance}
        
        allocation = {}
        for variant in variants_performance:
            variant_id = variant.get("variant_id")
            weight = variant.get("ctr", 0) / total_weight
            allocation[variant_id] = total_budget * weight
        
        return allocation
    
    @staticmethod
    def calculate_daily_spending_pace(
        total_budget: float,
        campaign_duration_days: int,
    ) -> Dict:
        """Calculate daily budget to spend evenly.
        
        Args:
            total_budget: Total campaign budget
            campaign_duration_days: Campaign duration in days
            
        Returns:
            Daily spending details
        """
        daily_budget = total_budget / campaign_duration_days
        
        return {
            "total_budget": total_budget,
            "duration_days": campaign_duration_days,
            "daily_budget": round(daily_budget, 2),
            "weekly_budget": round(daily_budget * 7, 2),
            "warning_threshold": round(daily_budget * 1.5, 2),
        }


class SmartRecommendations:
    """Generate AI recommendations for campaigns."""
    
    @staticmethod
    def get_optimization_suggestions(
        campaign_summary: Dict,
        variant_comparison: Dict,
    ) -> List[Dict]:
        """Generate optimization suggestions based on performance.
        
        Args:
            campaign_summary: Campaign summary stats
            variant_comparison: Variant comparison stats
            
        Returns:
            List of recommendations
        """
        suggestions = []
        
        # Low CTR
        if campaign_summary.get("ctr", 0) < 2.0:
            suggestions.append({
                "priority": "high",
                "type": "ctr",
                "message": "CTR is below 2% - consider improving ad creatives",
                "action": "Review best-performing variant and replicate design",
            })
        
        # High CPA
        if campaign_summary.get("cpa", 0) > 5.0:
            suggestions.append({
                "priority": "high",
                "type": "cpa",
                "message": f"CPA is high (${campaign_summary['cpa']}) - reduce bid or improve targeting",
                "action": "Reduce bid by 10-20% or expand to cheaper channels",
            })
        
        # Poor ROI
        if campaign_summary.get("roi", -100) < -50:
            suggestions.append({
                "priority": "critical",
                "type": "roi",
                "message": "Negative ROI - campaign is losing money",
                "action": "Pause campaign and review strategy",
            })
        
        # Variant performance variance
        best_vs_worst_ratio = (variant_comparison.get("best_ctr", 1) / 
                               (variant_comparison.get("worst_ctr", 1) or 1))
        
        if best_vs_worst_ratio > 3.0:
            suggestions.append({
                "priority": "medium",
                "type": "variants",
                "message": f"Huge variance between variants ({best_vs_worst_ratio:.1f}x)",
                "action": "Pause low-performing variants and focus budget on best",
            })
        
        # Budget efficiency
        if campaign_summary.get("spent", 0) < campaign_summary.get("budget", 1) * 0.3:
            suggestions.append({
                "priority": "low",
                "type": "budget",
                "message": "Campaign is spending slowly - consider raising bid",
                "action": "Increase daily budget or bid to spend allocated budget faster",
            })
        
        return suggestions


# ============================================================================
# FASE 4: Analytics & Reporting Functions
# ============================================================================

class EditorAnalytics:
    """Task 16: Editor analytics dashboard and reports."""
    
    @staticmethod
    def editor_analytics_dashboard(session: Session, editor_id: int) -> Dict:
        """Generate comprehensive editor analytics dashboard.
        
        Args:
            session: Database session
            editor_id: Editor user ID
            
        Returns:
            Complete editor analytics dashboard
        """
        try:
            editor = session.query(User).filter(User.id == editor_id).first()
            if not editor:
                logger.error(f"Editor {editor_id} not found")
                return {"error": "Editor not found"}
            
            # Get channels for this editor
            channels = session.query(Channel).filter(Channel.owner_id == editor_id).all()
            channel_ids = [c.id for c in channels]
            
            if not channel_ids:
                return {
                    "editor_id": editor_id,
                    "editor_name": editor.first_name or "Unknown",
                    "channels_count": 0,
                    "total_subscribers": 0,
                    "total_campaigns": 0,
                    "total_earnings": 0.0,
                    "active_campaigns": 0,
                    "completed_campaigns": 0,
                    "message": "No channels found"
                }
            
            # Calculate metrics
            total_subscribers = sum(c.subscribers_count for c in channels)
            
            # Campaigns stats
            campaigns = session.query(Campaign).filter(
                Campaign.channel_id.in_(channel_ids)
            ).all()
            
            total_campaigns = len(campaigns)
            active_campaigns = len([c for c in campaigns if c.is_active])
            completed_campaigns = len([c for c in campaigns if not c.is_active])
            
            # Earnings from successful orders
            earnings = session.query(func.sum(MarketplaceOrder.editor_earnings)).filter(
                MarketplaceOrder.channel_id.in_(channel_ids),
                MarketplaceOrder.state == OrderState.completed
            ).scalar() or 0.0
            
            # Average rating
            avg_rating = editor.rating or 0.0
            rating_count = editor.rating_count or 0
            
            return {
                "editor_id": editor_id,
                "editor_name": editor.first_name or "Unknown",
                "email": editor.email,
                "channels_count": len(channels),
                "total_subscribers": total_subscribers,
                "avg_subscribers_per_channel": int(total_subscribers / len(channels)) if channels else 0,
                "total_campaigns": total_campaigns,
                "active_campaigns": active_campaigns,
                "completed_campaigns": completed_campaigns,
                "total_earnings": float(earnings),
                "avg_rating": round(avg_rating, 2),
                "rating_count": rating_count,
                "is_verified": editor.admin_verified_at is not None,
                "is_suspended": editor.is_suspended,
                "created_at": editor.created_at.isoformat() if editor.created_at else None,
            }
        except Exception as e:
            logger.error(f"Error generating editor analytics: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def editor_earnings_report(session: Session, editor_id: int, days: int = 30) -> Dict:
        """Generate editor earnings report for time period.
        
        Args:
            session: Database session
            editor_id: Editor user ID
            days: Number of days to report (default 30)
            
        Returns:
            Earnings breakdown by period
        """
        try:
            channels = session.query(Channel).filter(Channel.owner_id == editor_id).all()
            channel_ids = [c.id for c in channels]
            
            if not channel_ids:
                return {"error": "No channels found", "total_earnings": 0.0}
            
            start_date = datetime.now() - timedelta(days=days)
            
            # Total earnings in period
            period_earnings = session.query(func.sum(MarketplaceOrder.editor_earnings)).filter(
                MarketplaceOrder.channel_id.in_(channel_ids),
                MarketplaceOrder.state == OrderState.completed,
                MarketplaceOrder.completed_at >= start_date
            ).scalar() or 0.0
            
            # Earnings by channel
            channel_earnings = {}
            for channel in channels:
                earnings = session.query(func.sum(MarketplaceOrder.editor_earnings)).filter(
                    MarketplaceOrder.channel_id == channel.id,
                    MarketplaceOrder.state == OrderState.completed,
                    MarketplaceOrder.completed_at >= start_date
                ).scalar() or 0.0
                channel_earnings[channel.channel_name] = float(earnings)
            
            # Daily breakdown
            daily_earnings = {}
            for i in range(days):
                day = (start_date + timedelta(days=i)).date()
                day_earnings = session.query(func.sum(MarketplaceOrder.editor_earnings)).filter(
                    MarketplaceOrder.channel_id.in_(channel_ids),
                    MarketplaceOrder.state == OrderState.completed,
                    func.date(MarketplaceOrder.completed_at) == day
                ).scalar() or 0.0
                daily_earnings[str(day)] = float(day_earnings)
            
            return {
                "editor_id": editor_id,
                "period_days": days,
                "total_earnings": float(period_earnings),
                "avg_daily_earnings": round(period_earnings / days, 2),
                "earnings_by_channel": channel_earnings,
                "daily_breakdown": daily_earnings,
            }
        except Exception as e:
            logger.error(f"Error generating earnings report: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def editor_channel_performance(session: Session, editor_id: int) -> Dict:
        """Analyze performance of all editor channels.
        
        Args:
            session: Database session
            editor_id: Editor user ID
            
        Returns:
            Per-channel performance metrics
        """
        try:
            channels = session.query(Channel).filter(Channel.owner_id == editor_id).all()
            
            channel_performance = []
            for channel in channels:
                # Get campaigns for this channel
                campaigns = session.query(Campaign).filter(
                    Campaign.channel_id == channel.id
                ).all()
                
                # Get completed orders
                orders = session.query(MarketplaceOrder).filter(
                    MarketplaceOrder.channel_id == channel.id,
                    MarketplaceOrder.state == OrderState.completed
                ).all()
                
                total_earnings = sum(o.editor_earnings or 0 for o in orders)
                
                # Campaign stats
                active_campaigns = len([c for c in campaigns if c.is_active])
                
                channel_performance.append({
                    "channel_id": channel.id,
                    "channel_name": channel.channel_name,
                    "subscribers": channel.subscribers_count,
                    "category": channel.category or "general",
                    "language": channel.language or "Italian",
                    "campaigns_total": len(campaigns),
                    "campaigns_active": active_campaigns,
                    "orders_completed": len(orders),
                    "total_earnings": float(total_earnings),
                    "avg_earnings_per_order": round(total_earnings / len(orders), 2) if orders else 0,
                    "created_at": channel.created_at.isoformat() if channel.created_at else None,
                })
            
            return {
                "editor_id": editor_id,
                "channels_count": len(channels),
                "channels": channel_performance,
                "total_subscribers": sum(c["subscribers"] for c in channel_performance),
                "total_earnings": sum(c["total_earnings"] for c in channel_performance),
            }
        except Exception as e:
            logger.error(f"Error analyzing channel performance: {e}")
            return {"error": str(e)}


class AdvertiserAnalytics:
    """Task 17: Advertiser analytics and campaign reports."""
    
    @staticmethod
    def advertiser_analytics_dashboard(session: Session, advertiser_id: int) -> Dict:
        """Generate comprehensive advertiser analytics dashboard.
        
        Args:
            session: Database session
            advertiser_id: Advertiser user ID
            
        Returns:
            Complete advertiser analytics dashboard
        """
        try:
            advertiser = session.query(User).filter(
                User.id == advertiser_id,
                User.role == UserRole.ADVERTISER
            ).first()
            
            if not advertiser:
                logger.error(f"Advertiser {advertiser_id} not found")
                return {"error": "Advertiser not found"}
            
            # Get campaigns created by advertiser
            campaigns = session.query(Campaign).filter(
                Campaign.advertiser_id == advertiser_id
            ).all()
            
            if not campaigns:
                return {
                    "advertiser_id": advertiser_id,
                    "advertiser_name": advertiser.first_name or "Unknown",
                    "campaigns_count": 0,
                    "total_budget": 0.0,
                    "total_spent": 0.0,
                    "total_impressions": 0,
                    "message": "No campaigns found"
                }
            
            campaign_ids = [c.id for c in campaigns]
            
            # Calculate metrics
            total_budget = sum(c.budget or 0 for c in campaigns)
            active_campaigns = len([c for c in campaigns if c.is_active])
            
            # Orders/impressions stats
            orders = session.query(MarketplaceOrder).filter(
                MarketplaceOrder.campaign_id.in_(campaign_ids)
            ).all()
            
            total_spent = sum(o.advertiser_cost or 0 for o in orders)
            total_impressions = sum(o.impressions_count or 0 for o in orders)
            total_clicks = sum(o.clicks_count or 0 for o in orders)
            
            # Completed campaigns only
            completed_orders = [o for o in orders if o.state == OrderState.completed]
            completed_spent = sum(o.advertiser_cost or 0 for o in completed_orders)
            
            return {
                "advertiser_id": advertiser_id,
                "advertiser_name": advertiser.first_name or "Unknown",
                "email": advertiser.email,
                "campaigns_total": len(campaigns),
                "campaigns_active": active_campaigns,
                "campaigns_completed": len([c for c in campaigns if not c.is_active]),
                "total_budget": float(total_budget),
                "total_spent": float(total_spent),
                "total_impressions": total_impressions,
                "total_clicks": total_clicks,
                "ctr": round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2),
                "budget_utilization": round((total_spent / total_budget * 100) if total_budget > 0 else 0, 2),
                "is_verified": advertiser.admin_verified_at is not None,
                "is_suspended": advertiser.is_suspended,
                "created_at": advertiser.created_at.isoformat() if advertiser.created_at else None,
            }
        except Exception as e:
            logger.error(f"Error generating advertiser analytics: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def advertiser_campaign_report(session: Session, advertiser_id: int) -> Dict:
        """Generate detailed report of all advertiser campaigns.
        
        Args:
            session: Database session
            advertiser_id: Advertiser user ID
            
        Returns:
            Campaign-by-campaign breakdown
        """
        try:
            campaigns = session.query(Campaign).filter(
                Campaign.advertiser_id == advertiser_id
            ).all()
            
            campaign_reports = []
            for campaign in campaigns:
                # Get orders for this campaign
                orders = session.query(MarketplaceOrder).filter(
                    MarketplaceOrder.campaign_id == campaign.id
                ).all()
                
                total_cost = sum(o.advertiser_cost or 0 for o in orders)
                total_impressions = sum(o.impressions_count or 0 for o in orders)
                total_clicks = sum(o.clicks_count or 0 for o in orders)
                
                campaign_reports.append({
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.campaign_name,
                    "budget": float(campaign.budget or 0),
                    "spent": float(total_cost),
                    "impressions": total_impressions,
                    "clicks": total_clicks,
                    "ctr": round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2),
                    "cpc": round(total_cost / total_clicks if total_clicks > 0 else 0, 2),
                    "orders_count": len(orders),
                    "is_active": campaign.is_active,
                    "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
                })
            
            return {
                "advertiser_id": advertiser_id,
                "campaigns_count": len(campaigns),
                "total_budget": sum(c["budget"] for c in campaign_reports),
                "total_spent": sum(c["spent"] for c in campaign_reports),
                "campaigns": campaign_reports,
            }
        except Exception as e:
            logger.error(f"Error generating campaign report: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def advertiser_spending_analytics(session: Session, advertiser_id: int, days: int = 30) -> Dict:
        """Analyze advertiser spending patterns over time.
        
        Args:
            session: Database session
            advertiser_id: Advertiser user ID
            days: Number of days to analyze (default 30)
            
        Returns:
            Spending breakdown and trends
        """
        try:
            campaigns = session.query(Campaign).filter(
                Campaign.advertiser_id == advertiser_id
            ).all()
            campaign_ids = [c.id for c in campaigns]
            
            if not campaign_ids:
                return {"error": "No campaigns found", "total_spent": 0.0}
            
            start_date = datetime.now() - timedelta(days=days)
            
            # Total spent in period
            total_spent = session.query(func.sum(Order.advertiser_cost)).filter(
                Order.campaign_id.in_(campaign_ids),
                Order.created_at >= start_date
            ).scalar() or 0.0
            
            # Daily breakdown
            daily_spending = {}
            for i in range(days):
                day = (start_date + timedelta(days=i)).date()
                day_spent = session.query(func.sum(Order.advertiser_cost)).filter(
                    Order.campaign_id.in_(campaign_ids),
                    func.date(Order.created_at) == day
                ).scalar() or 0.0
                daily_spending[str(day)] = float(day_spent)
            
            # Campaign spending breakdown
            campaign_spending = {}
            for campaign in campaigns:
                spent = session.query(func.sum(Order.advertiser_cost)).filter(
                    Order.campaign_id == campaign.id,
                    Order.created_at >= start_date
                ).scalar() or 0.0
                campaign_spending[campaign.campaign_name] = float(spent)
            
            return {
                "advertiser_id": advertiser_id,
                "period_days": days,
                "total_spent": float(total_spent),
                "avg_daily_spending": round(total_spent / days, 2),
                "daily_breakdown": daily_spending,
                "campaign_breakdown": campaign_spending,
            }
        except Exception as e:
            logger.error(f"Error analyzing spending: {e}")
            return {"error": str(e)}


class PlatformAnalytics:
    """Task 18: Platform-wide statistics and KPIs."""
    
    @staticmethod
    def platform_dashboard_stats(session: Session) -> Dict:
        """Generate platform-wide dashboard statistics.
        
        Returns:
            Platform KPIs and metrics
        """
        try:
            # User counts by role
            total_users = session.query(func.count(User.id)).scalar()
            editors = session.query(func.count(User.id)).filter(
                User.role == UserRole.EDITOR
            ).scalar()
            advertisers = session.query(func.count(User.id)).filter(
                User.role == UserRole.ADVERTISER
            ).scalar()
            admins = session.query(func.count(User.id)).filter(
                User.role == UserRole.ADMIN
            ).scalar()
            
            # Channel metrics
            total_channels = session.query(func.count(Channel.id)).scalar()
            total_subscribers = session.query(func.sum(Channel.subscribers_count)).scalar() or 0
            
            # Campaign metrics
            total_campaigns = session.query(func.count(Campaign.id)).scalar()
            active_campaigns = session.query(func.count(Campaign.id)).filter(
                Campaign.is_active == True
            ).scalar()
            
            # Order metrics
            total_orders = session.query(func.count(MarketplaceOrder.id)).scalar()
            completed_orders = session.query(func.count(MarketplaceOrder.id)).filter(
                MarketplaceOrder.state == OrderState.completed
            ).scalar()
            pending_orders = session.query(func.count(MarketplaceOrder.id)).filter(
                MarketplaceOrder.state == OrderState.pending
            ).scalar()
            
            # Revenue metrics
            total_platform_revenue = session.query(func.sum(MarketplaceOrder.platform_fee)).filter(
                MarketplaceOrder.state == OrderState.completed
            ).scalar() or 0.0
            
            total_editor_earnings = session.query(func.sum(MarketplaceOrder.editor_earnings)).filter(
                MarketplaceOrder.state == OrderState.completed
            ).scalar() or 0.0
            
            return {
                "timestamp": datetime.now().isoformat(),
                "users": {
                    "total": total_users,
                    "editors": editors,
                    "advertisers": advertisers,
                    "admins": admins,
                },
                "channels": {
                    "total": total_channels,
                    "total_subscribers": int(total_subscribers),
                    "avg_subscribers": int(total_subscribers / total_channels) if total_channels > 0 else 0,
                },
                "campaigns": {
                    "total": total_campaigns,
                    "active": active_campaigns,
                    "completed": total_campaigns - active_campaigns,
                },
                "orders": {
                    "total": total_orders,
                    "completed": completed_orders,
                    "pending": pending_orders,
                    "completion_rate": round((completed_orders / total_orders * 100) if total_orders > 0 else 0, 2),
                },
                "revenue": {
                    "platform_fees": float(total_platform_revenue),
                    "editor_earnings": float(total_editor_earnings),
                    "total_transactions": float(total_platform_revenue + total_editor_earnings),
                },
            }
        except Exception as e:
            logger.error(f"Error generating platform stats: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def platform_user_report(session: Session) -> Dict:
        """Generate detailed user demographics and statistics.
        
        Returns:
            User metrics by role and status
        """
        try:
            # User breakdown by role
            editor_data = session.query(User).filter(User.role == UserRole.EDITOR).all()
            advertiser_data = session.query(User).filter(User.role == UserRole.ADVERTISER).all()
            
            verified_users = session.query(func.count(User.id)).filter(
                User.admin_verified_at != None
            ).scalar()
            suspended_users = session.query(func.count(User.id)).filter(
                User.is_suspended == True
            ).scalar()
            
            # Average rating
            avg_editor_rating = session.query(func.avg(User.rating)).filter(
                User.role == UserRole.EDITOR,
                User.rating != None
            ).scalar() or 0.0
            
            # Growth metrics (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            new_users_30d = session.query(func.count(User.id)).filter(
                User.created_at >= thirty_days_ago
            ).scalar()
            
            return {
                "total_users": session.query(func.count(User.id)).scalar(),
                "verified_users": verified_users,
                "suspended_users": suspended_users,
                "editors": {
                    "count": len(editor_data),
                    "verified": len([e for e in editor_data if e.admin_verified_at]),
                    "avg_rating": round(avg_editor_rating, 2),
                    "avg_channels": len(session.query(Channel).all()) / max(len(editor_data), 1),
                },
                "advertisers": {
                    "count": len(advertiser_data),
                    "verified": len([a for a in advertiser_data if a.admin_verified_at]),
                    "avg_campaigns": len(session.query(Campaign).all()) / max(len(advertiser_data), 1),
                },
                "growth": {
                    "new_users_30d": new_users_30d,
                    "avg_daily_new_users": round(new_users_30d / 30, 2),
                },
            }
        except Exception as e:
            logger.error(f"Error generating user report: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def platform_category_report(session: Session) -> Dict:
        """Generate report of platform activity by channel category.
        
        Returns:
            Category-wise breakdown of channels and campaigns
        """
        try:
            # Group channels by category
            categories = session.query(Channel.category).distinct().all()
            category_data = {}
            
            for (category,) in categories:
                cat_name = category or "Uncategorized"
                
                channels = session.query(Channel).filter(Channel.category == category).all()
                campaigns = session.query(Campaign).filter(
                    Campaign.channel_id.in_([c.id for c in channels])
                ).all()
                
                total_subscribers = sum(c.subscribers_count for c in channels)
                total_spent = sum(sum(o.advertiser_cost or 0 for o in 
                              session.query(Order).filter(Order.campaign_id == c.id).all())
                              for c in campaigns)
                
                category_data[cat_name] = {
                    "channels": len(channels),
                    "campaigns": len(campaigns),
                    "subscribers": total_subscribers,
                    "total_spent": float(total_spent),
                }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "categories": category_data,
                "total_categories": len(category_data),
            }
        except Exception as e:
            logger.error(f"Error generating category report: {e}")
            return {"error": str(e)}


class ReportExporter:
    """Task 19: Export and report generation."""
    
    @staticmethod
    def export_csv_header(report_type: str) -> str:
        """Generate CSV header for report type.
        
        Args:
            report_type: Type of report (editor_earnings, campaign_performance, etc)
            
        Returns:
            CSV header line
        """
        headers = {
            "editor_earnings": "Date,Channel,Earnings,Orders,Impressions",
            "campaign_performance": "Campaign,Budget,Spent,Impressions,Clicks,CTR,CPC",
            "advertiser_spending": "Date,Campaign,Spent,Orders,Avg_Cost_Per_Order",
            "platform_stats": "Date,Total_Users,Editors,Advertisers,Channels,Campaigns,Orders,Revenue",
        }
        return headers.get(report_type, "")
    
    @staticmethod
    def generate_text_report(analytics_data: Dict, title: str) -> str:
        """Generate formatted text report from analytics data.
        
        Args:
            analytics_data: Analytics dictionary
            title: Report title
            
        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 60)
        lines.append(title)
        lines.append("=" * 60)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        def format_dict(d, indent=0):
            for key, value in d.items():
                if key in ["error", "message"]:
                    continue
                if isinstance(value, dict):
                    lines.append(" " * indent + f"{key}:")
                    format_dict(value, indent + 2)
                elif isinstance(value, list):
                    lines.append(" " * indent + f"{key}: {len(value)} items")
                else:
                    lines.append(" " * indent + f"{key}: {value}")
        
        format_dict(analytics_data)
        lines.append("=" * 60)
        return "\n".join(lines)
    
    @staticmethod
    def prepare_email_summary(analytics_data: Dict) -> Dict:
        """Prepare analytics data for email distribution.
        
        Args:
            analytics_data: Analytics dictionary
            
        Returns:
            Email-friendly summary
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "data": analytics_data,
            "format_html": ReportExporter.generate_text_report(analytics_data, "Analytics Report")
        }


# ============================================================================
# Existing Performance Forecast, Campaign Analytics, Budget Optimizer classes
# ============================================================================

