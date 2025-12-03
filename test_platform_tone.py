#!/usr/bin/env python
"""Test platform and tone selection for AI campaign generation."""

import os
import asyncio
from adsbot.chatgpt_integration import ChatGPTCampaignGenerator
from adsbot.models import Channel, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Load API key
api_key = os.getenv('OPENAI_API_KEY', '')
if not api_key:
    print('❌ No OpenAI API key found in environment')
    exit(1)

print('✅ API key loaded')

# Initialize generator
gen = ChatGPTCampaignGenerator(api_key)
print(f'✅ Generator initialized: {gen.enabled}')

# Create a mock channel
class MockChannel:
    def __init__(self):
        self.handle = "techitalia"
        self.topic = "Tecnologia e innovazione in italiano"
        self.description = "Il canale numero uno per notizie sulla tecnologia italiana"

channel = MockChannel()

# Test each platform and tone combination
platforms = ["telegram", "instagram", "facebook", "twitter"]
tones = ["professional", "friendly", "aggressive", "playful"]

print("\n" + "="*60)
print("Testing: Telegram + Professional")
print("="*60)

campaign = gen.generate_campaign_for_platform(
    channel=channel,
    platform="telegram",
    tone="professional"
)

if campaign:
    print(f"✅ Campaign generated successfully!")
    print(f"\n📋 Title: {campaign.title}")
    print(f"📝 Description: {campaign.description}")
    print(f"🎯 CTA: {campaign.cta_text}")
    print(f"💰 Budget: €{campaign.suggested_budget:.2f}")
    print(f"🏷️ Keywords: {', '.join(campaign.keywords)}")
    print(f"👥 Target: {campaign.target_audience}")
else:
    print("❌ Failed to generate campaign")
