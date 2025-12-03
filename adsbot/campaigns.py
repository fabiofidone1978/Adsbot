"""Advanced campaign management system for Inside Ads."""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from .models import Campaign, User, Channel

logger = logging.getLogger(__name__)


class TargetingType(str, Enum):
    """Targeting options."""
    LANGUAGE = "language"
    COUNTRY = "country"
    CATEGORY = "category"
    AGE_GROUP = "age_group"
    INTERESTS = "interests"


class PaymentModel(str, Enum):
    """Payment models for campaigns."""
    CPM = "cpm"  # Cost per thousand impressions
    CPC = "cpc"  # Cost per click
    CPA = "cpa"  # Cost per action (subscription)


class CampaignVariant:
    """Campaign variant/ad version."""
    
    def __init__(self, campaign_id: int, variant_id: int, title: str, 
                 description: str, image_url: Optional[str] = None,
                 performance: Dict = None):
        self.campaign_id = campaign_id
        self.variant_id = variant_id
        self.title = title
        self.description = description
        self.image_url = image_url
        self.performance = performance or {
            "impressions": 0,
            "clicks": 0,
            "subscriptions": 0,
            "ctr": 0.0,  # Click-through rate
            "cpa": 0.0,  # Cost per acquisition
        }


class CampaignMetrics:
    """Aggregate campaign metrics."""
    
    def __init__(self, campaign_id: int):
        self.campaign_id = campaign_id
        self.total_impressions = 0
        self.total_clicks = 0
        self.total_subscriptions = 0
        self.total_spent = 0.0
        self.total_revenue = 0.0
        self.estimated_reach = 0
        self.best_variant_id = None
        self.ctr = 0.0
        self.cpa = 0.0
        self.roi = 0.0
        self.status = "active"  # active, paused, ended


class TargetingSettings:
    """Campaign targeting configuration."""
    
    def __init__(self):
        self.languages: List[str] = ["Italian"]
        self.target_countries: List[str] = ["IT"]
        self.categories: List[str] = []
        self.min_subscribers = 0
        self.max_subscribers = 1_000_000
        self.excluded_channels: List[int] = []
        self.interests: List[str] = []


class BudgetSettings:
    """Campaign budget configuration."""
    
    def __init__(self, total_budget: float, payment_model: PaymentModel):
        self.total_budget = total_budget
        self.remaining_budget = total_budget
        self.payment_model = payment_model
        self.daily_budget: Optional[float] = None
        self.bid_amount = 0.0  # Cost per impression/click/action
        self.spent_today = 0.0
        self.spent_total = 0.0


class AdvancedCampaignManager:
    """Manage advanced campaign features."""
    
    def __init__(self, session: Session):
        self.session = session
        self.variants: Dict[int, List[CampaignVariant]] = {}
        self.metrics: Dict[int, CampaignMetrics] = {}
    
    def create_campaign_with_variants(
        self,
        advertiser: User,
        campaign_name: str,
        target_channels: List[Channel],
        variants: List[Dict],
        budget: float,
        payment_model: PaymentModel = PaymentModel.CPC,
        targeting: Optional[TargetingSettings] = None,
    ) -> Dict:
        """Create campaign with multiple ad variants.
        
        Args:
            advertiser: Advertiser user
            campaign_name: Campaign name
            target_channels: Target channels
            variants: List of variant dicts with title, description, image_url
            budget: Total campaign budget
            payment_model: CPM, CPC, or CPA
            targeting: Targeting settings
            
        Returns:
            Campaign creation result
        """
        try:
            # Create campaign
            campaign = Campaign(
                user_id=advertiser.id,
                name=campaign_name,
                description=f"Campaign with {len(variants)} variants",
                budget=budget,
                created_at=datetime.utcnow(),
            )
            
            self.session.add(campaign)
            self.session.flush()  # Get campaign ID
            
            campaign_id = campaign.id
            
            # Create variants
            variant_list = []
            for idx, var_data in enumerate(variants, start=1):
                variant = CampaignVariant(
                    campaign_id=campaign_id,
                    variant_id=idx,
                    title=var_data.get("title", f"Ad Variant {idx}"),
                    description=var_data.get("description", ""),
                    image_url=var_data.get("image_url"),
                )
                variant_list.append(variant)
            
            self.variants[campaign_id] = variant_list
            
            # Initialize metrics
            metrics = CampaignMetrics(campaign_id)
            metrics.total_spent = 0.0
            self.metrics[campaign_id] = metrics
            
            self.session.commit()
            
            logger.info(f"Campaign {campaign_name} created with {len(variant_list)} variants")
            
            return {
                "campaign_id": campaign_id,
                "name": campaign_name,
                "variants": len(variant_list),
                "budget": budget,
                "payment_model": payment_model.value,
                "target_channels": len(target_channels),
                "status": "created",
            }
            
        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            self.session.rollback()
            return None
    
    def update_variant_performance(
        self,
        campaign_id: int,
        variant_id: int,
        impressions: int = 0,
        clicks: int = 0,
        subscriptions: int = 0,
    ) -> Optional[Dict]:
        """Update variant performance metrics."""
        if campaign_id not in self.variants:
            return None
        
        variants = self.variants[campaign_id]
        for variant in variants:
            if variant.variant_id == variant_id:
                variant.performance["impressions"] += impressions
                variant.performance["clicks"] += clicks
                variant.performance["subscriptions"] += subscriptions
                
                # Calculate CTR
                if variant.performance["impressions"] > 0:
                    ctr = (variant.performance["clicks"] / variant.performance["impressions"]) * 100
                    variant.performance["ctr"] = round(ctr, 2)
                
                logger.info(f"Updated variant {variant_id}: +{impressions} impr, +{clicks} clicks")
                
                return {
                    "variant_id": variant_id,
                    "impressions": variant.performance["impressions"],
                    "clicks": variant.performance["clicks"],
                    "subscriptions": variant.performance["subscriptions"],
                    "ctr": variant.performance["ctr"],
                }
        
        return None
    
    def get_best_performing_variant(self, campaign_id: int) -> Optional[CampaignVariant]:
        """Get variant with highest performance."""
        if campaign_id not in self.variants:
            return None
        
        variants = self.variants[campaign_id]
        if not variants:
            return None
        
        # Sort by subscriptions, then clicks, then impressions
        best = max(
            variants,
            key=lambda v: (
                v.performance["subscriptions"],
                v.performance["clicks"],
                v.performance["impressions"],
            )
        )
        
        return best
    
    def get_campaign_summary(self, campaign_id: int) -> Optional[Dict]:
        """Get comprehensive campaign summary."""
        if campaign_id not in self.metrics:
            return None
        
        metrics = self.metrics[campaign_id]
        
        # Aggregate all variants
        total_impr = 0
        total_clicks = 0
        total_subs = 0
        
        if campaign_id in self.variants:
            for variant in self.variants[campaign_id]:
                total_impr += variant.performance["impressions"]
                total_clicks += variant.performance["clicks"]
                total_subs += variant.performance["subscriptions"]
        
        # Calculate CTR and CPA
        ctr = (total_clicks / total_impr * 100) if total_impr > 0 else 0
        cpa = (metrics.total_spent / total_subs) if total_subs > 0 else 0
        roi = ((metrics.total_revenue - metrics.total_spent) / metrics.total_spent * 100) if metrics.total_spent > 0 else 0
        
        # Estimate reach (70% of impressions are unique)
        estimated_reach = int(total_impr * 0.7)
        
        return {
            "campaign_id": campaign_id,
            "total_impressions": total_impr,
            "total_clicks": total_clicks,
            "total_subscriptions": total_subs,
            "ctr": round(ctr, 2),
            "cpa": round(cpa, 2),
            "total_spent": round(metrics.total_spent, 2),
            "total_revenue": round(metrics.total_revenue, 2),
            "roi": round(roi, 2),
            "estimated_reach": estimated_reach,
            "variants_count": len(self.variants.get(campaign_id, [])),
            "best_variant": self.get_best_performing_variant(campaign_id).variant_id if self.get_best_performing_variant(campaign_id) else None,
            "status": metrics.status,
        }
    
    def estimate_performance(
        self,
        targeting: TargetingSettings,
        available_channels: List[Channel],
    ) -> Dict:
        """Estimate campaign performance based on targeting."""
        # Filter channels by targeting
        matched_channels = [
            ch for ch in available_channels
            if ch.id not in targeting.excluded_channels
        ]
        
        # Estimate metrics
        total_subscribers = sum(getattr(ch, 'subscribers', 1000) for ch in matched_channels)
        estimated_impressions = int(total_subscribers * 0.6)  # 60% reach
        estimated_clicks = int(estimated_impressions * 0.05)  # 5% CTR
        estimated_subscriptions = int(estimated_clicks * 0.1)  # 10% conversion
        
        return {
            "matched_channels": len(matched_channels),
            "total_subscribers": total_subscribers,
            "estimated_impressions": estimated_impressions,
            "estimated_clicks": estimated_clicks,
            "estimated_subscriptions": estimated_subscriptions,
            "estimated_ctr": 5.0,
            "estimated_conversion_rate": 10.0,
        }
    
    def apply_ai_optimization(
        self,
        campaign_id: int,
        optimization_type: str = "performance",
    ) -> Dict:
        """Apply AI-based optimization to campaign.
        
        Args:
            campaign_id: Campaign to optimize
            optimization_type: "performance", "reach", or "cost"
            
        Returns:
            Optimization recommendations
        """
        summary = self.get_campaign_summary(campaign_id)
        if not summary:
            return {}
        
        recommendations = []
        
        if optimization_type == "performance":
            # Focus on best-performing variants
            best = self.get_best_performing_variant(campaign_id)
            if best:
                recommendations.append({
                    "action": "boost_variant",
                    "variant_id": best.variant_id,
                    "reason": f"Variant {best.variant_id} has highest conversion",
                    "budget_increase": "20%",
                })
        
        elif optimization_type == "reach":
            # Expand to similar channels
            if summary["ctr"] < 2.0:
                recommendations.append({
                    "action": "expand_targeting",
                    "reason": "Low CTR - expand targeting to more channels",
                    "new_targeting": "expand_countries",
                })
        
        elif optimization_type == "cost":
            # Reduce spend on low performers
            if summary["cpa"] > 5.0:
                recommendations.append({
                    "action": "reduce_bid",
                    "reason": f"High CPA (${summary['cpa']}) - reduce bid",
                    "bid_reduction": "15%",
                })
        
        return {
            "campaign_id": campaign_id,
            "optimization_type": optimization_type,
            "recommendations": recommendations,
            "applied_at": datetime.utcnow().isoformat(),
        }
    
    def pause_low_performers(self, campaign_id: int, min_ctr: float = 2.0) -> Dict:
        """Pause variants with CTR below threshold."""
        if campaign_id not in self.variants:
            return {}
        
        paused = []
        for variant in self.variants[campaign_id]:
            ctr = variant.performance["ctr"]
            if ctr < min_ctr and variant.performance["impressions"] > 100:
                paused.append({
                    "variant_id": variant.variant_id,
                    "ctr": ctr,
                    "impressions": variant.performance["impressions"],
                })
        
        logger.info(f"Paused {len(paused)} variants in campaign {campaign_id}")
        
        return {
            "campaign_id": campaign_id,
            "paused_variants": paused,
            "reason": f"CTR below {min_ctr}%",
        }
