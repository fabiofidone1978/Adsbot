# Developer Guide - AI Campaign Generation

## 🏗️ Architettura

```
User (Telegram)
    ↓
bot.py (aigen_* handlers)
    ↓
campaign_analyzer.py (CampaignAnalyzer)
    ↓
models.py (User, Channel, Campaign)
    ↓
database (SQLite/PostgreSQL)
```

## 📦 Moduli Principali

### 1. `campaign_analyzer.py`
**Responsabilità**: Analizzare dati del canale e generare suggerimenti

**Classi Principali**:
- `CampaignAnalyzer`: Orchestrator principale
- `ChannelAnalysis`: DTO con risultati analisi
- `CampaignSuggestion`: DTO con suggerimenti campagne

**Metodi Pubblici**:
```python
def analyze_channel(
    channel_handle: str,
    channel_title: Optional[str] = None,
    channel_topic: Optional[str] = None,
    followers: int = 0,
    recent_metrics: Dict = None,
    posts_data: List[Dict] = None,
) -> ChannelAnalysis
```

```python
def generate_campaign_suggestions(
    channel_analysis: ChannelAnalysis,
    goals: Optional[Dict] = None,
    budget: Optional[float] = None,
) -> List[CampaignSuggestion]
```

### 2. `bot.py` (AI Campaign Handlers)
**Responsabilità**: Gestire la conversazione con l'utente

**Handler Principali**:
- `aigen_start()`: Entry point, check premium
- `aigen_channel_selected()`: Analisza canale
- `aigen_show_campaign_suggestion()`: Mostra suggerimento
- `aigen_next_suggestion()`: Naviga avanti
- `aigen_prev_suggestion()`: Naviga indietro
- `aigen_create_campaign()`: Crea campagna nel DB

### 3. `models.py`
**Nuovi Campi**:
```python
class User(Base):
    subscription_type: str  # "gratis", "premium", "pro"
```

**Modelli Utilizzati**:
- `User`: Memorizza subscription_type
- `Channel`: Dati del canale (handle, title, topic)
- `Campaign`: Campagne create (name, budget, cta)

### 4. `services.py`
**Helper Functions**:
```python
def is_premium_user(session: Session, user: User) -> bool
def upgrade_user_to_premium(session: Session, user: User, plan_type: str) -> User
```

## 🔄 Flusso di Esecuzione

```
1. User preme "✨ Genera Campagna con AI"
   └─> callback_data="aigen:start"
   
2. bot.py riceve il callback
   └─> aigen_start() handler
   
3. Check subscription
   ├─> Se "gratis" → Mostra messaggio upgrade
   └─> Se "premium"/"pro" → Continua
   
4. Recupera lista canali dell'utente
   └─> Query: Channel.filter_by(user_id=user.id)
   
5. Mostra bottoni per selezionare canale
   └─> callback_data="aigen:channel:<channel_id>"
   
6. User seleziona canale
   └─> aigen_channel_selected() handler
   
7. Recupera dati del canale
   ├─> Channel info (handle, title, topic)
   └─> AdvertisementMetrics (ultimi 50)
   
8. Crea CampaignAnalyzer e chiama analyze_channel()
   └─> Restituisce ChannelAnalysis
   
9. Chiama generate_campaign_suggestions()
   └─> Restituisce List[CampaignSuggestion]
   
10. Mostra primo suggerimento
    └─> aigen_show_campaign_suggestion()
    
11. User naviga tra suggerimenti
    ├─> Callback: "aigen:next_suggestion"
    └─> Callback: "aigen:prev_suggestion"
    
12. User seleziona "Crea questa campagna"
    └─> aigen_create_campaign()
    
13. Salva nel DB
    └─> INSERT INTO campaigns (...)
    
14. Mostra messaggio di successo
    └─> Opzioni next steps
```

## 🔌 Integrazioni Necessarie

### 1. Telegram Bot API (Opzionale ma Consigliato)
Per ottenere statistiche REALI invece di simulate:

```python
from telegram import Bot

async def get_channel_stats(bot: Bot, channel_id: int):
    """Get real channel statistics from Telegram API"""
    try:
        chat = await bot.get_chat(channel_id)
        return {
            "members_count": chat.get_member_count(),
            # Nota: Telegram non espone pubblicamente:
            # - Engagement rate
            # - Post analytics
            # - Audience demographics
        }
    except Exception as e:
        logger.error(f"Error fetching channel stats: {e}")
        return None
```

### 2. AI APIs per Content Generation
Per generare contenuti REALI:

**OpenAI/Claude**:
```python
import openai

async def generate_campaign_content(suggestion: CampaignSuggestion):
    """Generate campaign content using OpenAI"""
    prompt = f"""
    Genera un post per una campagna di {suggestion.campaign_type}
    Focus: {suggestion.content_focus}
    Tono: professionale
    Max 280 caratteri
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content
```

### 3. Analytics Dashboard (Futuro)
```python
# In webapp/dashboard.py
@app.get("/api/campaigns/<campaign_id>/analytics")
def get_campaign_analytics(campaign_id: int):
    """Get real-time campaign analytics"""
    return {
        "reach": 5000,
        "engagement": 250,
        "roi": 3.5,
        "ctr": 0.05,
    }
```

## 🧪 Testing

### Unit Tests
```bash
# Test campaign analyzer
pytest tests/test_campaign_analyzer.py

# Test subscription checking
pytest tests/test_services.py::test_is_premium_user

# Test handlers
pytest tests/test_bot_handlers.py::test_aigen_handlers
```

### Integration Tests
```bash
# Test full flow
pytest tests/test_integration.py::test_ai_campaign_flow

# Test with mock DB
pytest tests/test_integration.py::test_aigen_with_db
```

### Manual Testing
```bash
# Esegui il test script
python test_ai_campaigns.py
```

## 📊 Database Schema Changes

### Migration (Alembic)
Se usi Alembic:

```bash
# Genera migration
alembic revision --autogenerate -m "Add subscription_type to User"

# Applica
alembic upgrade head
```

### Schema SQL
```sql
-- Se non usi ORM migrations
ALTER TABLE users ADD COLUMN subscription_type VARCHAR(50) DEFAULT 'gratis';
CREATE INDEX idx_users_subscription ON users(subscription_type);
```

## 🔐 Sicurezza

### Best Practices Implementate
1. ✅ Check subscription_type prima di accedere alla feature
2. ✅ Validazione input (channel_id, user_id)
3. ✅ Logging di tutte le azioni
4. ✅ Error handling graceful
5. ✅ SQL injection prevention (ORM)

### Da Implementare
1. Rate limiting per analysis
2. Audit logging per tracciare usi premium
3. Encryption di dati sensibili
4. Validation di budget limits

## 🚀 Performance

### Ottimizzazioni Attuali
- Query con limit 50 metriche (non tutte)
- In-memory campaign generation
- Lazy loading relationships

### Da Implementare
- Caching di analysis (Redis)
- Async campaign analysis
- Background jobs per heavy computations
- Pagination per large datasets

## 📝 Logging

### Configurazione
```python
import logging

logger = logging.getLogger(__name__)

# Log esempi
logger.info(f"Analyzing channel: {channel_handle}")
logger.warning(f"No metrics found for channel: {channel_id}")
logger.error(f"Error creating campaign: {str(e)}")
```

### Levels
- `INFO`: Flussi normali, azioni utente
- `WARNING`: Anomalie non critiche
- `ERROR`: Errori che impediscono azione
- `DEBUG`: Dettagli per troubleshooting

## 🎯 Roadmap Futuro

### Phase 2: Content Generation
- [ ] Integrazione OpenAI/Claude
- [ ] Template di contenuti AI
- [ ] A/B testing automatico
- [ ] Multi-language support

### Phase 3: Automazione
- [ ] Scheduling automatico campagne
- [ ] Auto-posting su Telegram
- [ ] Automazione pagamenti
- [ ] Notification system

### Phase 4: Analytics
- [ ] Real-time dashboard
- [ ] Export reports (PDF, Excel)
- [ ] Predictive analytics
- [ ] ROI tracking

### Phase 5: Enterprise
- [ ] Team collaboration
- [ ] White-label options
- [ ] API per third-party
- [ ] Advanced targeting

## 🐛 Debugging

### Common Issues

**1. "Canale non trovato"**
```python
# Check
session.query(Channel).filter_by(id=channel_id, user_id=user.id).first()
# Se None, il canale non esiste o non appartiene all'utente
```

**2. "Errore durante l'analisi"**
```python
# Controlla logs
logger.error(f"Error analyzing channel: {e}")
# Verifica metrica disponibilità
```

**3. "Messaggio di upgrade non mostra"**
```python
# Verifica subscription_type
print(f"User subscription: {user.subscription_type}")
# Deve essere "gratis" per mostrare upgrade message
```

## 📚 Documentazione Aggiuntiva

- `AI_CAMPAIGN_GENERATION.md`: Specifiche tecniche
- `USER_GUIDE_AI_CAMPAIGNS.md`: Guida utente
- `README.md`: Documentazione generale

## 💬 Support

Per domande o issues:
1. Controlla la documentazione
2. Esegui il test script
3. Controlla i logs
4. Apri un issue su GitHub
