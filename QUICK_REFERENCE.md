# Quick Reference - Genera Campagna con AI

## 🎯 For Users

### How to Access
```
/start 
  ↓
Menu → "✨ Genera Campagna con AI"
```

### What You Get
- Analysis of your channel
- 7 personalized campaign suggestions
- 1-click campaign creation
- Budget recommendations
- ROI estimates

### Requirements
- Profile: **Premium** (€9.99/mth) or **Pro** (€29.99/mth)
- Minimum: 1 registered channel

### Quick Steps
1. Click button
2. Select channel
3. Browse suggestions (➡️ ⬅️)
4. Create campaign ✅

---

## 🔧 For Developers

### Files Modified
```
adsbot/models.py              # + subscription_type to User
adsbot/bot.py                 # + 5 handlers, 1 menu button, 1 conversation
adsbot/services.py            # + 2 helper functions
```

### Files Created
```
adsbot/campaign_analyzer.py   # Main logic (350+ lines)
```

### Documentation
```
AI_CAMPAIGN_GENERATION.md              # Technical spec
DEVELOPER_GUIDE_AI_CAMPAIGNS.md        # Dev guide
ARCHITECTURE_AI_CAMPAIGNS.md           # Diagrams
USER_GUIDE_AI_CAMPAIGNS.md             # User manual
CHANGELOG_AI_CAMPAIGNS.md              # What changed
IMPLEMENTATION_SUMMARY_AI_CAMPAIGNS.md # This summary
```

### Database Change
```sql
ALTER TABLE users ADD COLUMN subscription_type VARCHAR(50) DEFAULT 'gratis';
```

### Key Classes
```python
# Main orchestrator
from adsbot.campaign_analyzer import CampaignAnalyzer

# Analysis result
from adsbot.campaign_analyzer import ChannelAnalysis

# Campaign suggestion
from adsbot.campaign_analyzer import CampaignSuggestion

# Helper functions
from adsbot.services import is_premium_user, upgrade_user_to_premium
```

### Quick Integration Example
```python
from adsbot.campaign_analyzer import CampaignAnalyzer

analyzer = CampaignAnalyzer()

# Analyze channel
analysis = analyzer.analyze_channel(
    channel_handle="@mychannel",
    channel_title="My Channel",
    channel_topic="Tech",
    followers=5000,
    recent_metrics={"total_likes": 1500},
    posts_data=[...]
)

# Generate suggestions
suggestions = analyzer.generate_campaign_suggestions(analysis)

# Use suggestions
for suggestion in suggestions:
    print(f"{suggestion.title}: {suggestion.description}")
    print(f"Budget: €{suggestion.recommended_budget}")
    print(f"ROI: {suggestion.expected_roi}x")
```

### Handlers
```python
aigen_start()                      # Entry point
aigen_channel_selected()           # Analyze channel
aigen_show_campaign_suggestion()   # Display campaign
aigen_next_suggestion()            # Next campaign
aigen_prev_suggestion()            # Previous campaign
aigen_create_campaign()            # Save campaign
```

### Callback Patterns
```
aigen:start
aigen:channel:<id>
aigen:next_suggestion
aigen:prev_suggestion
aigen:create:<index>
```

### States
```python
AIGEN_SELECT_CHANNEL = 25      # User selecting channel
AIGEN_ANALYZING = 26           # Bot analyzing
AIGEN_REVIEW_CAMPAIGNS = 27    # User reviewing suggestions
```

---

## 📊 Campaign Types

| Type | Icon | For | Budget | ROI |
|------|------|-----|--------|-----|
| Growth | 🚀 | Small channels | €50-100 | 3.5x |
| Engagement | 💬 | Established | €100-150 | 2.8x |
| Monetization | 💰 | High engagement | €200+ | 5.2x |
| Viral | ⚡ | Rapid growth | €80-150 | 4.1x |
| Brand | 👑 | Luxury | €250+ | 3.8x |
| Loyalty | ❤️ | Retention | €50-120 | 4.5x |
| Awareness | 🎯 | New audience | €40-100 | 2.5x |

---

## 🔑 Key Metrics

```python
# Engagement rate
engagement_rate = (likes + comments) / (followers * 10)

# Average post engagement
avg_engagement = total_engagement / num_posts

# Reach estimation
reach = budget × 1000

# Engagement estimation  
engagement = budget × 50
```

---

## 🧪 Testing

### Unit Test
```bash
python test_ai_campaigns.py
```

### Manual Test
```python
from adsbot.campaign_analyzer import CampaignAnalyzer

analyzer = CampaignAnalyzer()
analysis = analyzer.analyze_channel(
    channel_handle="@test",
    followers=5000,
    recent_metrics={"total_likes": 1500, "total_comments": 300},
    posts_data=[
        {"likes": 150, "comments": 30, "hour": 19},
        {"likes": 120, "comments": 25, "hour": 20},
    ]
)

suggestions = analyzer.generate_campaign_suggestions(analysis)
print(f"Generated {len(suggestions)} suggestions")
```

---

## 🔐 Access Control

```python
# Check if user can access feature
from adsbot.services import is_premium_user

if is_premium_user(session, user):
    # Show feature
    pass
else:
    # Show upgrade message
    pass
```

---

## 🚀 Deployment

### Pre-deployment
1. Backup database
2. Test with `python test_ai_campaigns.py`
3. Verify all files included

### Database migration
```sql
ALTER TABLE users ADD COLUMN subscription_type VARCHAR(50) DEFAULT 'gratis';
```

### Post-deployment
1. Test button appears in menu
2. Test with free user (should show upgrade)
3. Test with premium user (should work)

---

## 📞 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "Accesso negato" | Upgrade to premium |
| "Canale non trovato" | Add a channel first |
| "Errore analisi" | Wait, then try again |
| Button not showing | Rebuild/restart bot |
| No suggestions | Check channel data |

---

## 📚 Documentation Priority

1. **For Users**: `USER_GUIDE_AI_CAMPAIGNS.md`
2. **For Devs**: `DEVELOPER_GUIDE_AI_CAMPAIGNS.md`
3. **For Architects**: `ARCHITECTURE_AI_CAMPAIGNS.md`
4. **For All**: `AI_CAMPAIGN_GENERATION.md`

---

## ✅ Verification Checklist

- [x] Code compiles
- [x] No breaking changes
- [x] Backward compatible
- [x] All handlers registered
- [x] Error handling works
- [x] Logging active
- [x] Documentation complete
- [x] Tests pass
- [x] Security verified

---

## 🎯 Feature Status

```
✅ Implementation:    COMPLETE
✅ Testing:          COMPLETE  
✅ Documentation:    COMPLETE
✅ Security:         VERIFIED
✅ Performance:      OPTIMIZED
✅ Production Ready: YES
```

---

**Version**: 1.0.0
**Date**: December 3, 2025
**Status**: Production Ready ✅
