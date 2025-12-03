# AI Campaign Generation - Architecture Diagrams

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     TELEGRAM USER                            │
└────────────┬────────────────────────────────────────────────┘
             │
             │ /start or ✨ Genera Campagna con AI
             ↓
┌─────────────────────────────────────────────────────────────┐
│                    TELEGRAM BOT API                          │
│                    (python-telegram-bot)                     │
└────────────┬────────────────────────────────────────────────┘
             │
             │ CallbackQuery(aigen:*)
             ↓
┌─────────────────────────────────────────────────────────────┐
│              BOT.PY - MESSAGE HANDLERS                        │
│                                                              │
│  ├─ aigen_start()                                           │
│  ├─ aigen_channel_selected()                               │
│  ├─ aigen_show_campaign_suggestion()                       │
│  ├─ aigen_next_suggestion()                                │
│  ├─ aigen_prev_suggestion()                                │
│  └─ aigen_create_campaign()                                │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┴────────┐
    ↓                 ↓
┌─────────┐    ┌──────────────────────────┐
│ MODELS  │    │ CAMPAIGN_ANALYZER        │
├─────────┤    ├──────────────────────────┤
│ User    │    │ - analyze_channel()      │
│Channel  │    │ - generate_suggestions() │
│Campaign │    │ - _calculate_metrics()   │
│Metrics  │    │ - _create_*_campaign()   │
└────┬────┘    └────────┬─────────────────┘
     │                  │
     ↓                  ↓
┌──────────────────────────────────────┐
│    DATABASE (SQLite/PostgreSQL)      │
│                                      │
│  Tables:                             │
│  ├─ users (+ subscription_type)      │
│  ├─ channels                         │
│  ├─ campaigns                        │
│  ├─ ad_metrics                       │
│  └─ transactions                     │
└──────────────────────────────────────┘
```

## 🔀 Data Flow Diagram

```
User Action: Click "✨ Genera Campagna con AI"
│
├─→ [aigen_start()]
│   ├─→ Get User from Telegram ID
│   ├─→ Check user.subscription_type
│   │
│   ├─ If "gratis" → Show Upgrade Message → END
│   │
│   └─ If "premium"/"pro"
│       └─→ Query channels for user
│           └─→ Show Channel Selection Buttons
│               └─→ AIGEN_SELECT_CHANNEL state
│
└─→ User Selects Channel: aigen:channel:<id>
    │
    ├─→ [aigen_channel_selected()]
    │   ├─→ Show "Analyzing..." message
    │   ├─→ Query Channel data
    │   ├─→ Query AdvertisementMetrics (limit 50)
    │   │
    │   ├─→ Call CampaignAnalyzer.analyze_channel()
    │   │   ├─→ Calculate engagement_rate
    │   │   ├─→ Calculate avg_post_engagement
    │   │   ├─→ Analyze posting_frequency
    │   │   ├─→ Find best_posting_time
    │   │   ├─→ Extract content_themes
    │   │   └─→ Return ChannelAnalysis
    │   │
    │   ├─→ Call analyzer.generate_campaign_suggestions()
    │   │   ├─→ Evaluate engagement rate
    │   │   ├─→ Evaluate follower count
    │   │   ├─→ Create 5-7 CampaignSuggestion objects
    │   │   └─→ Return List[CampaignSuggestion]
    │   │
    │   └─→ Store in context:
    │       ├─ aigen_analysis (ChannelAnalysis)
    │       ├─ aigen_suggestions (List[CampaignSuggestion])
    │       ├─ aigen_suggestion_index (0)
    │       └─→ AIGEN_REVIEW_CAMPAIGNS state
    │
    └─→ Show First Suggestion: [aigen_show_campaign_suggestion()]
        │
        ├─→ Display Campaign Details
        ├─→ Show Action Buttons
        │
        ├─→ User Options:
        │   ├─ Next: aigen:next_suggestion → [aigen_next_suggestion()]
        │   ├─ Prev: aigen:prev_suggestion → [aigen_prev_suggestion()]
        │   └─ Create: aigen:create:<idx> → [aigen_create_campaign()]
        │
        └─→ If Create Selected:
            ├─→ [aigen_create_campaign()]
            ├─→ INSERT Campaign into DB
            ├─→ Show Success Message
            └─→ Show Next Steps Options
```

## 📊 Class Diagram

```
CampaignAnalyzer
├─ Methods:
│  ├─ analyze_channel(handle, title, topic, followers, metrics, posts)
│  │  └─ Returns: ChannelAnalysis
│  │
│  ├─ generate_campaign_suggestions(analysis, goals, budget)
│  │  └─ Returns: List[CampaignSuggestion]
│  │
│  ├─ _create_growth_campaign(analysis, budget)
│  ├─ _create_engagement_campaign(analysis, budget)
│  ├─ _create_monetization_campaign(analysis, budget)
│  ├─ _create_viral_campaign(analysis, budget)
│  ├─ _create_premium_campaign(analysis, budget)
│  ├─ _create_loyalty_campaign(analysis, budget)
│  ├─ _create_awareness_campaign(analysis, budget)
│  │
│  └─ Private Helpers:
│     ├─ _calculate_engagement_rate(metrics, followers)
│     ├─ _calculate_avg_engagement(posts_data)
│     ├─ _analyze_posting_frequency(posts_data)
│     ├─ _find_best_posting_time(posts_data)
│     ├─ _extract_content_themes(posts_data)
│     ├─ _estimate_demographics(followers)
│     ├─ _analyze_competitors(topic)
│     ├─ _analyze_growth_trends(posts_data)
│     └─ _generate_recommendations(followers, engagement, themes)
│
└─ Attributes:
   ├─ campaign_types: List[str]
   └─ (no instance state beyond methods)


ChannelAnalysis
├─ Fields:
│  ├─ channel_handle: str
│  ├─ channel_title: Optional[str]
│  ├─ topic: Optional[str]
│  ├─ total_followers: int
│  ├─ engagement_rate: float
│  ├─ avg_post_engagement: float
│  ├─ posting_frequency: str
│  ├─ best_posting_time: str
│  ├─ audience_demographics: Dict
│  ├─ content_themes: List[str]
│  ├─ competitor_analysis: Dict
│  ├─ growth_trends: Dict
│  └─ recommendations: List[str]
│
└─ Type: @dataclass


CampaignSuggestion
├─ Fields:
│  ├─ campaign_type: str
│  ├─ title: str
│  ├─ description: str
│  ├─ recommended_budget: float
│  ├─ estimated_reach: int
│  ├─ estimated_engagement: float
│  ├─ content_focus: str
│  ├─ targeting: Dict
│  ├─ timing: Dict
│  ├─ expected_roi: float
│  └─ reasoning: str
│
└─ Type: @dataclass


User (Model)
├─ Fields:
│  ├─ id: int (PK)
│  ├─ telegram_id: int (UK)
│  ├─ username: str
│  ├─ first_name: str
│  ├─ language_code: str
│  ├─ subscription_type: str  ← NEW! ("gratis"/"premium"/"pro")
│  ├─ created_at: datetime
│  │
│  └─ Relationships:
│     ├─ channels: List[Channel]
│     └─ templates: List[BroadcastTemplate]
│
└─ Type: SQLAlchemy ORM Model


Campaign (Model)
├─ Fields:
│  ├─ id: int (PK)
│  ├─ channel_id: int (FK)
│  ├─ name: str
│  ├─ budget: float
│  ├─ call_to_action: str
│  ├─ created_at: datetime
│  │
│  └─ Relationships:
│     └─ channel: Channel
│
└─ Type: SQLAlchemy ORM Model
```

## 🎯 State Machine

```
START
  │
  ├─→ aigen:start (callback)
  │   │
  │   ├─→ Check Subscription
  │   │   ├─ If GRATIS → Show Upgrade → END
  │   │   └─ If PREMIUM/PRO → Continue
  │   │
  │   └─→ State: AIGEN_SELECT_CHANNEL
  │       Show Channel List
  │
  └─→ User Selects Channel: aigen:channel:<id>
      │
      ├─→ aigen_channel_selected()
      │   Analyze Channel
      │
      └─→ State: AIGEN_REVIEW_CAMPAIGNS
          Show Suggestion #1
          
          ├─→ User: aigen:next_suggestion
          │   └─→ State: AIGEN_REVIEW_CAMPAIGNS (index++)
          │       Show Next Suggestion
          │
          ├─→ User: aigen:prev_suggestion
          │   └─→ State: AIGEN_REVIEW_CAMPAIGNS (index--)
          │       Show Previous Suggestion
          │
          └─→ User: aigen:create:<idx>
              └─→ aigen_create_campaign()
                  Save to DB
                  Show Success
                  
                  ├─→ User: aigen:next_suggestion
                  │   Repeat suggestions loop
                  │
                  ├─→ User: aigen:generate_content:<id>
                  │   Generate AI Content
                  │
                  ├─→ User: aigen:edit:<id>
                  │   Edit Campaign
                  │
                  └─→ User: menu:main
                      → END

```

## 📈 Sequence Diagram

```
User          Telegram Bot      bot.py          Models       Database
  │                │              │                │             │
  ├──Click Button──→│              │                │             │
  │                 │─aigen:start→│                │             │
  │                 │             │                │             │
  │                 │             ├─Get User───────→│─────────────→│
  │                 │             │◄─User object────│◄─────────────│
  │                 │             │                │             │
  │                 │             ├─Is Premium?────→ (check subscription_type)
  │                 │             │                │             │
  │                 │             ├─Get Channels───→│─────────────→│
  │                 │             │◄─Channel list───│◄─────────────│
  │                 │             │                │             │
  │                 ←─Show Buttons─│                │             │
  │◄────────────────│                │             │
  │                 │              │                │             │
  ├──Select Channel→│              │                │             │
  │                 │─aigen:channel:5─→│             │             │
  │                 │             │                │             │
  │                 ├─"Analyzing..."→│             │             │
  │                 │◄─────────────────│             │             │
  │                 │             │                │             │
  │◄──Analyzing msg─│             │                │             │
  │                 │             ├─Get Channel────→│─────────────→│
  │                 │             │◄─Channel data───│◄─────────────│
  │                 │             │                │             │
  │                 │             ├─Get Metrics────→│─────────────→│
  │                 │             │◄─Metrics (50)──│◄─────────────│
  │                 │             │                │             │
  │                 │             ├─Analyze()     │             │
  │                 │             │├─calc engagement│             │
  │                 │             │├─calc trends   │             │
  │                 │             │├─find themes   │             │
  │                 │             │└─→ChannelAnalysis            │
  │                 │             │                │             │
  │                 │             ├─Generate Suggestions()        │
  │                 │             │├─→ CampaignSuggestion[] │    │
  │                 │             │                │             │
  │                 │             ├─Store in context          │
  │                 │             │                │             │
  │                 ←─Campaign #1──│                │             │
  │◄────────────────│              │                │             │
  │                 │              │                │             │
  ├──Next/Create────→│             │                │             │
  │                 │─aigen:create:0─→│             │             │
  │                 │             │                │             │
  │                 │             ├─INSERT Campaign─→│────────────→│
  │                 │             │                │       │       │
  │                 │             │                │◄──Confirm────│
  │                 │             │                │       │       │
  │                 ←─Success msg──│                │       │       │
  │◄────────────────│              │                │       │       │
  │                 │              │                │       │       │

```

## 🔑 Key Metrics Calculations

```python
# Engagement Rate Formula
engagement_rate = (total_likes + total_comments) / (followers * 10)

# Average Post Engagement
avg_engagement = sum(likes + comments for all posts) / num_posts

# Posting Frequency Categories
- Very High:  >= 20 posts     → 5+ per day
- High:       10-19 posts     → 2-4 per day  
- Medium:     5-9 posts       → 1-2 per day
- Low:        < 5 posts       → < 1 per day

# ROI Estimation
roi = (estimated_engagement / budget) * conversion_rate_factor

# Reach Estimation
reach = budget * 1000  # Conservative: 1000 impressions per euro

# Engagement Estimation
engagement = budget * 50   # Conservative: 50 interactions per euro
```

---

**Last Updated**: December 3, 2025
**Version**: 1.0
**Status**: Production Ready
