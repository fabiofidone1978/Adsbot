"""
Campaign Analyzer Module - Analizza i dati del bot/canale e genera campagne personalizzate
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ChannelAnalysis:
    """Risultati dell'analisi di un canale"""
    channel_handle: str
    channel_title: Optional[str]
    topic: Optional[str]
    total_followers: int = 0
    engagement_rate: float = 0.0
    avg_post_engagement: float = 0.0
    posting_frequency: str = "unknown"
    best_posting_time: str = "unknown"
    audience_demographics: Dict = None
    content_themes: List[str] = None
    competitor_analysis: Dict = None
    growth_trends: Dict = None
    recommendations: List[str] = None


@dataclass
class CampaignSuggestion:
    """Suggerimento per una campagna personalizzata"""
    campaign_type: str
    title: str
    description: str
    recommended_budget: float
    estimated_reach: int
    estimated_engagement: float
    content_focus: str
    targeting: Dict
    timing: Dict
    expected_roi: float
    reasoning: str


class CampaignAnalyzer:
    """
    Analizza i dati del bot/canale e genera campagne personalizzate.
    """
    
    def __init__(self):
        """Initialize campaign analyzer"""
        self.campaign_types = [
            "growth",
            "engagement",
            "conversion",
            "awareness",
            "retention",
        ]
    
    def analyze_channel(
        self,
        channel_handle: str,
        channel_title: Optional[str] = None,
        channel_topic: Optional[str] = None,
        followers: int = 0,
        recent_metrics: Dict = None,
        posts_data: List[Dict] = None,
    ) -> ChannelAnalysis:
        """
        Analizza un canale e genera insights.
        
        Args:
            channel_handle: Handle del canale (es. @mychannel)
            channel_title: Titolo del canale
            channel_topic: Argomento principale
            followers: Numero di follower
            recent_metrics: Metriche recenti (engagement, etc)
            posts_data: Dati dei post recenti
            
        Returns:
            ChannelAnalysis con insights e raccomandazioni
        """
        logger.info(f"Analyzing channel: {channel_handle}")
        
        # Default values
        if recent_metrics is None:
            recent_metrics = {}
        if posts_data is None:
            posts_data = []
        
        # Calculate metrics
        engagement_rate = self._calculate_engagement_rate(recent_metrics, followers)
        avg_engagement = self._calculate_avg_engagement(posts_data)
        posting_freq = self._analyze_posting_frequency(posts_data)
        best_time = self._find_best_posting_time(posts_data)
        themes = self._extract_content_themes(posts_data)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            followers=followers,
            engagement_rate=engagement_rate,
            themes=themes,
        )
        
        analysis = ChannelAnalysis(
            channel_handle=channel_handle,
            channel_title=channel_title,
            topic=channel_topic,
            total_followers=followers,
            engagement_rate=engagement_rate,
            avg_post_engagement=avg_engagement,
            posting_frequency=posting_freq,
            best_posting_time=best_time,
            audience_demographics=self._estimate_demographics(followers),
            content_themes=themes,
            competitor_analysis=self._analyze_competitors(channel_topic),
            growth_trends=self._analyze_growth_trends(posts_data),
            recommendations=recommendations,
        )
        
        return analysis
    
    def generate_campaign_suggestions(
        self,
        channel_analysis: ChannelAnalysis,
        goals: Optional[Dict] = None,
        budget: Optional[float] = None,
    ) -> List[CampaignSuggestion]:
        """
        Genera suggerimenti di campagne personalizzate basati sull'analisi.
        
        Args:
            channel_analysis: Risultati dell'analisi del canale
            goals: Obiettivi della campagna (es. {"type": "growth", "target": 1000})
            budget: Budget disponibile
            
        Returns:
            Lista di campagne suggerite
        """
        logger.info(f"Generating campaign suggestions for: {channel_analysis.channel_handle}")
        
        suggestions = []
        
        # Sulla base dell'engagement rate, suggerisci diverse strategie
        if channel_analysis.engagement_rate > 0.05:
            # Alto engagement - Focus su monetization
            suggestions.append(self._create_monetization_campaign(channel_analysis, budget))
            suggestions.append(self._create_premium_campaign(channel_analysis, budget))
        
        if channel_analysis.total_followers < 10000:
            # Basso numero di follower - Focus su growth
            suggestions.append(self._create_growth_campaign(channel_analysis, budget))
            suggestions.append(self._create_viral_campaign(channel_analysis, budget))
        else:
            # Alto numero di follower - Focus su engagement
            suggestions.append(self._create_engagement_campaign(channel_analysis, budget))
            suggestions.append(self._create_loyalty_campaign(channel_analysis, budget))
        
        # Sempre suggerisci una campagna di awareness
        suggestions.append(self._create_awareness_campaign(channel_analysis, budget))
        
        return suggestions
    
    def _create_growth_campaign(
        self,
        analysis: ChannelAnalysis,
        budget: Optional[float] = None,
    ) -> CampaignSuggestion:
        """Crea una campagna di crescita"""
        base_budget = budget or 100.0
        
        return CampaignSuggestion(
            campaign_type="growth",
            title="🚀 Accelerazione Crescita",
            description=f"Campagna focalizzata sulla crescita di follower per {analysis.channel_handle}. "
                       f"Perfetto per canali emergenti con tematica: {analysis.topic or 'generale'}",
            recommended_budget=base_budget * 0.5,
            estimated_reach=base_budget * 1000,  # 1000 impressioni per dollaro
            estimated_engagement=base_budget * 50,  # ~50 engagement per dollaro
            content_focus="Viral content, trend, challenge",
            targeting={
                "interests": analysis.content_themes or [],
                "behavior": "follower di canali simili",
                "demographics": analysis.audience_demographics or {},
            },
            timing={
                "best_time": analysis.best_posting_time,
                "duration": "2 settimane",
                "frequency": "3-4 post al giorno",
            },
            expected_roi=3.5,
            reasoning=f"Il tuo canale ha {analysis.total_followers} follower con engagement del {analysis.engagement_rate:.2%}. "
                     f"Una campagna di crescita può aiutare a triplicare i nuovi follower in 2 settimane.",
        )
    
    def _create_engagement_campaign(
        self,
        analysis: ChannelAnalysis,
        budget: Optional[float] = None,
    ) -> CampaignSuggestion:
        """Crea una campagna di engagement"""
        base_budget = budget or 150.0
        
        return CampaignSuggestion(
            campaign_type="engagement",
            title="💬 Boost Engagement",
            description=f"Campagna per aumentare l'engagement sui post di {analysis.channel_handle}. "
                       f"Perfetto per canali consolidati.",
            recommended_budget=base_budget * 0.7,
            estimated_reach=base_budget * 800,
            estimated_engagement=base_budget * 100,  # Maggiore focus su engagement
            content_focus="Domande, sondaggi, user-generated content",
            targeting={
                "interests": analysis.content_themes or [],
                "behavior": "utenti attivi su contenuti simili",
                "demographics": analysis.audience_demographics or {},
            },
            timing={
                "best_time": analysis.best_posting_time,
                "duration": "3 settimane",
                "frequency": "2-3 post al giorno",
            },
            expected_roi=2.8,
            reasoning=f"Con {analysis.total_followers} follower, hai una base solida. "
                     f"Aumentare l'engagement dal {analysis.engagement_rate:.2%} al 15% può triplicare il reach organico.",
        )
    
    def _create_monetization_campaign(
        self,
        analysis: ChannelAnalysis,
        budget: Optional[float] = None,
    ) -> CampaignSuggestion:
        """Crea una campagna di monetization"""
        base_budget = budget or 200.0
        
        return CampaignSuggestion(
            campaign_type="monetization",
            title="💰 Monetizzazione Premium",
            description=f"Campagna per monetizzare il tuo canale {analysis.channel_handle} "
                       f"con alto engagement ({analysis.engagement_rate:.2%}).",
            recommended_budget=base_budget,
            estimated_reach=base_budget * 1200,
            estimated_engagement=base_budget * 150,
            content_focus="Sponsored content, affiliate marketing, products",
            targeting={
                "interests": analysis.content_themes or [],
                "behavior": "utenti con alta propensione all'acquisto",
                "demographics": analysis.audience_demographics or {},
            },
            timing={
                "best_time": analysis.best_posting_time,
                "duration": "4 settimane",
                "frequency": "1-2 sponsored post al giorno",
            },
            expected_roi=5.2,
            reasoning=f"Il tuo engagement rate del {analysis.engagement_rate:.2%} è eccellente! "
                     f"Puoi monetizzare con campagne premium e generare €{base_budget * 4:.0f} al mese.",
        )
    
    def _create_viral_campaign(
        self,
        analysis: ChannelAnalysis,
        budget: Optional[float] = None,
    ) -> CampaignSuggestion:
        """Crea una campagna virale"""
        base_budget = budget or 150.0
        
        return CampaignSuggestion(
            campaign_type="viral",
            title="⚡ Viral Booster",
            description=f"Campagna aggressiva per creare contenuti virali su {analysis.channel_handle}. "
                       f"Perfetto per la rapida crescita.",
            recommended_budget=base_budget * 0.6,
            estimated_reach=base_budget * 2000,  # Massimo reach
            estimated_engagement=base_budget * 60,
            content_focus="Trending topics, meme, challenge, shock value",
            targeting={
                "interests": analysis.content_themes or [],
                "behavior": "utenti che condividono contenuti virali",
                "demographics": {"age_range": "18-35", "activity": "high"},
            },
            timing={
                "best_time": "ore di punta (18-22)",
                "duration": "10 giorni",
                "frequency": "1-2 post virali al giorno",
            },
            expected_roi=4.1,
            reasoning=f"I tuoi temi principali ({', '.join(analysis.content_themes or ['trending'])}) "
                     f"sono perfetti per contenuti virali. Aspettati 5x il reach normale.",
        )
    
    def _create_premium_campaign(
        self,
        analysis: ChannelAnalysis,
        budget: Optional[float] = None,
    ) -> CampaignSuggestion:
        """Crea una campagna premium/brand"""
        base_budget = budget or 250.0
        
        return CampaignSuggestion(
            campaign_type="brand",
            title="👑 Premium Brand Campaign",
            description=f"Campagna di posizionamento premium per {analysis.channel_handle}. "
                       f"Perfetto per brand awareness e posizionamento di lusso.",
            recommended_budget=base_budget,
            estimated_reach=base_budget * 900,
            estimated_engagement=base_budget * 80,
            content_focus="Luxury content, exclusive access, brand storytelling",
            targeting={
                "interests": analysis.content_themes or [],
                "behavior": "utenti premium, early adopters, influencer followers",
                "demographics": {"income": "high", "education": "university+"},
            },
            timing={
                "best_time": analysis.best_posting_time,
                "duration": "1 mese",
                "frequency": "1 premium post al giorno",
            },
            expected_roi=3.8,
            reasoning=f"Con l'alto engagement rate ({analysis.engagement_rate:.2%}), il tuo canale è pronto "
                     f"per campagne premium a tariffe premium. Rivolgi ai brand luxury.",
        )
    
    def _create_loyalty_campaign(
        self,
        analysis: ChannelAnalysis,
        budget: Optional[float] = None,
    ) -> CampaignSuggestion:
        """Crea una campagna di retention/loyalty"""
        base_budget = budget or 120.0
        
        return CampaignSuggestion(
            campaign_type="loyalty",
            title="❤️ Loyalty & Retention",
            description=f"Campagna per mantenere e aumentare la loyalty dei tuoi {analysis.total_followers} follower.",
            recommended_budget=base_budget * 0.5,
            estimated_reach=base_budget * 600,
            estimated_engagement=base_budget * 120,  # Massimo engagement
            content_focus="Exclusive content, behind-the-scenes, community building",
            targeting={
                "interests": analysis.content_themes or [],
                "behavior": "followers attuali, super-fans",
                "demographics": analysis.audience_demographics or {},
            },
            timing={
                "best_time": analysis.best_posting_time,
                "duration": "4 settimane",
                "frequency": "1-2 exclusive post al giorno",
            },
            expected_roi=4.5,
            reasoning=f"I tuoi {analysis.total_followers} follower attuali sono i tuoi beni più preziosi. "
                     f"Mantenerli attivi genererà ricorrenti entrate pubblicitarie.",
        )
    
    def _create_awareness_campaign(
        self,
        analysis: ChannelAnalysis,
        budget: Optional[float] = None,
    ) -> CampaignSuggestion:
        """Crea una campagna di awareness"""
        base_budget = budget or 100.0
        
        return CampaignSuggestion(
            campaign_type="awareness",
            title="🎯 Brand Awareness",
            description=f"Campagna di awareness generale per {analysis.channel_handle} "
                       f"con focus su nuovi utenti interessati a: {analysis.topic or 'tuoi contenuti'}",
            recommended_budget=base_budget * 0.4,
            estimated_reach=base_budget * 1500,  # Massimo reach
            estimated_engagement=base_budget * 45,
            content_focus="Educational, informational, intro content",
            targeting={
                "interests": analysis.content_themes or [],
                "behavior": "utenti interessati a {topic}",
                "demographics": analysis.audience_demographics or {},
            },
            timing={
                "best_time": "ore di ufficio (9-17)",
                "duration": "2 settimane",
                "frequency": "3-4 post informativi al giorno",
            },
            expected_roi=2.5,
            reasoning=f"Costruisci consapevolezza su ampia scala. Questa campagna è il fondamento "
                     f"per tutte le altre strategie di crescita.",
        )
    
    def _calculate_engagement_rate(
        self,
        metrics: Dict,
        followers: int,
    ) -> float:
        """Calcola engagement rate"""
        if followers == 0:
            return 0.0
        
        total_engagement = metrics.get("total_likes", 0) + metrics.get("total_comments", 0)
        return total_engagement / (followers * 10) if followers > 0 else 0.0
    
    def _calculate_avg_engagement(self, posts_data: List[Dict]) -> float:
        """Calcola media engagement per post"""
        if not posts_data:
            return 0.0
        
        total_engagement = sum(
            post.get("likes", 0) + post.get("comments", 0)
            for post in posts_data
        )
        return total_engagement / len(posts_data)
    
    def _analyze_posting_frequency(self, posts_data: List[Dict]) -> str:
        """Analizza frequenza di posting"""
        if not posts_data or len(posts_data) < 2:
            return "unknown"
        
        # Simple heuristic basato su numero di post
        post_count = len(posts_data)
        
        if post_count >= 20:
            return "Molto alta (5+ al giorno)"
        elif post_count >= 10:
            return "Alta (2-4 al giorno)"
        elif post_count >= 5:
            return "Media (1-2 al giorno)"
        else:
            return "Bassa (< 1 al giorno)"
    
    def _find_best_posting_time(self, posts_data: List[Dict]) -> str:
        """Trova il miglior orario di posting"""
        if not posts_data:
            return "18-22 (default)"
        
        # Heuristic semplice
        best_engagement = 0
        best_hour = "18-22"
        
        hours = {}
        for post in posts_data:
            hour = post.get("hour", 18)
            engagement = post.get("likes", 0) + post.get("comments", 0)
            
            if hour not in hours:
                hours[hour] = {"engagement": 0, "count": 0}
            
            hours[hour]["engagement"] += engagement
            hours[hour]["count"] += 1
        
        for hour, data in hours.items():
            avg_engagement = data["engagement"] / data["count"]
            if avg_engagement > best_engagement:
                best_engagement = avg_engagement
                best_hour = f"{hour}-{hour+1}"
        
        return best_hour
    
    def _extract_content_themes(self, posts_data: List[Dict]) -> List[str]:
        """Estrae temi principali dei contenuti"""
        themes = set()
        
        for post in posts_data:
            if "hashtags" in post:
                # Estrai hashtag come temi
                for tag in post["hashtags"][:3]:
                    themes.add(tag.lstrip("#"))
            
            if "category" in post:
                themes.add(post["category"])
        
        # Default themes se none found
        if not themes:
            themes = {"tecnologia", "lifestyle", "intrattenimento"}
        
        return list(themes)[:5]
    
    def _estimate_demographics(self, followers: int) -> Dict:
        """Stima dati demografici base"""
        return {
            "size": "small" if followers < 5000 else "medium" if followers < 50000 else "large",
            "growth_potential": "high" if followers < 10000 else "medium",
            "age_range": "18-45",
            "activity_level": "high",
        }
    
    def _analyze_competitors(self, topic: Optional[str]) -> Dict:
        """Analizza i competitor nello stesso spazio"""
        return {
            "competitor_count": 50 if topic else 100,
            "market_saturation": "medium",
            "opportunity": "high",
            "recommendation": "Focus su unique angle e personality",
        }
    
    def _analyze_growth_trends(self, posts_data: List[Dict]) -> Dict:
        """Analizza trend di crescita"""
        if not posts_data:
            return {
                "trend": "stable",
                "growth_rate": 0.0,
                "forecast": "stable for next month",
            }
        
        # Simple trend analysis
        return {
            "trend": "growing" if len(posts_data) > 5 else "stable",
            "growth_rate": 0.15,  # 15% al mese
            "forecast": "Growth expected with proper strategy",
            "recommendation": "Maintain consistency and engage with audience",
        }
    
    def _generate_recommendations(
        self,
        followers: int,
        engagement_rate: float,
        themes: List[str],
    ) -> List[str]:
        """Genera raccomandazioni generali"""
        recommendations = []
        
        if followers < 1000:
            recommendations.append("🎯 Focalizzati su crescita organica nei prossimi 3 mesi")
            recommendations.append("📱 Potenzia la presence sui social con la stessa username")
        
        if engagement_rate < 0.02:
            recommendations.append("💬 Aumenta l'interazione con i follower (domande, sondaggi)")
            recommendations.append("🎯 Adatta i contenuti ai feedback dei tuoi follower")
        
        if not themes:
            recommendations.append("📌 Definisci una nicchia/tema principale per il canale")
        
        recommendations.append("📊 Monitora analytics settimanalmente")
        recommendations.append("🤖 Usa AI per generare contenuti consistenti di qualità")
        
        return recommendations[:5]
