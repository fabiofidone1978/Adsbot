CHATGPT PROMPTS & AI INTEGRATION
==================================

## File: adsbot/chatgpt_integration.py

### Location: Line 48-93
### Function: ChatGPTCampaignGenerator.generate_campaign()

#### PROMPT 1: Campaign Generation for Channel (Telegram + Immagine Obbligatoria)
```
Analizza il seguente canale Telegram e crea una campagna pubblicitaria personalizzata ESCLUSIVAMENTE IN ITALIANO.

OBIETTIVO:
- Proporre una campagna ADV realistica e immediatamente utilizzabile su Telegram.
- Generare sia i testi della campagna sia il brief per l'immagine ADV di accompagnamento.

INFORMAZIONI CANALE:
- Nome: {channel_name}
- Argomento principale: {channel_topic}
- Descrizione: {channel_description}
- Engagement Rate stimato: {engagement_rate:.2%}

VINCOLI DI STILE:
- Linguaggio chiaro, professionale e orientato alla conversione.
- Tono coerente con l'argomento del canale.
- Nessun testo in lingue diverse dall'italiano.
- Evitare promesse irrealistiche, claim non verificabili o contenuti fuorvianti.

DEVI PRODURRE UNICAMENTE UN OGGETTO JSON VALIDO CON QUESTA STRUTTURA:

{
  "title": "Titolo breve, chiaro e accattivante della campagna in italiano",
  "description": "Descrizione dettagliata della campagna in italiano (2-3 frasi, orientate al beneficio e all'azione)",
  "cta_text": "Testo della Call-To-Action in italiano, breve e diretto",
  "suggested_budget": 50.00,
  "keywords": ["keyword1_in_italiano", "keyword2_in_italiano", "keyword3_in_italiano"],
  "target_audience": "Descrizione del pubblico target in italiano (es. età, interessi, livello di consapevolezza)",
  "image_prompt": "Descrizione in italiano dell'immagine ideale per accompagnare questa campagna: soggetto, inquadratura, stile visivo, colori, atmosfera. L'immagine deve essere coerente con titolo, descrizione e CTA, senza testo sovrapposto e senza contenuti sensibili."
}

REQUISITI OBBLIGATORI:
- Rispondi SOLO con JSON valido, senza markdown, senza commenti, senza testo fuori dal JSON.
- Tutti i campi testuali (title, description, cta_text, keywords, target_audience, image_prompt) devono essere ESCLUSIVAMENTE in italiano.
- Usa valori concreti e plausibili, mai placeholder generici.
```

**System Message:** "You are a senior advertising strategist specialized in Telegram campaigns. You always answer with strictly valid JSON, in Italian only, and you always include a coherent image_prompt for each campaign."
**Model:** gpt-3.5-turbo
**Temperature:** 0.4
**Max Tokens:** 500

---

### Location: Line 134-220
### Function: ChatGPTCampaignGenerator.generate_campaign_for_platform()

#### PROMPT 2: Platform-Specific Campaign Generation (con Immagine Obbligatoria)
```
Crea una campagna pubblicitaria PERSONALIZZATA PER {platform} in italiano.

OBIETTIVO:
- Generare una campagna ADV completa, ottimizzata per {platform}, con testi e brief per l'immagine.
- Produrre contenuti immediatamente utilizzabili come annuncio pubblicitario.

LINEE GUIDA PIATTAFORMA:
{platform_guide}

TONO DELLA CAMPAGNA:
{tone_guide}

DATI DEL CANALE DI RIFERIMENTO:
- Nome canale: {channel_name}
- Topic principale: {channel_topic}
- Descrizione canale: {channel_description}

VINCOLI DI STILE:
- Tutto in italiano corretto e professionale.
- Adatta tono e struttura alla piattaforma {platform} e al tono {tone}.
- Evita promesse irrealistiche, claim non verificabili o contenuti fuorvianti.
- Non citare esplicitamente "{platform}" nel testo rivolto all'utente finale (niente frasi tipo "su {platform} trovi…").

DEVI PRODURRE UNICAMENTE UN OGGETTO JSON VALIDO CON QUESTA STRUTTURA:

{
  "title": "Titolo accattivante della campagna in italiano, adatto a {platform}",
  "description": "Descrizione della campagna in italiano (2-3 frasi) ottimizzata per {platform} e con tono {tone}, focalizzata su beneficio e azione",
  "cta_text": "Testo della Call-To-Action in italiano, specifico e coerente con {platform} e il tono {tone}",
  "suggested_budget": 50.00,
  "keywords": ["keyword1_in_italiano", "keyword2_in_italiano", "keyword3_in_italiano"],
  "target_audience": "Descrizione in italiano del pubblico target per {platform} (es. età, interessi, intenzione)",
  "image_prompt": "Descrizione in italiano dell'immagine ideale per accompagnare l'annuncio su {platform}: soggetto, stile, inquadratura, palette di colori, atmosfera. L'immagine deve essere coerente con titolo, descrizione e CTA, senza testo sovrapposto e senza contenuti sensibili."
}

REQUISITI OBBLIGATORI:
- Rispondi SOLO con JSON valido, senza markdown e senza testo esterno.
- Tutti i campi testuali devono essere ESCLUSIVAMENTE in italiano.
- Usa valori concreti, mai placeholder come 'XXX' o 'prodotto generico'.
```

**Platform Guidelines (Hardcoded):**
- Telegram: "Conciso, può usare emoji in modo moderato, supporta markdown. Max 4000 caratteri."
- Instagram: "Con hashtag rilevanti ed eventuali emoji, frasi brevi. Focus su impatto visivo ed engagement."
- Facebook: "Descrittivo e professionale, incoraggia interazione e condivisione. Supporta link cliccabili."
- Twitter: "Massimo 280 caratteri totali (inclusi spazi). Messaggio diretto, sintetico e orientato all'azione."

**Tone Guidelines (Hardcoded):**
- Professional: "Formale, serio, affidabile. Usa linguaggio professionale e preciso."
- Friendly: "Cordiale, accogliente, conversazionale. Crea connessione senza perdere chiarezza."
#### PROMPT 3: Content Generation Base Prompt (con hint immagine per ADV)
```
Genera contenuto per annunci pubblicitari e contenuti di marketing.

Parametri:
- Topic: {request.topic}
- Tipo di contenuto: {request.content_type.value}
- Tono: {request.tone.value}
- Audience target: {request.target_audience}
- Lingua: {request.language}
- Lunghezza massima: {request.max_length} caratteri

{optional_keywords}
{optional_context}
{optional_cta}

LINEE GUIDA:
- Usa esclusivamente la lingua indicata (default: italiano).
- Linguaggio chiaro, professionale, orientato al beneficio per l'utente e all'azione.
- Evita claim ingannevoli, promesse non realistiche e linguaggio eccessivamente sensazionalistico.

SE IL TIPO DI CONTENUTO È PUBBLICITARIO
(ad esempio: "ad_copy", "social_caption" o "post" usato per annunci):
- Alla fine del testo principale aggiungi una riga separata con il seguente formato esatto:
  IMMAGINE SUGGERITA: descrizione sintetica in italiano dell'immagine ideale per accompagnare questo annuncio (soggetto, stile, inquadratura, atmosfera, colori), senza testo sovrapposto nell'immagine.

OUTPUT:
- Restituisci solo il testo finale pronto per l'uso, senza spiegazioni aggiuntive.
```
Genera contenuto per annunci pubblicitari.

Topic: {request.topic}
Tipo di contenuto: {request.content_type.value}
Tono: {request.tone.value}
Audience: {request.target_audience}
Lingua: {request.language}
Max lunghezza: {request.max_length} caratteri

{optional_keywords}
{optional_context}
{optional_cta}

Generare contenuto persuasivo e accattivante.
```

**Components:**
- Keywords: `\nKeywords da includere: {', '.join(request.keywords)}`
- Context: `\nContesto: {request.context}`
- Call-to-Action: `\nCall to action: {request.call_to_action}`

---

### Location: Line 369-390
### Function: AIContentGenerator._call_ai_api()

#### NOTE: Template-Based Fallback
This function uses template-based generation as fallback instead of direct OpenAI API call.
In production, it should be enhanced to call OpenAI directly:

```python
# Production implementation would be:
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are an expert content creator for advertising campaigns."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.7,
    max_tokens=500
)
content = response.choices[0].message.content.strip()
```

---

## CONTENT TYPES & GENERATION MAPPING

### ai_content.py - ContentType Enum
```python
class ContentType(Enum):
    "Type of content to generate"
    HEADLINE = "headline"
    POST = "post"
    EMAIL_SUBJECT = "email_subject"
    EMAIL_BODY = "email_body"
    AD_COPY = "ad_copy"
    CALL_TO_ACTION = "call_to_action"
    PRODUCT_DESCRIPTION = "product_description"
    SOCIAL_CAPTION = "social_caption"
```

### Tone Types
```python
class ToneType(Enum):
    "Tone of generated content"
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    AGGRESSIVE = "aggressive"
    PLAYFUL = "playful"
    INSPIRATIONAL = "inspirational"
    HUMOROUS = "humorous"
    EDUCATIONAL = "educational"
    URGENT = "urgent"
```

---

## TEMPLATE LIBRARY

### Location: ai_content.py - Line 501-520

#### E-Commerce Templates
```python
ECOMMERCE_TEMPLATES = {
    "flash_sale": "⚡ OFFERTA LAMPO! {product} a {price}€ - Solo oggi!",
    "new_product": "🎉 Novità! Scopri {product} - Il nuovo must-have",
    "seasonal": "🌟 Collezione {season}: {product} a prezzo speciale",
}
```

#### SaaS Templates
```python
SAAS_TEMPLATES = {
    "trial": "🚀 Prova {product} gratis per 14 giorni - Nessuna carta di credito richiesta",
    "feature": "✨ {product} ti permette di {benefit}",
    "success_story": "📈 Aumenta il tuo ROI con {product} - Scopri come!",
}
```

#### Social Media Templates
```python
SOCIAL_TEMPLATES = {
    "engagement": "❓ {question} Condividi la tua opinione nei commenti!",
    # ... more templates
}
```

---

## CAMPAIGN GENERATION FLOW

### Step 1: User Input Collection (bot.py)
- User selects channel
- User selects platform (Telegram, Instagram, Facebook, Twitter)
- User selects tone (Professional, Friendly, Aggressive, Playful)

### Step 2: Prompt Building (chatgpt_integration.py)
- Retrieve channel data (name, topic, description, engagement rate)
- Build platform-specific guidelines
- Build tone-specific guidelines
- Construct JSON prompt with platform/tone context

### Step 3: ChatGPT Call
```python
response = self.client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ],
    temperature=0.7,
    max_tokens=500
)
```

### Step 4: Response Parsing
- Extract JSON from response
- Handle markdown-wrapped JSON: `\`\`\`json {...}\`\`\``
- Validate all fields are in Italian
- Create CampaignContent object

### Step 5: User Display (bot.py)
- Show campaign title, description, CTA, budget
- Display suggestions
- Allow creation/customization/regeneration

---

## REQUEST/RESPONSE STRUCTURES

### ContentRequest (Line 40)
```python
@dataclass
class ContentRequest:
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
```

### GeneratedContent (Line 49)
```python
@dataclass
class GeneratedContent:
    content_type: ContentType
    text: str
    tone: ToneType
    tokens_used: int
    language: str
    variations: List[str] = None
    confidence_score: float = 0.85
```

### CampaignContent (chatgpt_integration.py, Line 12 – Aggiornato)
```python
@dataclass
class CampaignContent:
    title: str
    description: str
    cta_text: str
    suggested_budget: float
    keywords: list[str]
    target_audience: str
    image_prompt: str  # NUOVO: Brief in italiano per l'immagine ADV di accompagnamento
```

**Campo Nuovo - image_prompt:**
- **Tipo:** str (non nullable)
- **Descrizione:** Descrizione dettagliata in italiano dell'immagine ideale per accompagnare la campagna/annuncio
- **Contenuto:** Soggetto, stile visivo, inquadratura, palette di colori, atmosfera
- **Vincoli:** Senza testo sovrapposto, senza contenuti sensibili, coerente con title/description/cta_text
- **Utilizzo:** 
  - Passato a un generatore di immagini AI (DALL-E, Midjourney, Stable Diffusion)
  - Oppure usato come brief per designer umano
  - Loggato per audit e miglioramento

---

## ERROR HANDLING

### JSON Parsing Errors & image_prompt Validation
```python
try:
    campaign_data = json.loads(response_text)
except json.JSONDecodeError:
    # Try extracting from markdown
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0].strip()
        campaign_data = json.loads(json_str)
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0].strip()
        campaign_data = json.loads(json_str)
    else:
        raise

# NUOVO: Validazione obbligatoria di image_prompt
if "image_prompt" not in campaign_data or not campaign_data["image_prompt"]:
    logger.error("Missing or empty image_prompt in campaign data. Response was: %s", response_text)
    raise ValueError("image_prompt è obbligatorio e non può essere vuoto")

if len(campaign_data["image_prompt"]) < 30:
    logger.warning("image_prompt seems too short: %s", campaign_data["image_prompt"])

# Creare CampaignContent con tutti i campi validati
campaign_content = CampaignContent(
    title=campaign_data["title"],
    description=campaign_data["description"],
    cta_text=campaign_data["cta_text"],
    suggested_budget=float(campaign_data["suggested_budget"]),
    keywords=campaign_data["keywords"],
    target_audience=campaign_data["target_audience"],
    image_prompt=campaign_data["image_prompt"]  # Campo obbligatorio
)
```

### API Configuration Errors
```python
if not self.enabled:
    logger.warning("ChatGPT API key not configured")
    return None
```

---

## CONFIGURATION

### Environment Variables (config.py)
- `OPENAI_API_KEY`: ChatGPT API key
- `OPENAI_MODEL`: Model name (default: gpt-3.5-turbo)
- `OPENAI_TEMPERATURE`: Temperature (default: 0.7)
- `OPENAI_MAX_TOKENS`: Max tokens (default: 500)

### Usage in bot.py (Line 3905+)
```python
from .chatgpt_integration import ChatGPTCampaignGenerator

async def aigen_create_from_gpt(update: Update, context: CallbackContext):
    generator = ChatGPTCampaignGenerator(api_key=config.openai_api_key)
    campaign_content = generator.generate_campaign_for_platform(
        channel=channel_obj,
        platform=platform,
        tone=tone
    )
```

---

## PRODUCTION CONSIDERATIONS

### 1. Error Handling
- Implement retry logic for API failures
- Cache generated campaigns to reduce API calls
- Fallback to template-based generation if API unavailable

### 2. Rate Limiting
- Implement user-level rate limits (X campaigns per day)
- Implement API-level rate limits (respect OpenAI quotas)
- Queue generation requests during peak hours

### 3. Content Moderation
- Add content filter before displaying to users
- Flag potentially problematic content
- Implement user feedback loop

### 4. Monitoring & Image Generation Integration
- Log all API calls with timestamp, user_id, prompt, **image_prompt generated**
- Track success/failure rates (including image_prompt validation failures)
- Monitor costs (API calls × cost per token)
- Alert on failures
- **NEW:** Monitor image_prompt quality (length, coherence with title/description)
- **NEW:** Integrate with image generation service (DALL-E, Midjourney, Stable Diffusion) and track results
- **NEW:** User feedback loop on generated image quality from brief

### 5. Optimization
- Store successful campaign templates
- Build user-specific style profiles
- Learn from user selections (A/B testing)
- Implement cost optimization (use gpt-3.5 for simple, gpt-4 for complex)

---

## TESTING

### Unit Tests
```python
def test_campaign_generation():
    generator = ChatGPTCampaignGenerator(api_key="test-key")
    result = generator.generate_campaign(
        channel_name="TestChannel",
        channel_topic="Tech News",
        channel_description="Latest tech updates",
        engagement_rate=0.05
    )
    assert isinstance(result, CampaignContent)
    assert result.title != ""
    assert result.description != ""
    assert result.image_prompt != ""  # NUOVO: Validare sempre image_prompt
    assert len(result.image_prompt) > 20  # Image prompt non deve essere banale

def test_platform_specific():
    result = generator.generate_campaign_for_platform(
        channel=test_channel,
        platform="telegram",
        tone="professional"
    )
    assert "telegram" not in result.description  # Non deve essere nominata nel testo all'utente
    assert len(result.cta_text) < 4000  # Limite Telegram
    assert result.image_prompt != ""  # NUOVO: image_prompt obbligatorio
    assert "telegram" not in result.image_prompt  # Brief non deve mentionare esplicitamente la piattaforma
```

### Integration Tests
```python
async def test_aigen_create_from_gpt():
    # Mock ChatGPT response
    # Create campaign through bot handler
    # Verify campaign stored in database
    # Verify notifications sent
```

---

## IMAGE GENERATION WORKFLOW (NEW)

### Step 1: Campaign Generation with image_prompt
- ChatGPT generates CampaignContent including detailed image_prompt in Italian
- image_prompt validated (not empty, > 30 chars, coherent with copy)

### Step 2: Image Generation Service Integration
```python
# Example: Using DALL-E for image generation
from openai import OpenAI

async def generate_campaign_image(campaign_content: CampaignContent) -> str:
    """Generate image from image_prompt using DALL-E."""
    client = OpenAI(api_key=config.openai_api_key)
    
    response = client.images.generate(
        model="dall-e-3",
        prompt=campaign_content.image_prompt,  # Use the Italian brief
        size="1024x1024",
        quality="standard",
        n=1
    )
    
    image_url = response.data[0].url
    return image_url
```

### Step 3: Display in Bot UI
```python
# Show campaign + generated image
caption = f"""
📋 **{campaign_content.title}**

{campaign_content.description}

📞 {campaign_content.cta_text}

💰 Budget suggerito: €{campaign_content.suggested_budget}
👥 Target: {campaign_content.target_audience}
"""

# Send image + caption to Telegram user
await context.bot.send_photo(
    chat_id=update.effective_chat.id,
    photo=image_url,
    caption=caption,
    parse_mode="HTML"
)
```

### Step 4: Store Campaign with Image Reference
```python
# Database: Add image_url and image_prompt to Campaign model
campaign = Campaign(
    channel_id=channel_id,
    title=campaign_content.title,
    description=campaign_content.description,
    cta_text=campaign_content.cta_text,
    suggested_budget=campaign_content.suggested_budget,
    keywords=",".join(campaign_content.keywords),
    target_audience=campaign_content.target_audience,
    image_prompt=campaign_content.image_prompt,  # Store for audit/regeneration
    image_url=image_url,  # Store generated image URL
    platform="telegram"
)
session.add(campaign)
session.commit()
```

### Step 5: Image Caching & Regeneration
```python
# Cache successful images by image_prompt hash
import hashlib

def get_image_cache_key(image_prompt: str) -> str:
    return f"img_{hashlib.md5(image_prompt.encode()).hexdigest()}"

async def get_or_generate_image(campaign_content: CampaignContent) -> str:
    cache_key = get_image_cache_key(campaign_content.image_prompt)
    
    # Check cache
    cached_url = cache.get(cache_key)
    if cached_url:
        return cached_url
    
    # Generate if not cached
    image_url = await generate_campaign_image(campaign_content)
    cache.set(cache_key, image_url, ttl=7*24*3600)  # Cache 7 days
    
    return image_url
```

---

## VALIDATION CHECKLIST

### Per ogni campagna generata, verificare:

**JSON Structure Validation:**
- [ ] response è JSON valido
- [ ] title non vuoto (min 3 chars)
- [ ] description non vuoto (min 20 chars)
- [ ] cta_text non vuoto (min 5 chars)
- [ ] suggested_budget è numero > 0
- [ ] keywords è array non vuoto (min 1, max 5 items)
- [ ] target_audience non vuoto (min 15 chars)
- [ ] image_prompt non vuoto e >= 30 chars ✅ **OBBLIGATORIO**

**Language Validation:**
- [ ] title è in italiano
- [ ] description è in italiano
- [ ] cta_text è in italiano
- [ ] keywords sono in italiano
- [ ] target_audience è in italiano
- [ ] image_prompt è in italiano ✅ **OBBLIGATORIO**
- [ ] Nessun testo in altre lingue

**Content Quality:**
- [ ] Nessuna promessa irrealistica in description
- [ ] CTA è chiaro e orientato all'azione
- [ ] image_prompt descrive coerentemente il visual della campagna
- [ ] image_prompt NON contiene testo sovrapposto
- [ ] image_prompt è libero da contenuti sensibili

**Platform Compliance (se platform_specific):**
- [ ] Telegram: cta_text < 4000 chars
- [ ] Instagram: keywords hanno hashtag rilevanti
- [ ] Facebook: description >= 50 chars (descrittivo)
- [ ] Twitter: (se applicabile) cta_text < 280 chars
- [ ] image_prompt NON nomina esplicitamente la piattaforma

**Image Generation Readiness:**
- [ ] image_prompt è adatto per DALL-E/Midjourney/Stable Diffusion
- [ ] image_prompt NON è troppo vago (es. "qualcosa di carino")
- [ ] image_prompt include stile e atmosfera (es. "stile minimale, colori caldi, atmosfera professional")
- [ ] image_prompt include dimensioni/inquadratura (es. "portrait mode", "wide angle")

---

