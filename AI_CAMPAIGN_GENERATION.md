# Feature: Genera Campagna con AI

## 📋 Descrizione
Nuova feature che consente agli utenti **premium** di generare campagne personalizzate analizzando il loro bot/canale utilizzando l'intelligenza artificiale.

## ✨ Funzionalità Principali

### 1. **Controllo Accesso Premium**
- Solo gli utenti con `subscription_type != "gratis"` possono accedere
- Gli utenti gratis ricevono un messaggio con opzioni di upgrade
- Piani disponibili: Premium (€9.99/mese), Pro (€29.99/mese)

### 2. **Analisi del Canale**
Il bot analizza automaticamente:
- 📊 Numero di follower
- 💬 Engagement rate (likes, comments, shares)
- 📈 Trend di crescita
- 🎯 Temi principali dei contenuti
- ⏰ Orari migliori di posting
- 👥 Stima dati demografici audience
- 🏆 Analisi competitor

### 3. **Generazione Campagne Personalizzate**
Sulla base dell'analisi, genera 5 suggerimenti di campagne:

#### a. **🚀 Accelerazione Crescita**
- Perfetto per: Canali con pochi follower (<10k)
- Focus: Viral content, trend, challenge
- Budget consigliato: €50-100
- ROI atteso: 3.5x

#### b. **💬 Boost Engagement**
- Perfetto per: Canali consolidati
- Focus: Domande, sondaggi, user-generated content
- Budget consigliato: €100-150
- ROI atteso: 2.8x

#### c. **💰 Monetizzazione Premium**
- Perfetto per: Canali con alto engagement (>5%)
- Focus: Sponsored content, affiliate, products
- Budget consigliato: €200+
- ROI atteso: 5.2x

#### d. **⚡ Viral Booster**
- Perfetto per: Rapida crescita
- Focus: Trending topics, meme, shock value
- Budget consigliato: €80-150
- ROI atteso: 4.1x

#### e. **👑 Premium Brand Campaign**
- Perfetto per: Posizionamento luxury
- Focus: Exclusive content, brand storytelling
- Budget consigliato: €250+
- ROI atteso: 3.8x

#### f. **❤️ Loyalty & Retention**
- Perfetto per: Mantenimento community
- Focus: Exclusive content, behind-the-scenes
- Budget consigliato: €50-120
- ROI atteso: 4.5x

#### g. **🎯 Brand Awareness**
- Perfetto per: Nuovi utenti
- Focus: Educational, informational
- Budget consigliato: €40-100
- ROI atteso: 2.5x

## 🔧 Modifiche Tecniche

### File Modificati:

#### 1. **`models.py`**
```python
class User(Base):
    # ... altri campi ...
    subscription_type: Mapped[str] = mapped_column(String(50), default="gratis")
    # "gratis" o "premium" o "pro"
```

#### 2. **`bot.py`**
- Aggiunto bottone "✨ Genera Campagna con AI" nel menu principale
- Aggiunti 3 nuovi stati della conversation:
  - `AIGEN_SELECT_CHANNEL`: Selezione canale
  - `AIGEN_ANALYZING`: Analisi in corso
  - `AIGEN_REVIEW_CAMPAIGNS`: Revisione suggerimenti
- Implementati 5 nuovi handler:
  - `aigen_start()`: Entry point, check premium
  - `aigen_channel_selected()`: Seleziona canale
  - `aigen_show_campaign_suggestion()`: Mostra suggerimento
  - `aigen_next_suggestion()`: Passa al prossimo
  - `aigen_create_campaign()`: Crea la campagna

#### 3. **`services.py`**
Aggiunte funzioni helper:
```python
def is_premium_user(session: Session, user: User) -> bool
def upgrade_user_to_premium(session: Session, user: User, plan_type: str)
```

#### 4. **`campaign_analyzer.py`** (NUOVO)
Nuovo modulo che implementa:
- `CampaignAnalyzer`: Classe principale per l'analisi
- `ChannelAnalysis`: Dataclass con risultati analisi
- `CampaignSuggestion`: Dataclass con suggerimenti campagne
- Metodi per calcolare engagement, trends, recommendations

## 🔄 Flusso di Utilizzo

```
1. Utente clicca "✨ Genera Campagna con AI"
    ↓
2. Bot verifica subscription_type
    ↓
3a. Se "gratis" → Mostra messaggio upgrade ❌
    ↓
3b. Se "premium"/"pro" → Continua ✅
    ↓
4. Bot chiede: "Seleziona un canale"
    ↓
5. Bot analizza il canale (dati, metriche, engagement)
    ↓
6. Bot genera 5 suggerimenti di campagne personalizzate
    ↓
7. Utente naviga tra i suggerimenti (➡️ ⬅️)
    ↓
8. Utente clicca "Crea questa campagna"
    ↓
9. Campagna salvata nel database
    ↓
10. Mostra opzioni next steps:
    - 🤖 Genera Contenuti
    - 🎨 Personalizza
    - ➡️ Prossima campagna
    - ◀️ Torna al menu
```

## 📊 Struttura Dati

### ChannelAnalysis
```python
@dataclass
class ChannelAnalysis:
    channel_handle: str
    channel_title: Optional[str]
    topic: Optional[str]
    total_followers: int
    engagement_rate: float
    avg_post_engagement: float
    posting_frequency: str
    best_posting_time: str
    audience_demographics: Dict
    content_themes: List[str]
    competitor_analysis: Dict
    growth_trends: Dict
    recommendations: List[str]
```

### CampaignSuggestion
```python
@dataclass
class CampaignSuggestion:
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
```

## 🎯 Callback Patterns

| Pattern | Handler | Descrizione |
|---------|---------|-------------|
| `^aigen:start$` | `aigen_start()` | Initia il flusso |
| `^aigen:channel:\d+$` | `aigen_channel_selected()` | Canale selezionato |
| `^aigen:next_suggestion$` | `aigen_next_suggestion()` | Prossima campagna |
| `^aigen:prev_suggestion$` | `aigen_prev_suggestion()` | Campagna precedente |
| `^aigen:create:\d+$` | `aigen_create_campaign()` | Crea campagna |

## 💡 Prossimi Passi (Futuri)

1. **Integrazione OpenAI/Claude**: Generare contenuti reali con AI
2. **Analytics Avanzati**: Leggere da Telegram API statistiche reali
3. **Campagne Ricorrenti**: Permettere scheduling automatico
4. **A/B Testing**: Testare automaticamente variazioni di contenuti
5. **Reporting**: Statistiche dettagliate per ogni campagna
6. **Payment Integration**: Pagamento automatico con Stripe/PayPal

## 🧪 Testing

Per testare la feature:

```python
# 1. Crea un utente premium
user.subscription_type = "premium"

# 2. Clicca il bottone "✨ Genera Campagna con AI"
# Callback: aigen:start

# 3. Seleziona un canale
# Callback: aigen:channel:<channel_id>

# 4. Naviga tra i suggerimenti
# Callback: aigen:next_suggestion o aigen:prev_suggestion

# 5. Crea una campagna
# Callback: aigen:create:<index>
```

## 📝 Note Importanti

- Il bot non legge davvero da Telegram API (richiede token admin)
- Le metriche sono simulate per demo purposes
- In produzione, integrare con `python-telegram-bot` per get statistics
- Usare vere AI API (OpenAI, Anthropic) per generazione contenuti
- Salvare la cronologia delle campagne per analytics
