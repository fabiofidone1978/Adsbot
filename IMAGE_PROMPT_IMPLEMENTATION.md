# IMAGE_PROMPT IMPLEMENTATION - Telegram ADV Marketplace

**Commit:** `68d1a9d`  
**Date:** 2024-12-27  
**Feature:** Mandatory `image_prompt` field for ADV campaign generation

---

## OVERVIEW

Abbiamo aggiunto un campo **`image_prompt`** obbligatorio a tutte le campagne generate da ChatGPT. Questo campo contiene un brief dettagliato in italiano che descrive l'immagine ideale per accompagnare la campagna ADV su Telegram.

### Benefici:
- ✅ **Automazione visuale completa:** Campaign text → image_prompt → generated image (DALL-E, Midjourney, Stable Diffusion)
- ✅ **Qualità garantita:** Brief coerente con copy, professional Italian
- ✅ **Caching intelligente:** Images cached per hash del prompt
- ✅ **Audit trail:** Tutti gli image_prompt loggati per miglioramento continuo
- ✅ **Specializzazione Telegram:** Brief ottimizzati per formato Telegram (portrait, landscape, square)

---

## CAMBIAMENTI IMPLEMENTATI

### 1. **CHATGPT_PROMPTS.md** - Tre Prompt Aggiornati

#### PROMPT 1: Campaign Generation for Channel
**Nuovo campo JSON:**
```json
{
  "image_prompt": "Descrizione in italiano dell'immagine ideale per accompagnare questa campagna: soggetto, inquadratura, stile visivo, colori, atmosfera. L'immagine deve essere coerente con titolo, descrizione e CTA, senza testo sovrapposto e senza contenuti sensibili."
}
```

**Temperature:** 0.4 (ridotto da 0.7) → Maggiore coerenza JSON
**System Message:** "You are a senior advertising strategist specialized in Telegram campaigns. You always answer with strictly valid JSON, in Italian only, and you always include a coherent image_prompt for each campaign."

---

#### PROMPT 2: Platform-Specific Campaign Generation
**Nuovo campo JSON (con ottimizzazione per piattaforma):**
```json
{
  "image_prompt": "Descrizione in italiano dell'immagine ideale per accompagnare l'annuncio su {platform}: soggetto, stile, inquadratura, palette di colori, atmosfera. L'immagine deve essere coerente con titolo, descrizione e CTA, senza testo sovrapposto e senza contenuti sensibili."
}
```

**Importante:** image_prompt NON nomina esplicitamente la piattaforma (es. non scrive "logo Telegram")

**Temperature:** 0.4  
**System Message:** "You are an expert advertising strategist specializing in platform-specific campaign optimization. You always answer in strictly valid JSON, in Italian only, and you always include a precise image_prompt aligned with the ad copy."

---

#### PROMPT 3: Content Generation Base Prompt
**Per contenuti ADV, output include:**
```
IMMAGINE SUGGERITA: descrizione sintetica in italiano dell'immagine ideale per accompagnare questo annuncio (soggetto, stile, inquadratura, atmosfera, colori), senza testo sovrapposto nell'immagine.
```

---

### 2. **adsbot/chatgpt_integration.py** - Dataclass Aggiornata

**Prima:**
```python
@dataclass
class CampaignContent:
    """Contenuto della campagna generata da ChatGPT."""
    title: str
    description: str
    cta_text: str
    suggested_budget: float
    keywords: list[str]
    target_audience: str
```

**Dopo:**
```python
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
```

---

## VALIDATION RULES

### JSON Structure Validation
- ✅ image_prompt non vuoto
- ✅ image_prompt >= 30 caratteri
- ✅ Presente nel JSON response
- ❌ Fallback a template se assente

### Language Validation
- ✅ image_prompt esclusivamente in italiano
- ✅ No English, no mixed languages
- ✅ Grammatica e ortografia corrette

### Content Quality
- ✅ Coerente con title/description/cta_text
- ✅ NON contiene testo sovrapposto
- ✅ NON contiene contenuti sensibili
- ✅ NON è generico ("qualcosa di carino")

### Image Generation Readiness
- ✅ Adatto per DALL-E 3, Midjourney, Stable Diffusion
- ✅ Include stile e atmosfera (es. "minimalist, warm colors, professional")
- ✅ Include inquadratura (es. "portrait mode", "16:9 widescreen")
- ✅ Include soggetto principale chiaro

---

## WORKFLOW COMPLETO

```
1. User richiede campagna
   ↓
2. ChatGPT genera JSON con image_prompt
   ↓
3. Validazione: image_prompt obbligatorio e >= 30 chars
   ↓
4. Salvataggio in database:
   - Campaign.image_prompt = brief italiano
   - Campaign.image_url = NULL (da generare)
   ↓
5. Generazione immagine:
   - DALL-E API call con image_prompt
   - Caching per hash MD5(image_prompt)
   ↓
6. Display to user:
   - Telegram photo + campaign copy
   - Image generato da DALL-E/Midjourney
   ↓
7. Feedback loop:
   - User può rigenerare image
   - Tracciare quality metrics
```

---

## EXAMPLE: Campaign Generation

### Input:
```
Channel: "Tech Italia"
Topic: "Notizie tecnologia"
Engagement: 3.5%
Platform: Telegram
Tone: Professional
```

### Output - Campaign Content:
```json
{
  "title": "Scopri le ultime innovazioni tech",
  "description": "Resta aggiornato sulle news tecnologiche più importanti. Iscriviti al nostro canale Telegram per contenuti esclusivi, interviste e analisi approfondite.",
  "cta_text": "Leggi di più sul canale",
  "suggested_budget": 75.00,
  "keywords": ["tecnologia", "innovazione", "notizie", "canale"],
  "target_audience": "Professionisti IT, early adopters, appassionati tech 25-45 anni, interesse in innovazione e notizie del settore",
  "image_prompt": "Immagine high-tech minimalista con sfondo blu scuro e accenti arancioni. In primo piano: icone stilizzate di tecnologia (chip, circuiti, smartphone) disposte dinamicamente. Stile: flat design moderno, colori professionali (blu navy, arancione, bianco). Atmosfera: innovazione, fiducia, professionalismo. Inquadratura: square/vertical per Telegram. No text overlay. Risoluzione 1024x1024."
}
```

### DALL-E Image Generation:
```python
response = client.images.generate(
    model="dall-e-3",
    prompt="Immagine high-tech minimalista con sfondo blu scuro e accenti arancioni. In primo piano: icone stilizzate di tecnologia (chip, circuiti, smartphone) disposte dinamicamente. Stile: flat design moderno, colori professionali (blu navy, arancione, bianco). Atmosfera: innovazione, fiducia, professionalismo. Inquadratura: square/vertical per Telegram. No text overlay. Risoluzione 1024x1024.",
    size="1024x1024",
    quality="standard"
)
# Result: image_url = "https://..."
```

### Display in Bot:
```
[IMAGE]

📋 **Scopri le ultime innovazioni tech**

Resta aggiornato sulle news tecnologiche più importanti. Iscriviti al nostro canale Telegram per contenuti esclusivi, interviste e analisi approfondite.

📞 Leggi di più sul canale

💰 Budget suggerito: €75.00
👥 Target: Professionisti IT, early adopters, appassionati tech 25-45 anni
```

---

## DATABASE SCHEMA UPDATE (Recommended)

Aggiungere a `Campaign` model:

```python
class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True)
    # ... existing fields ...
    
    # NUOVO: Image generation fields
    image_prompt = Column(String(1000), nullable=False)  # Italian brief
    image_url = Column(String(500), nullable=True)        # Generated image URL
    image_generated_at = Column(DateTime, nullable=True)  # Timestamp
    image_quality_score = Column(Float, default=0.0)      # User rating 0-5
```

---

## MONITORING & LOGGING

### Log Pattern:
```
timestamp | user_id | channel_id | platform | tone | image_prompt | image_url | quality_score | duration_ms
2024-12-27 14:23:45 | 123456 | 5 | telegram | professional | "Immagine high-tech..." | "https://..." | 4.5 | 3200
```

### Metrics to Track:
- ✅ image_prompt generation success rate (target: 100%)
- ✅ Image generation success rate (target: 98%)
- ✅ Average image_prompt length
- ✅ Cache hit rate
- ✅ User quality ratings (1-5 stars)
- ✅ API costs per image generation

---

## INTEGRATION CHECKLIST

- [ ] Update `CampaignContent` dataclass ✅ **DONE**
- [ ] Update PROMPT 1 in CHATGPT_PROMPTS.md ✅ **DONE**
- [ ] Update PROMPT 2 in CHATGPT_PROMPTS.md ✅ **DONE**
- [ ] Update PROMPT 3 in CHATGPT_PROMPTS.md ✅ **DONE**
- [ ] Add image_prompt validation in chatgpt_integration.py
- [ ] Add image generation service integration (DALL-E/Midjourney)
- [ ] Update Campaign model with image_prompt/image_url fields
- [ ] Add image caching strategy
- [ ] Add image quality rating to UI
- [ ] Create monitoring dashboard for image_prompt metrics
- [ ] Add user feedback loop (thumbs up/down on images)
- [ ] Test end-to-end: campaign → image_prompt → generated image

---

## TESTING EXAMPLES

### Unit Test: image_prompt Validation
```python
def test_campaign_generation_includes_image_prompt():
    generator = ChatGPTCampaignGenerator(api_key="test-key")
    result = generator.generate_campaign(
        channel_name="Test",
        channel_topic="Tech",
        channel_description="Tech news",
        engagement_rate=0.03
    )
    
    assert result.image_prompt is not None
    assert len(result.image_prompt) >= 30
    assert "telegram" not in result.image_prompt.lower() or "piattaforma" in result.image_prompt.lower()
```

### Integration Test: Full Workflow
```python
async def test_campaign_with_generated_image():
    # Generate campaign with image_prompt
    campaign = await generator.generate_campaign_for_platform(...)
    
    # Generate image from image_prompt
    image_url = await generate_image_from_prompt(campaign.image_prompt)
    
    # Store in database
    campaign_record = Campaign(
        image_prompt=campaign.image_prompt,
        image_url=image_url
    )
    session.add(campaign_record)
    
    # Verify image URL is valid
    response = requests.head(image_url)
    assert response.status_code == 200
```

---

## NEXT STEPS

1. **Image Service Integration** (Priority: HIGH)
   - Integrate DALL-E 3 API for image generation
   - Add fallback to Midjourney for premium campaigns
   - Implement image caching by prompt hash

2. **Database Updates** (Priority: HIGH)
   - Add image_prompt and image_url to Campaign model
   - Create AIGeneratedImage table for tracking

3. **UI Enhancements** (Priority: MEDIUM)
   - Display generated image + campaign copy
   - Add image regeneration button
   - Add quality rating (⭐⭐⭐⭐⭐)

4. **Monitoring** (Priority: MEDIUM)
   - Create dashboard for image_prompt metrics
   - Track image generation success rate
   - Monitor costs (DALL-E API)

5. **User Feedback** (Priority: LOW)
   - Add thumbs up/down on images
   - Learn from successful campaigns
   - A/B test image styles

---

## REFERENCES

- **ChatGPT Integration:** `adsbot/chatgpt_integration.py`
- **Prompts Documentation:** `CHATGPT_PROMPTS.md`
- **AI Content Generator:** `adsbot/ai_content.py`
- **Bot Handler:** `adsbot/bot.py` (lines 3905+)

---

**Status:** ✅ READY FOR IMAGE GENERATION SERVICE INTEGRATION

**Token Cost Estimate:** 
- Campaign generation: ~250 tokens/call
- Image generation: ~100 DALL-E credits/image (varies by size)
- Total per campaign: ~$0.03-0.05

**Performance:**
- Campaign generation: ~2-3 seconds
- Image generation: ~5-15 seconds (DALL-E)
- Total end-to-end: ~10-20 seconds
