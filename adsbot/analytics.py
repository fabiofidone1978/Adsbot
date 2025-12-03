"""Campaign analytics and forecasting system."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

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
