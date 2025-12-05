"""ChatGPT integration for campaign generation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CampaignContent:
    """Contenuto della campagna generata da ChatGPT con brief immagine ADV."""
    title: str
    description: str
    cta_text: str
    suggested_budget: float
    keywords: list[str]
    target_audience: str
    image_prompt: str  # Brief in italiano per l'immagine ADV di accompagnamento


class ChatGPTCampaignGenerator:
    """Generate campaigns using ChatGPT API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize ChatGPT generator."""
        self.api_key = api_key
        self.enabled = bool(api_key)
        
        if self.enabled:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
            except ImportError:
                logger.warning("openai package not installed. ChatGPT integration disabled.")
                self.enabled = False
    
    def generate_campaign(
        self,
        channel_name: str,
        channel_topic: str,
        channel_description: str,
        engagement_rate: float,
    ) -> Optional[CampaignContent]:
        """Generate a campaign using ChatGPT based on channel data."""
        
        if not self.enabled:
            logger.warning("ChatGPT API key not configured")
            return None
        
        try:
            import json
            
            prompt = f"""Analizza il seguente canale Telegram e crea una campagna pubblicitaria personalizzata IN ITALIANO:

**Informazioni Canale:**
- Nome: {channel_name}
- Argomento: {channel_topic}
- Descrizione: {channel_description}
- Engagement Rate: {engagement_rate:.2%}

Genera una campagna pubblicitaria completa ESCLUSIVAMENTE IN ITALIANO con il seguente formato JSON:
{{
    "title": "Titolo accattivante della campagna in italiano",
    "description": "Descrizione dettagliata della campagna in italiano (2-3 frasi)",
    "cta_text": "Testo della Call-To-Action in italiano",
    "suggested_budget": 50.00,
    "keywords": ["keyword1_italiano", "keyword2_italiano", "keyword3_italiano"],
    "target_audience": "Descrizione del target audience in italiano",
    "image_prompt": "Brief in italiano per generare immagine ADV: descrizione visiva dell'asset pubblicità"
}}

IMPORTANTE: Rispondi SOLO con il JSON valido. Tutti i testi (title, description, cta_text, keywords, target_audience, image_prompt) devono essere ESCLUSIVAMENTE in italiano.
Senza markdown, senza commenti, solo JSON."""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert social media campaign strategist."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=500
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Estrai JSON dalla risposta
            try:
                campaign_data = json.loads(response_text)
            except json.JSONDecodeError:
                # Prova ad estrarre JSON se è wrappato in markdown
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                    campaign_data = json.loads(json_str)
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                    campaign_data = json.loads(json_str)
                else:
                    raise
            
            return CampaignContent(
                title=campaign_data.get("title", "Campaign"),
                description=campaign_data.get("description", ""),
                cta_text=campaign_data.get("cta_text", "Scopri di più"),
                suggested_budget=float(campaign_data.get("suggested_budget", 50.0)),
                keywords=campaign_data.get("keywords", []),
                target_audience=campaign_data.get("target_audience", ""),
                image_prompt=campaign_data.get("image_prompt", "Immagine pubblicitaria per campagna Telegram")
            )
        
        except Exception as e:
            logger.error(f"Error generating campaign with ChatGPT: {e}")
            return None
    
    def generate_campaign_for_channel(self, channel) -> Optional[CampaignContent]:
        """Generate campaign for a specific channel object."""
        
        return self.generate_campaign(
            channel_name=channel.handle or "Channel",
            channel_topic=channel.topic or "General content",
            channel_description=channel.title or "A Telegram channel",
            engagement_rate=0.05  # Default 5%, in produzione calcolarlo dai dati
        )

    
    def generate_campaign_for_platform(
        self,
        channel,
        platform: str = "telegram",
        tone: str = "professional"
    ) -> Optional[CampaignContent]:
        """Generate campaign for a specific platform and tone."""
        
        if not self.enabled:
            logger.warning("ChatGPT API key not configured")
            return None
        
        try:
            import json
            
            # Platform-specific guidelines
            platform_guidelines = {
                "telegram": "Conciso, con emoji, supporta markdown. Max 4000 caratteri."
            }
            
            # Tone guidelines
            tone_guidelines = {
                "professional": "Formale, serio, affidabile. Usa linguaggio professionale.",
                "friendly": "Cordiale, accogliente, conversazionale. Crea connessione.",
                "aggressive": "Urgente, stimolante, FOMO. Incoraggia azione immediata.",
                "playful": "Divertente, leggero, con humor. Emojis e linguaggio casual."
            }
            
            platform_guide = platform_guidelines.get(platform, platform_guidelines["telegram"])
            tone_guide = tone_guidelines.get(tone, tone_guidelines["professional"])
            
            prompt = f"""Analizza il seguente canale Telegram e crea una campagna pubblicitaria personalizzata PER {platform.upper()} IN ITALIANO:

**Informazioni Canale:**
- Nome: {channel.handle or "Channel"}
- Argomento: {channel.topic or "Contenuto generale"}
- Titolo: {channel.title or "Un canale Telegram"}

**Specifiche Piattaforma ({platform.upper()}):**
{platform_guide}

**Tono Richiesto ({tone.upper()}):**
{tone_guide}

Genera una campagna pubblicitaria completa ESCLUSIVAMENTE IN ITALIANO con il seguente formato JSON:
{{
    "title": "Titolo accattivante della campagna in italiano per {platform}",
    "description": "Descrizione della campagna in italiano, ottimizzata per {platform} con tono {tone} (2-3 frasi)",
    "cta_text": "Testo della Call-To-Action in italiano appropriato per {platform} e tono {tone}",
    "suggested_budget": 50.00,
    "keywords": ["keyword1_italiano", "keyword2_italiano", "keyword3_italiano"],
    "target_audience": "Descrizione del target audience italiano per {platform}",
    "image_prompt": "Brief visivo in italiano per generare immagine ADV per {platform} con tono {tone}"
}}

IMPORTANTE: Rispondi SOLO con il JSON valido. Tutto il contenuto (title, description, cta_text, keywords, target_audience, image_prompt) deve essere ESCLUSIVAMENTE in italiano.
Senza markdown, senza commenti, solo JSON.
Assicurati che sia ottimizzato per {platform} e segua il tono {tone}."""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert social media campaign strategist specializing in platform-specific content optimization."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=500
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Estrai JSON dalla risposta
            try:
                campaign_data = json.loads(response_text)
            except json.JSONDecodeError:
                # Prova ad estrarre JSON se è wrappato in markdown
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                    campaign_data = json.loads(json_str)
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                    campaign_data = json.loads(json_str)
                else:
                    raise
            return CampaignContent(
                title=campaign_data.get("title", "Campaign"),
                description=campaign_data.get("description", ""),
                cta_text=campaign_data.get("cta_text", "Scopri di più"),
                suggested_budget=float(campaign_data.get("suggested_budget", 50.0)),
                keywords=campaign_data.get("keywords", []),
                target_audience=campaign_data.get("target_audience", ""),
                image_prompt=campaign_data.get("image_prompt", f"Immagine pubblicitaria per {platform} con tono {tone}")
            )
        
        except Exception as e:
            logger.error(f"Error generating campaign with ChatGPT for {platform}/{tone}: {e}")
            return None

