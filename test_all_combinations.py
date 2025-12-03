#!/usr/bin/env python
"""Test different platforms and tones for AI campaign generation."""

import os
from pathlib import Path
from dotenv import load_dotenv
from adsbot.chatgpt_integration import ChatGPTCampaignGenerator

# Load .env
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Load API key
api_key = os.getenv('OPENAI_API_KEY', '')
if not api_key:
    print('❌ No OpenAI API key found in environment')
    exit(1)

# Initialize generator
gen = ChatGPTCampaignGenerator(api_key)

# Create a mock channel
class MockChannel:
    def __init__(self):
        self.handle = "techitalia"
        self.topic = "Tecnologia e innovazione in italiano"
        self.description = "Il canale numero uno per notizie sulla tecnologia italiana"

channel = MockChannel()

# Test combinations
test_cases = [
    ("instagram", "playful"),
    ("twitter", "aggressive"),
    ("facebook", "friendly"),
]

for platform, tone in test_cases:
    print("\n" + "="*60)
    print(f"Testing: {platform.upper()} + {tone.upper()}")
    print("="*60)
    
    campaign = gen.generate_campaign_for_platform(
        channel=channel,
        platform=platform,
        tone=tone
    )
    
    if campaign:
        print(f"✅ Campaign generated!")
        print(f"📋 Title: {campaign.title}")
        print(f"📝 Description: {campaign.description[:80]}...")
        print(f"🎯 CTA: {campaign.cta_text}")
    else:
        print("❌ Failed to generate campaign")

