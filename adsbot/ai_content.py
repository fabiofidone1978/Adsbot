"""
Adsbot - AI Content Generation Module
Generates ad content, posts, and marketing materials using AI
"""

import json
import logging
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Type of content to generate"""
    AD_COPY = "ad_copy"           # Short ad copy
    POST = "post"                  # Social media post
    HEADLINE = "headline"          # Attention-grabbing headline
    CALL_TO_ACTION = "cta"        # Call to action text
    DESCRIPTION = "description"    # Detailed description
    EMAIL_SUBJECT = "email_subject"  # Email subject line
    EMAIL_BODY = "email_body"      # Email body
    HASHTAGS = "hashtags"          # Relevant hashtags
    LANDING_PAGE = "landing_page"  # Landing page copy


class ToneType(Enum):
    """Tone of generated content"""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    URGENT = "urgent"
    LUXURY = "luxury"
    PLAYFUL = "playful"
    EDUCATIONAL = "educational"
    INSPIRATIONAL = "inspirational"
    HUMOROUS = "humorous"


@dataclass
class ContentRequest:
    """Request parameters for content generation"""
    content_type: ContentType
    topic: str
    tone: ToneType = ToneType.FRIENDLY
    target_audience: str = "general"
    max_length: int = 280
    keywords: List[str] = None
    context: str = ""
    language: str = "it"
    budget_range: Optional[str] = None
    call_to_action: Optional[str] = None


@dataclass
class GeneratedContent:
    """Generated content response"""
    content_type: ContentType
    text: str
    tone: ToneType
    tokens_used: int
    language: str
    variations: List[str] = None
    confidence_score: float = 0.85


class AIContentGenerator:
    """
    AI-powered content generation for advertising campaigns.
    Generates marketing materials, posts, headlines, and ad copy.
    """
    
    def __init__(self):
        """Initialize AI content generator"""
        self.model = "gpt-like-model"
        self.language = "it"
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict:
        """Load content templates for fallback"""
        return {
            "ad_copy_luxury": [
                "Scopri {topic}. Esclusivo, premium, inimitabile.",
                "{topic} per chi non scende a compromessi. Qualità garantita.",
                "Il tuo meritato upgrade verso {topic}.",
            ],
            "ad_copy_urgent": [
                "⏰ ULTIMA CHANCE: {topic} - Offerta limitata!",
                "🚨 {topic} - Disponibilità ridotta. Agisci ora!",
                "Non aspettare! {topic} - Offerta a termine.",
            ],
            "headline_professional": [
                "Massimizza i risultati con {topic}",
                "{topic}: La soluzione che cercavi",
                "Scopri come {topic} cambia tutto",
            ],
            "headline_playful": [
                "Pronto per il tuo {topic} moment?",
                "{topic} isn't just great, it's {topic}!",
                "Perché aspettare? Vedi {topic} in azione",
            ],
            "cta_professional": [
                "Scopri di più",
                "Inizia ora",
                "Accedi alla piattaforma",
                "Ricevi una demo",
            ],
            "cta_urgent": [
                "Accedi subito",
                "Richiedi accesso immediato",
                "Garantisci il tuo posto",
                "Non perdere questa occasione",
            ],
            "hashtags": [
                "#AdsTech", "#MarketingDigitale", "#CampagneAnnunci",
                "#DigitalMarketing", "#SocialMedia", "#ContentMarketing",
                "#StartupItalia", "#Innovazione", "#GrowthHacking",
            ],
        }
    
    def generate_post(
        self,
        request: ContentRequest
    ) -> GeneratedContent:
        """
        Generate a social media post.
        
        Args:
            request: ContentRequest with post parameters
            
        Returns:
            GeneratedContent with generated post
        """
        logger.info(f"Generating post for topic: {request.topic}")
        
        # Build prompt
        prompt = self._build_prompt(request)
        
        # Generate content
        generated_text = self._call_ai_api(prompt, request)
        
        # Generate variations
        variations = self._generate_variations(request, generated_text)
        
        return GeneratedContent(
            content_type=request.content_type,
            text=generated_text,
            tone=request.tone,
            tokens_used=len(generated_text.split()),
            language=request.language,
            variations=variations,
            confidence_score=0.92,
        )
    
    def generate_ad_copy(
        self,
        topic: str,
        tone: ToneType = ToneType.FRIENDLY,
        target_audience: str = "general",
        keywords: List[str] = None,
        max_length: int = 280,
    ) -> GeneratedContent:
        """
        Generate short ad copy.
        
        Args:
            topic: Main topic/product
            tone: Tone of the copy
            target_audience: Who is this for
            keywords: Important keywords to include
            max_length: Maximum character length
            
        Returns:
            GeneratedContent with ad copy
        """
        request = ContentRequest(
            content_type=ContentType.AD_COPY,
            topic=topic,
            tone=tone,
            target_audience=target_audience,
            max_length=max_length,
            keywords=keywords or [],
        )
        return self.generate_post(request)
    
    def generate_headline(
        self,
        topic: str,
        tone: ToneType = ToneType.PROFESSIONAL,
        max_length: int = 100,
        audience: str = "general",
    ) -> GeneratedContent:
        """
        Generate attention-grabbing headline.
        
        Args:
            topic: Main topic
            tone: Tone of headline
            max_length: Max characters
            audience: Target audience
            
        Returns:
            GeneratedContent with headline
        """
        request = ContentRequest(
            content_type=ContentType.HEADLINE,
            topic=topic,
            tone=tone,
            max_length=max_length,
            target_audience=audience,
        )
        return self.generate_post(request)
    
    def generate_call_to_action(
        self,
        action: str,
        tone: ToneType = ToneType.FRIENDLY,
    ) -> GeneratedContent:
        """
        Generate call-to-action text.
        
        Args:
            action: What action to promote (e.g., "signup", "purchase")
            tone: Tone of CTA
            
        Returns:
            GeneratedContent with CTA
        """
        request = ContentRequest(
            content_type=ContentType.CALL_TO_ACTION,
            topic=action,
            tone=tone,
            max_length=50,
        )
        return self.generate_post(request)
    
    def generate_email(
        self,
        topic: str,
        target_audience: str,
        tone: ToneType = ToneType.PROFESSIONAL,
    ) -> Dict[str, GeneratedContent]:
        """
        Generate complete email (subject + body).
        
        Args:
            topic: Email topic
            target_audience: Who to send to
            tone: Tone of email
            
        Returns:
            Dictionary with subject and body
        """
        subject_request = ContentRequest(
            content_type=ContentType.EMAIL_SUBJECT,
            topic=topic,
            tone=tone,
            target_audience=target_audience,
            max_length=100,
        )
        
        body_request = ContentRequest(
            content_type=ContentType.EMAIL_BODY,
            topic=topic,
            tone=tone,
            target_audience=target_audience,
            max_length=1000,
        )
        
        return {
            "subject": self.generate_post(subject_request),
            "body": self.generate_post(body_request),
        }
    
    def generate_hashtags(
        self,
        topic: str,
        count: int = 5,
        language: str = "it",
    ) -> List[str]:
        """
        Generate relevant hashtags.
        
        Args:
            topic: Topic for hashtags
            count: Number of hashtags
            language: Language for hashtags
            
        Returns:
            List of hashtags
        """
        # Use templates as primary source
        base_tags = self.templates.get("hashtags", [])
        
        # Add topic-specific tags
        topic_tags = [f"#{word.replace(' ', '')}" for word in topic.split()[:2]]
        
        # Combine and return
        all_tags = base_tags + topic_tags
        return all_tags[:count]
    
    def generate_campaign_bundle(
        self,
        product_name: str,
        product_description: str,
        target_audience: str,
        tone: ToneType = ToneType.FRIENDLY,
        budget_range: Optional[str] = None,
    ) -> Dict[str, GeneratedContent]:
        """
        Generate complete campaign bundle.
        
        Args:
            product_name: Product/service name
            product_description: Description
            target_audience: Target audience
            tone: Campaign tone
            budget_range: Budget range if applicable
            
        Returns:
            Dictionary with all campaign materials
        """
        logger.info(f"Generating campaign bundle for: {product_name}")
        
        context = f"{product_name}: {product_description}"
        
        bundle = {
            "headline": self.generate_headline(product_name, tone, audience=target_audience),
            "ad_copy": self.generate_ad_copy(product_name, tone, target_audience),
            "post": self.generate_post(ContentRequest(
                content_type=ContentType.POST,
                topic=product_name,
                tone=tone,
                target_audience=target_audience,
                context=context,
            )),
            "cta": self.generate_call_to_action("scopri", tone),
            "hashtags": self.generate_hashtags(product_name),
        }
        
        return bundle
    
    def _build_prompt(self, request: ContentRequest) -> str:
        """Build AI prompt from request"""
        prompt = f"""
Genera contenuto per annunci pubblicitari.

Topic: {request.topic}
Tipo di contenuto: {request.content_type.value}
Tono: {request.tone.value}
Audience: {request.target_audience}
Lingua: {request.language}
Max lunghezza: {request.max_length} caratteri
        """
        
        if request.keywords:
            prompt += f"\nKeywords da includere: {', '.join(request.keywords)}"
        
        if request.context:
            prompt += f"\nContesto: {request.context}"
        
        if request.call_to_action:
            prompt += f"\nCall to action: {request.call_to_action}"
        
        prompt += "\n\nGenerare contenuto persuasivo e accattivante."
        
        return prompt
    
    def _call_ai_api(self, prompt: str, request: ContentRequest) -> str:
        """Call AI API to generate content"""
        # In production, this would call OpenAI, Anthropic, etc.
        # For now, use template-based generation
        
        template_key = f"{request.content_type.value}_{request.tone.value}"
        templates = self.templates.get(template_key, None)
        
        if templates:
            # Use first template as base
            content = templates[0].format(topic=request.topic)
        else:
            # Fallback
            content = f"{request.topic} - Scopri come può cambiarti la vita!"
        
        # Ensure within length limit
        if len(content) > request.max_length:
            content = content[:request.max_length].rsplit(' ', 1)[0] + "..."
        
        return content
    
    def _generate_variations(
        self,
        request: ContentRequest,
        base_content: str,
        count: int = 2,
    ) -> List[str]:
        """Generate content variations"""
        variations = []
        
        # Variation 1: Shorter version
        words = base_content.split()
        if len(words) > 10:
            short_version = ' '.join(words[:len(words)//2])
            if short_version.endswith(' '):
                short_version = short_version[:-1]
            variations.append(short_version + "...")
        
        # Variation 2: With emoji
        emojis = ["🎯", "✨", "🚀", "💡", "⭐"]
        emoji_version = f"{emojis[hash(base_content) % len(emojis)]} {base_content}"
        if len(emoji_version) <= request.max_length + 2:
            variations.append(emoji_version)
        
        return variations[:count]
    
    def optimize_for_platform(
        self,
        content: str,
        platform: str,
    ) -> str:
        """
        Optimize content for specific platform.
        
        Args:
            content: Original content
            platform: Target platform (instagram, facebook, telegram, etc)
            
        Returns:
            Optimized content
        """
        if platform == "instagram":
            # Add relevant Instagram hashtags
            hashtags = self.generate_hashtags(content, count=10)
            return f"{content}\n\n{' '.join(hashtags)}"
        
        elif platform == "telegram":
            # Keep it concise, no hashtags needed
            return content[:200]
        
        elif platform == "facebook":
            # Add emoji, keep length reasonable
            emoji = "🎯"
            return f"{emoji} {content}"
        
        elif platform == "twitter":
            # Strict 280 character limit
            return content[:280]
        
        else:
            return content
    
    def A_B_test_variations(
        self,
        base_topic: str,
        tone: ToneType = ToneType.FRIENDLY,
        variations: int = 3,
    ) -> List[Dict]:
        """
        Generate A/B test variations of content.
        
        Args:
            base_topic: Topic to create variations for
            tone: Base tone
            variations: Number of variations
            
        Returns:
            List of variations with performance recommendations
        """
        test_variations = []
        
        tones = [
            ToneType.PROFESSIONAL,
            ToneType.PLAYFUL,
            ToneType.URGENT,
        ]
        
        for i, alt_tone in enumerate(tones[:variations]):
            variant = {
                "variation_id": chr(65 + i),  # A, B, C, etc
                "tone": alt_tone.value,
                "content": self._call_ai_api(
                    f"Topic: {base_topic}, Tone: {alt_tone.value}",
                    ContentRequest(
                        content_type=ContentType.AD_COPY,
                        topic=base_topic,
                        tone=alt_tone,
                    )
                ),
                "expected_ctr": 0.025 + (i * 0.005),  # Slight variation
                "recommendation": f"Variazione {chr(65 + i)}: Usa tono {alt_tone.value}",
            }
            test_variations.append(variant)
        
        return test_variations


class ContentTemplateLibrary:
    """
    Pre-built content templates for quick generation.
    """
    
    ECOMMERCE_TEMPLATES = {
        "flash_sale": "⚡ OFFERTA LAMPO! {product} a {price}€ - Solo oggi!",
        "new_product": "🎉 Novità! Scopri {product} - Il nuovo must-have",
        "seasonal": "🌟 Collezione {season}: {product} a prezzo speciale",
    }
    
    SAAS_TEMPLATES = {
        "trial": "🚀 Prova {product} gratis per 14 giorni - Nessuna carta di credito richiesta",
        "feature": "✨ {product} ti permette di {benefit}",
        "success_story": "📈 Aumenta il tuo ROI con {product} - Scopri come!",
    }
    
    SOCIAL_TEMPLATES = {
        "engagement": "❓ {question} Condividi la tua opinione nei commenti!",
        "tip": "💡 Trucco del giorno: {tip}",
        "behind_scenes": "👀 Dietro le quinte: {story}",
    }
    
    @classmethod
    def get_template(cls, category: str, template_name: str, **kwargs) -> str:
        """
        Get template and fill variables.
        
        Args:
            category: Template category (ecommerce, saas, social)
            template_name: Template name
            **kwargs: Variables to fill
            
        Returns:
            Filled template string
        """
        templates_map = {
            "ecommerce": cls.ECOMMERCE_TEMPLATES,
            "saas": cls.SAAS_TEMPLATES,
            "social": cls.SOCIAL_TEMPLATES,
        }
        
        template_dict = templates_map.get(category, {})
        template = template_dict.get(template_name, "")
        
        if not template:
            return f"Template non trovato: {category}/{template_name}"
        
        return template.format(**kwargs)


# Utility functions
def generate_quick_ad(topic: str, tone: str = "friendly") -> str:
    """Quick ad generation helper"""
    generator = AIContentGenerator()
    tone_enum = ToneType[tone.upper()] if hasattr(ToneType, tone.upper()) else ToneType.FRIENDLY
    content = generator.generate_ad_copy(topic, tone=tone_enum)
    return content.text


def generate_social_post(topic: str, platform: str = "instagram") -> str:
    """Quick social post generation helper"""
    generator = AIContentGenerator()
    content = generator.generate_post(ContentRequest(
        content_type=ContentType.POST,
        topic=topic,
    ))
    return generator.optimize_for_platform(content.text, platform)


def create_campaign_content(
    product_name: str,
    description: str,
    audience: str,
) -> Dict:
    """Quick campaign content generation helper"""
    generator = AIContentGenerator()
    return generator.generate_campaign_bundle(product_name, description, audience)
