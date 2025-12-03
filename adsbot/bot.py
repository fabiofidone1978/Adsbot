"""Telegram bot entrypoint for Adsbot."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

# Patch APScheduler early to avoid timezone issues (must run before
# python-telegram-bot imports APScheduler internally).
try:
    import pytz
    import apscheduler.util as _aps_util

    # Simple ASTIMEZONE override: return UTC pytz tzinfo when APScheduler
    # asks for the localzone or converts timezones. This avoids the
    # 'Only timezones from the pytz library are supported' TypeError on
    # systems where local timezone is a zoneinfo tzinfo.
    def _astimezone_override(tz):
        return pytz.timezone("UTC")

    _aps_util.astimezone = _astimezone_override
except Exception:
    pass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Workaround: APScheduler expects pytz timezone objects; on some systems
# get_localzone() returns a zoneinfo tzinfo which APScheduler rejects.
# Patch apscheduler.util.get_localzone to return a pytz timezone (UTC)
# so JobQueue/AsyncIOScheduler initializes without TypeError.
try:
    import pytz
    import apscheduler.util as _aps_util

    def _get_localzone_pytz():
        return pytz.timezone("UTC")

    _aps_util.get_localzone = _get_localzone_pytz
except Exception:
    # If pytz or apscheduler not available yet, skip the patch; error
    # will surface later and should be handled by normal dependency fixes.
    pass

from .config import Config
from .db import create_session_factory, session_scope
from .models import OfferType
from .services import (
    add_campaign,
    add_channel,
    add_goal,
    add_offer,
    add_template,
    ensure_user,
    summarize_user,
)
from .inside_ads_services import (
    add_transaction,
    create_campaign_purchase,
    get_campaign_performance,
    get_user_balance,
    get_user_statistics,
    list_available_channels_for_ads,
)
from .payments import PaymentProcessor
from .notifications import (
    NotificationDispatcher,
    NotificationType,
    NotificationPreferences,
)
from .campaigns import (
    AdvancedCampaignManager,
    TargetingSettings,
    BudgetSettings,
    PaymentModel,
)
from .analytics import (
    PerformanceForecast,
    CampaignAnalytics,
    BudgetOptimizer,
    SmartRecommendations,
)
from .ai_content import (
    AIContentGenerator,
    ContentType,
    ToneType,
    ContentRequest,
    ContentTemplateLibrary,
)
from .campaign_analyzer import (
    CampaignAnalyzer,
    ChannelAnalysis,
)


logger = logging.getLogger(__name__)

(
    ADD_CHANNEL,
    GOAL_CHANNEL,
    GOAL_TARGET,
    GOAL_DEADLINE,
    OFFER_CHANNEL,
    OFFER_TYPE,
    OFFER_PRICE,
    OFFER_NOTES,
    CAMPAIGN_CHANNEL,
    CAMPAIGN_NAME,
    CAMPAIGN_BUDGET,
    CAMPAIGN_LOAD_BALANCE,
    CAMPAIGN_PRICE,
    CAMPAIGN_CTA,
    TEMPLATE_NAME,
    TEMPLATE_CONTENT,
    # Purchase campaign states
    SELECT_CAMPAIGN,
    ENTER_AMOUNT,
    SELECT_PAYMENT_PROVIDER,
    CONFIRM_PAYMENT,
    # AI Content Generation states
    GENERATE_TOPIC,
    SELECT_TONE,
    SELECT_PLATFORM,
    REVIEW_CONTENT,
    # AI Campaign Generation states
    AIGEN_SELECT_CHANNEL,
    AIGEN_ANALYZING,
    AIGEN_REVIEW_CAMPAIGNS,
    AIGEN_REVIEWING_CHANNEL,
    AIGEN_SELECTING_PLATFORM,
    AIGEN_SELECTING_TONE,
) = range(30)


# Old menu (kept for backward compatibility)
MENU_BUTTONS = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("➕ Aggiungi canale", callback_data="menu:add_channel"),
            InlineKeyboardButton("🎯 Obiettivi", callback_data="menu:goals"),
        ],
        [
            InlineKeyboardButton("💸 Offerte ADV", callback_data="menu:offers"),
            InlineKeyboardButton("📣 Campagna", callback_data="menu:campaign"),
        ],
        [
            InlineKeyboardButton("🧭 Template broadcast", callback_data="menu:template"),
            InlineKeyboardButton("📊 Statistiche", callback_data="menu:stats"),
        ],
        [
            InlineKeyboardButton("🤖 Genera Contenuti AI", callback_data="ai:menu"),
            InlineKeyboardButton("✨ Genera Campagna con AI", callback_data="aigen:start"),
        ],
    ]
)

# Inside Ads main menu
MAIN_MENU_BUTTONS = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("💰 Guadagna", callback_data="insideads:earn")],
        [InlineKeyboardButton("🛒 Acquista", callback_data="insideads:buy")],
        [InlineKeyboardButton("🔄 Scambio", callback_data="insideads:exchange")],
        [InlineKeyboardButton("📊 Statistiche", callback_data="insideads:stats")],
        [InlineKeyboardButton("👤 Account", callback_data="insideads:account")],
    ]
)

# Earn submenu (Guadagna)
EARN_MENU_BUTTONS = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("📝 Editore", callback_data="insideads:earn:editor")],
        [InlineKeyboardButton("🎯 Inserizionista", callback_data="insideads:earn:advertiser")],
        [InlineKeyboardButton("🆓 Iscritti gratis", callback_data="insideads:earn:free")],
        [InlineKeyboardButton("📈 Analisi canale", callback_data="insideads:earn:analysis")],
        [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:main")],
    ]
)


def with_session(context: CallbackContext):
    return session_scope(context.bot_data["session_factory"])


def format_summary(summary: dict[str, int]) -> str:
    return (
        "\n".join(
            [
                f"Canali gestiti: {summary['channels']}",
                f"Obiettivi attivi: {summary['goals']}",
                f"Offerte pubblicitarie: {summary['offers']}",
                f"Template broadcast: {summary['templates']}",
            ]
        )
    )


async def start(update: Update, context: CallbackContext) -> None:
    """Handle /start by registering the user and showing the main menu."""

    user_data = update.effective_user
    if not user_data:
        return

    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        summary = summarize_user(session, user)

    text = (
        "Benvenuto nel Growth & Monetization Bot!\n"
        "Puoi organizzare i tuoi canali, fissare obiettivi e creare offerte pubblicitarie."
    )
    await update.message.reply_text(
        f"{text}\n\n{format_summary(summary)}",
        reply_markup=MENU_BUTTONS,
    )


async def help_command(update: Update, context: CallbackContext) -> None:
    """Show a quick command reference."""

    text = (
        "Comandi disponibili:\n"
        "/start - mostra la dashboard\n"
        "/help - guida rapida\n"
        "/addchannel - registra un canale\n"
        "/goal - imposta un obiettivo di crescita\n"
        "/offer - salva un'offerta pubblicitaria\n"
        "/campaign - registra una campagna\n"
        "/template - crea un template di broadcast\n"
    )
    await update.message.reply_text(text)


async def open_menu(update: Update, context: CallbackContext) -> None:
    """Open the inline keyboard menu."""

    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("Scegli un'azione:", reply_markup=MENU_BUTTONS)


async def stats(update: Update, context: CallbackContext) -> None:
    """Show channel selection for statistics."""

    user_data = update.effective_user
    if not user_data:
        return
    
    query = update.callback_query
    if query:
        await query.answer()
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        
        # Prendi i canali dell'utente
        from .models import Channel
        channels = session.query(Channel).filter_by(user_id=user.id).all()
    
    if not channels:
        text = "📊 **Statistiche**\n\nNon hai ancora aggiunto canali. Aggiungi un canale per visualizzare le sue statistiche."
        if query:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Aggiungi Canale", callback_data="menu:add_channel")],
                [InlineKeyboardButton("◀️ Indietro", callback_data="menu:main")],
            ]))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Aggiungi Canale", callback_data="menu:add_channel")],
                [InlineKeyboardButton("◀️ Indietro", callback_data="menu:main")],
            ]))
        return
    
    # Crea la lista di canali
    text = "📊 **Scegli un canale per visualizzare le statistiche:**"
    keyboard = []
    
    for channel in channels:
        channel_name = f"@{channel.handle}" if channel.handle else f"#{channel.id}"
        button_text = f"📺 {channel_name}"
        if channel.title:
            button_text += f" - {channel.title[:20]}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"stats:channel:{channel.id}")])
    
    keyboard.append([InlineKeyboardButton("◀️ Indietro", callback_data="menu:main")])
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_channel_stats(update: Update, context: CallbackContext) -> None:
    """Show statistics for a specific channel."""
    query = update.callback_query
    await query.answer()
    
    # Estrai channel_id dal callback
    channel_id = int(query.data.split(":")[-1])
    
    user_data = update.effective_user
    with with_session(context) as session:
        from .models import Channel, Campaign
        
        channel = session.query(Channel).filter_by(id=channel_id).first()
        if not channel:
            await query.edit_message_text("❌ Canale non trovato")
            return
        
        # Calcola statistiche del canale
        total_campaigns = session.query(Campaign).filter_by(channel_id=channel_id).count()
        
        # Statistiche simulate (in produzione verrebbero da API vere)
        stats_text = (
            f"📊 **Statistiche Canale: {channel.handle}**\n\n"
            f"📺 **Informazioni Canale:**\n"
            f"• Nome: @{channel.handle}\n"
            f"• Titolo: {channel.title or 'N/A'}\n"
            f"• Argomento: {channel.topic or 'N/A'}\n\n"
            f"📈 **Metriche:**\n"
            f"• 👥 Follower: N/A*\n"
            f"• 👁️ Visualizzazioni (7d): N/A*\n"
            f"• 🖱️ Click ricevuti (7d): N/A*\n"
            f"• 📢 Condivisioni in altri canali: N/A*\n"
            f"• 📊 Campagne create: {total_campaigns}\n\n"
            f"💡 *Le metriche dettagliate verranno caricate dall'API di Telegram una volta configurata"
        )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Aggiorna", callback_data=f"stats:channel:{channel_id}")],
        [InlineKeyboardButton("📋 Campagne", callback_data=f"stats:campaigns:{channel_id}")],
        [InlineKeyboardButton("◀️ Indietro", callback_data="menu:stats")],
    ]
    
    await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard))



async def add_channel_entry(update: Update, context: CallbackContext) -> int:
    """Ask the user for a channel handle."""

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "Inserisci lo @username o il link del canale:"
        )
    else:
        await update.message.reply_text("Inserisci lo @username o il link del canale:")
    return ADD_CHANNEL


async def add_channel_save(update: Update, context: CallbackContext) -> int:
    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END

    handle = update.message.text.strip()
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        channel = add_channel(session, user, handle)
    await update.message.reply_text(
        f"✅ Canale {channel.handle} salvato!", reply_markup=MENU_BUTTONS
    )
    return ConversationHandler.END


async def goal_entry(update: Update, context: CallbackContext) -> int:
    """Begin a growth goal conversation - show bot selection menu."""

    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END

    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        # Get user's administered bots
        from .models import Channel
        channels = session.query(Channel).filter_by(user_id=user.id).all()

    if not channels:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "❌ Non hai canali amministrati ancora.\n\n"
                "Aggiungi un canale prima di creare obiettivi.",
                reply_markup=MENU_BUTTONS
            )
        else:
            await update.message.reply_text(
                "❌ Non hai canali amministrati ancora.\n\n"
                "Aggiungi un canale prima di creare obiettivi.",
                reply_markup=MENU_BUTTONS
            )
        return ConversationHandler.END

    # Show bot selection keyboard with search
    text = "🎯 Seleziona il canale per cui impostare un obiettivo:\n\n"
    keyboard = []
    
    for channel in channels[:10]:
        keyboard.append([
            InlineKeyboardButton(
                f"📱 {channel.handle} ({channel.title or 'Canale'})",
                callback_data=f"goal:select_channel:{channel.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔍 Cerca canale", callback_data="goal:search_channel")])
    keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="menu:home")])
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return GOAL_CHANNEL


async def goal_channel_selected(update: Update, context: CallbackContext) -> int:
    """User selected a channel for goal setup - check if goals already exist."""
    query = update.callback_query
    await query.answer()

    # Extract channel ID
    channel_id = int(query.data.split(":")[2])
    
    with with_session(context) as session:
        from .models import Channel, GrowthGoal
        channel = session.query(Channel).filter_by(id=channel_id).first()
        if not channel:
            await query.edit_message_text("❌ Canale non trovato.")
            return ConversationHandler.END
        
        # Controlla se ci sono già obiettivi per questo canale
        existing_goals = session.query(GrowthGoal).filter_by(channel_id=channel_id).all()
        
        context.user_data["goal_channel"] = channel.handle
        context.user_data["goal_channel_id"] = channel_id
        
        if existing_goals:
            # Mostra gli obiettivi già impostati
            goals_text = f"🎯 **Obiettivi per: @{channel.handle}**\n\n"
            
            for i, goal in enumerate(existing_goals, 1):
                goals_text += (
                    f"**Obiettivo #{i}:**\n"
                    f"👥 Target: {goal.target_members} iscritti\n"
                )
                if goal.deadline:
                    goals_text += f"📅 Scadenza: {goal.deadline.strftime('%d/%m/%Y')}\n"
                if goal.description:
                    goals_text += f"📝 Note: {goal.description}\n"
                goals_text += "\n"
            
            keyboard = [
                [InlineKeyboardButton("➕ Aggiungi nuovo obiettivo", callback_data=f"goal:new:{channel_id}")],
                [InlineKeyboardButton("✏️ Modifica", callback_data=f"goal:edit:{channel_id}")],
                [InlineKeyboardButton("◀️ Indietro", callback_data="menu:home")],
            ]
            
            await query.edit_message_text(goals_text, reply_markup=InlineKeyboardMarkup(keyboard))
            return ConversationHandler.END
    
    # Se non ci sono obiettivi, chiedi di crearne uno
    await query.edit_message_text(
        f"📊 Obiettivo per: @{context.user_data['goal_channel']}\n\n"
        "👥 **Quanti iscritti vuoi raggiungere?**\n\n"
        "Questo è il tuo **target di crescita**.\n"
        "Es: se hai 1000 iscritti, puoi metterti come obiettivo 5000.\n\n"
        "Scrivi un numero intero (es: 5000)"
    )
    return GOAL_TARGET


async def goal_search_channel(update: Update, context: CallbackContext) -> int:
    """Start channel search."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("🔍 Scrivi il nome o il @username del canale:")
    return GOAL_CHANNEL


async def goal_channel(update: Update, context: CallbackContext) -> int:
    """Handle channel search or selection."""
    search_term = update.message.text.strip().lower()
    
    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        
        from .models import Channel
        # Search for matching channels
        all_channels = session.query(Channel).filter_by(user_id=user.id).all()
        matching = [ch for ch in all_channels if search_term in ch.handle.lower()]
    
    if not matching:
        await update.message.reply_text(
            f"❌ Nessun canale trovato per '{search_term}'.\n\n"
            "Prova di nuovo:"
        )
        return GOAL_CHANNEL
    
    # Show search results
    text = f"🔍 Risultati per '{search_term}':\n\n"
    keyboard = []
    
    for channel in matching[:10]:
        keyboard.append([
            InlineKeyboardButton(
                f"📱 {channel.handle} ({channel.title or 'Canale'})",
                callback_data=f"goal:select_channel:{channel.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="menu:home")])
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return GOAL_CHANNEL


async def goal_target(update: Update, context: CallbackContext) -> int:
    try:
        target = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Inserisci un numero valido")
        return GOAL_TARGET

    context.user_data["goal_target"] = target
    await update.message.reply_text(
        "Qual è la deadline? (YYYY-MM-DD) oppure lascia vuoto per nessuna",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭️ Nessuna deadline", callback_data="goal:skip_deadline")],
        ])
    )
    return GOAL_DEADLINE


async def goal_skip_deadline(update: Update, context: CallbackContext) -> int:
    """Salta la deadline e salva l'obiettivo con deadline=None"""
    query = update.callback_query
    await query.answer()
    
    # Prendi i dati salvati
    user_id = context.user_data.get("user_id")
    channel_id = context.user_data.get("channel_id")
    target = context.user_data.get("goal_target")
    
    if not all([user_id, channel_id, target]):
        await query.edit_message_text("Errore: dati mancanti. Riprova con /goal")
        return ConversationHandler.END
    
    # Salva l'obiettivo senza deadline
    try:
        goal = GrowthGoal(
            user_id=user_id,
            channel_id=channel_id,
            target_subscribers=target,
            deadline=None,
            status="active",
            current_subscribers=0,
            created_at=datetime.now()
        )
        session.add(goal)
        session.commit()
        
        await query.edit_message_text(
            f"✅ Obiettivo di crescita creato con successo!\n"
            f"Target: {target:,} iscritti\n"
            f"Senza deadline"
        )
    except Exception as e:
        session.rollback()
        await query.edit_message_text(f"Errore nel salvataggio: {str(e)}")
    
    return ConversationHandler.END


async def goal_deadline(update: Update, context: CallbackContext) -> int:
    deadline_text = update.message.text.strip()
    deadline: Optional[datetime.date] = None
    if deadline_text:
        try:
            deadline = datetime.strptime(deadline_text, "%Y-%m-%d").date()
        except ValueError:
            await update.message.reply_text("Formato data non valido. Usa YYYY-MM-DD")
            return GOAL_DEADLINE

    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END

    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        channel = add_channel(session, user, context.user_data["goal_channel"])
        add_goal(session, channel, context.user_data["goal_target"], deadline)

    await update.message.reply_text(
        "🎯 Obiettivo registrato!", reply_markup=MENU_BUTTONS
    )
    return ConversationHandler.END


async def offer_entry(update: Update, context: CallbackContext) -> int:
    """Begin an offer conversation - show bot selection menu."""

    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END

    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        from .models import Channel
        channels = session.query(Channel).filter_by(user_id=user.id).all()

    if not channels:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "❌ Non hai canali amministrati ancora.\n\n"
                "Aggiungi un canale prima di creare offerte.",
                reply_markup=MENU_BUTTONS
            )
        else:
            await update.message.reply_text(
                "❌ Non hai canali amministrati ancora.\n\n"
                "Aggiungi un canale prima di creare offerte.",
                reply_markup=MENU_BUTTONS
            )
        return ConversationHandler.END

    text = "💸 Seleziona il canale dove creare l'offerta:\n\n"
    keyboard = []
    
    for channel in channels[:10]:
        keyboard.append([
            InlineKeyboardButton(
                f"📱 {channel.handle} ({channel.title or 'Canale'})",
                callback_data=f"offer:select_channel:{channel.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔍 Cerca canale", callback_data="offer:search_channel")])
    keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="menu:home")])
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return OFFER_CHANNEL


async def offer_channel_selected(update: Update, context: CallbackContext) -> int:
    """User selected a channel for offer setup."""
    query = update.callback_query
    await query.answer()

    channel_id = int(query.data.split(":")[2])
    
    with with_session(context) as session:
        from .models import Channel
        channel = session.query(Channel).filter_by(id=channel_id).first()
        if not channel:
            await query.edit_message_text("❌ Canale non trovato.")
            return ConversationHandler.END
        
        context.user_data["offer_channel"] = channel.handle
        context.user_data["offer_channel_id"] = channel_id
    
    await query.edit_message_text(
        f"💰 Offerta per: {context.user_data['offer_channel']}\n\n"
        "Che tipo di offerta? (shoutout, post, pinned, takeover)"
    )
    return OFFER_TYPE


async def offer_search_channel(update: Update, context: CallbackContext) -> int:
    """Start channel search for offers."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("🔍 Scrivi il nome o il @username del canale:")
    return OFFER_CHANNEL


async def offer_channel(update: Update, context: CallbackContext) -> int:
    """Handle channel search for offers."""
    search_term = update.message.text.strip().lower()
    
    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        
        from .models import Channel
        all_channels = session.query(Channel).filter_by(user_id=user.id).all()
        matching = [ch for ch in all_channels if search_term in ch.handle.lower()]
    
    if not matching:
        await update.message.reply_text(
            f"❌ Nessun canale trovato per '{search_term}'.\n\n"
            "Prova di nuovo:"
        )
        return OFFER_CHANNEL
    
    text = f"🔍 Risultati per '{search_term}':\n\n"
    keyboard = []
    
    for channel in matching[:10]:
        keyboard.append([
            InlineKeyboardButton(
                f"📱 {channel.handle} ({channel.title or 'Canale'})",
                callback_data=f"offer:select_channel:{channel.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="menu:home")])
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return OFFER_CHANNEL


async def offer_type(update: Update, context: CallbackContext) -> int:
    offer_type_value = update.message.text.strip().lower()
    try:
        offer_type_enum = OfferType(offer_type_value)
    except ValueError:
        guide = (
            "❓ **Tipi di offerta disponibili:**\n\n"
            "🔊 **Shoutout** - Menzione vocale del tuo prodotto\n"
            "📸 **Post** - Un post dedicato sul canale\n"
            "📌 **Pinned** - Post fisso in alto per più giorni\n"
            "🎯 **Takeover** - Controllo totale del canale per X ore\n\n"
            "Scrivi il tipo che preferisci: shoutout, post, pinned o takeover"
        )
        await update.message.reply_text(guide)
        return OFFER_TYPE

    context.user_data["offer_type"] = offer_type_enum
    await update.message.reply_text("Qual è il prezzo per l'inserzione? (es. 25.50)")
    return OFFER_PRICE


async def offer_price(update: Update, context: CallbackContext) -> int:
    try:
        price = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Inserisci un numero valido")
        return OFFER_PRICE

    context.user_data["offer_price"] = price
    await update.message.reply_text(
        "Note opzionali? Puoi descrivere il formato o lasciare vuoto",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭️ Salta note", callback_data="offer:skip_notes")],
        ])
    )
    return OFFER_NOTES


async def offer_skip_notes(update: Update, context: CallbackContext) -> int:
    """Salta le note opzionali dell'offerta."""
    query = update.callback_query
    await query.answer()
    
    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END

    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        channel = add_channel(session, user, context.user_data["offer_channel"])
        add_offer(
            session,
            channel,
            context.user_data["offer_type"],
            context.user_data["offer_price"],
            None,  # nessuna nota
        )

    await query.edit_message_text("✅ Offerta registrata!", reply_markup=MENU_BUTTONS)
    return ConversationHandler.END


async def offer_notes(update: Update, context: CallbackContext) -> int:
    notes = update.message.text.strip() if update.message.text else None
    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END

    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        channel = add_channel(session, user, context.user_data["offer_channel"])
        add_offer(
            session,
            channel,
            context.user_data["offer_type"],
            context.user_data["offer_price"],
            notes,
        )

    await update.message.reply_text("💸 Offerta salvata!", reply_markup=MENU_BUTTONS)
    return ConversationHandler.END


async def campaign_disclaimer(update: Update, context: CallbackContext) -> int:
    """Show disclaimer about campaign creation before proceeding."""
    query = update.callback_query
    if query:
        await query.answer()
    
    text = (
        "📣 **Creazione Campagna Manuale**\n\n"
        "Questa funzione è per te se:\n"
        "✅ Hai già idee chiare sulla campagna\n"
        "✅ Vuoi supporto nella creazione\n\n"
        "Se invece:\n"
        "❌ Non hai idee su cosa fare\n"
        "❌ Vuoi che l'AI generi le campagne\n\n"
        "👉 Usa '✨ Genera Campagna con AI' (gratis con upgrade)\n\n"
        "Cosa vuoi fare?"
    )
    
    keyboard = [
        [InlineKeyboardButton("➡️ Prosegui con creazione manuale", callback_data="campaign:proceed")],
        [InlineKeyboardButton("✨ Usa AI Campaign Generator", callback_data="aigen:start")],
        [InlineKeyboardButton("◀️ Indietro", callback_data="menu:home")],
    ]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    return CAMPAIGN_CHANNEL


async def upgrade_plan_selected(update: Update, context: CallbackContext) -> None:
    """Handle plan selection and show payment screen."""
    query = update.callback_query
    await query.answer()
    
    # Estrai il piano dal callback
    plan = query.data.split(":")[-1]  # "premium" o "pro"
    
    if plan == "premium":
        plan_name = "Premium"
        price = 9.99
        description = (
            "📦 **Piano Premium**\n\n"
            "✅ Crea campagne illimitate\n"
            "✅ Supporto prioritario\n"
            "✅ Analytics avanzate\n\n"
            "Prezzo: €9.99/mese"
        )
    else:  # pro
        plan_name = "Pro"
        price = 29.99
        description = (
            "👑 **Piano Pro**\n\n"
            "✅ Tutto di Premium +\n"
            "✅ Supporto 24/7\n"
            "✅ Funzioni AI avanzate\n\n"
            "Prezzo: €29.99/mese"
        )
    
    context.user_data["upgrade_plan"] = plan
    context.user_data["upgrade_price"] = price
    context.user_data["upgrade_plan_name"] = plan_name
    
    # Mostra il form di pagamento
    payment_text = (
        f"{description}\n\n"
        "💳 **Procedi al pagamento:**\n\n"
        "Per testare, puoi usare €0.00 per testare il flusso PayPal"
    )
    
    keyboard = [
        [InlineKeyboardButton("💳 Paga con PayPal", callback_data=f"upgrade:paypal:{plan}")],
        [InlineKeyboardButton("🧪 Test (€0.00)", callback_data=f"upgrade:test:{plan}")],
        [InlineKeyboardButton("◀️ Indietro", callback_data="campaign:payment")],
    ]
    
    await query.edit_message_text(payment_text, reply_markup=InlineKeyboardMarkup(keyboard))


async def upgrade_paypal(update: Update, context: CallbackContext) -> None:
    """Handle PayPal payment."""
    query = update.callback_query
    await query.answer()
    
    plan = query.data.split(":")[-1]
    plan_name = context.user_data.get("upgrade_plan_name", "Premium")
    price = context.user_data.get("upgrade_price", 9.99)
    
    text = (
        f"💳 **Pagamento PayPal**\n\n"
        f"Piano: {plan_name}\n"
        f"Importo: €{price:.2f}\n\n"
        f"Reindirizzamento a PayPal...\n\n"
        f"(In produzione, questo collegherebbe a PayPal)\n"
        f"Transazione ID: {update.effective_user.id}_{int(__import__('time').time())}"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Confermato", callback_data=f"upgrade:confirmed:{plan}")],
        [InlineKeyboardButton("❌ Annulla", callback_data="menu:home")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def upgrade_test(update: Update, context: CallbackContext) -> None:
    """Handle test payment (€0.00)."""
    query = update.callback_query
    await query.answer()
    
    plan = query.data.split(":")[-1]
    plan_name = context.user_data.get("upgrade_plan_name", "Premium")
    
    text = (
        f"🧪 **Test Pagamento**\n\n"
        f"Piano: {plan_name}\n"
        f"Importo: €0.00\n\n"
        f"✅ Pagamento di test completato!\n\n"
        f"L'upgrade sarà attivo entro pochi secondi..."
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Confermato", callback_data=f"upgrade:confirmed:{plan}")],
        [InlineKeyboardButton("❌ Annulla", callback_data="menu:home")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def upgrade_confirmed(update: Update, context: CallbackContext) -> None:
    """Handle confirmed upgrade."""
    query = update.callback_query
    await query.answer()
    
    plan = query.data.split(":")[-1]
    user_data = update.effective_user
    
    # Aggiorna il database con il piano
    with with_session(context) as session:
        from .models import User
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        user.subscription_type = plan
        session.commit()
    
    plan_name = context.user_data.get("upgrade_plan_name", "Premium")
    
    text = (
        f"🎉 **Upgrade Completato!**\n\n"
        f"Benvenuto al Piano {plan_name}!\n\n"
        f"✅ Accesso illimitato alle funzioni premium\n"
        f"✅ Supporto prioritario attivo\n\n"
        f"Ora puoi creare campagne personalizzate.\n"
        f"Ritorna al menu principale per iniziare!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Menu Principale", callback_data="menu:home")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def campaign_payment_request(update: Update, context: CallbackContext) -> int:
    """Show payment/upgrade request before creating campaign."""
    query = update.callback_query
    if query:
        await query.answer()
    
    text = (
        "💳 **Upgrade Richiesto**\n\n"
        "La creazione di campagne personalizzate richiede un upgrade premium.\n\n"
        "**Piano Premium** - €9.99/mese\n"
        "✅ Crea campagne illimitate\n"
        "✅ Supporto prioritario\n"
        "✅ Analytics avanzate\n\n"
        "**Piano Pro** - €29.99/mese\n"
        "✅ Tutto di Premium +\n"
        "✅ Supporto 24/7\n"
        "✅ Funzioni AI avanzate\n\n"
        "Scegli un piano per procedere:"
    )
    
    keyboard = [
        [InlineKeyboardButton("💳 Upgrade a Premium", callback_data="upgrade:premium")],
        [InlineKeyboardButton("👑 Scopri Piano Pro", callback_data="upgrade:pro")],
        [InlineKeyboardButton("◀️ Indietro", callback_data="menu:campaign")],
    ]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    return ConversationHandler.END


async def campaign_entry(update: Update, context: CallbackContext) -> int:
    """Begin a campaign conversation - show bot selection menu."""

    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END

    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        from .models import Channel
        channels = session.query(Channel).filter_by(user_id=user.id).all()

    if not channels:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "❌ Non hai canali amministrati ancora.\n\n"
                "Aggiungi un canale prima di creare campagne.",
                reply_markup=MENU_BUTTONS
            )
        else:
            await update.message.reply_text(
                "❌ Non hai canali amministrati ancora.\n\n"
                "Aggiungi un canale prima di creare campagne.",
                reply_markup=MENU_BUTTONS
            )
        return ConversationHandler.END

    text = "📣 Seleziona il canale dove lanciare la campagna:\n\n"
    keyboard = []
    
    for channel in channels[:10]:
        keyboard.append([
            InlineKeyboardButton(
                f"📱 {channel.handle} ({channel.title or 'Canale'})",
                callback_data=f"campaign:select_channel:{channel.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔍 Cerca canale", callback_data="campaign:search_channel")])
    keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="menu:home")])
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return CAMPAIGN_CHANNEL


async def campaign_channel_selected(update: Update, context: CallbackContext) -> int:
    """User selected a channel for campaign."""
    query = update.callback_query
    await query.answer()

    channel_id = int(query.data.split(":")[2])
    
    with with_session(context) as session:
        from .models import Channel
        channel = session.query(Channel).filter_by(id=channel_id).first()
        if not channel:
            await query.edit_message_text("❌ Canale non trovato.")
            return ConversationHandler.END
        
        context.user_data["campaign_channel"] = channel.handle
        context.user_data["campaign_channel_id"] = channel_id
    
    await query.edit_message_text(
        f"📣 Campagna su: {context.user_data['campaign_channel']}\n\n"
        "Nome della campagna?"
    )
    return CAMPAIGN_NAME


async def campaign_search_channel(update: Update, context: CallbackContext) -> int:
    """Start channel search for campaigns."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("🔍 Scrivi il nome o il @username del canale:")
    return CAMPAIGN_CHANNEL


async def campaign_channel(update: Update, context: CallbackContext) -> int:
    """Handle channel search for campaigns."""
    search_term = update.message.text.strip().lower()
    
    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        
        from .models import Channel
        all_channels = session.query(Channel).filter_by(user_id=user.id).all()
        matching = [ch for ch in all_channels if search_term in ch.handle.lower()]
    
    if not matching:
        await update.message.reply_text(
            f"❌ Nessun canale trovato per '{search_term}'.\n\n"
            "Prova di nuovo:"
        )
        return CAMPAIGN_CHANNEL
    
    text = f"🔍 Risultati per '{search_term}':\n\n"
    keyboard = []
    
    for channel in matching[:10]:
        keyboard.append([
            InlineKeyboardButton(
                f"📱 {channel.handle} ({channel.title or 'Canale'})",
                callback_data=f"campaign:select_channel:{channel.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="menu:home")])
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return CAMPAIGN_CHANNEL


async def campaign_name(update: Update, context: CallbackContext) -> int:
    context.user_data["campaign_name"] = update.message.text.strip()
    await update.message.reply_text(
        "Budget previsto? (numero, opzionale, altrimenti lascia vuoto)"
    )
    return CAMPAIGN_BUDGET


async def campaign_budget(update: Update, context: CallbackContext) -> int:
    budget_text = update.message.text.strip()
    budget = None
    if budget_text:
        try:
            budget = float(budget_text)
        except ValueError:
            await update.message.reply_text("Inserisci un numero valido o lascia vuoto")
            return CAMPAIGN_BUDGET
    context.user_data["campaign_budget"] = budget
    
    # Controlla il saldo dell'utente
    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        balance = get_user_balance(session, user.id)
    
    if balance < 50:  # Minimo richiesto
        await update.message.reply_text(
            f"💰 **Saldo insufficiente**\n\n"
            f"Saldo attuale: €{balance:.2f}\n"
            f"Minimo richiesto per campagne: €50.00\n\n"
            f"Desideri caricare crediti?"
        )
        return CAMPAIGN_LOAD_BALANCE
    
    # Se ha crediti sufficienti, chiedi il prezzo per inserzione (opzionale)
    await update.message.reply_text(
        f"💵 **Prezzo per inserzione** (opzionale)\n\n"
        f"Quanto vuoi spendere per ogni post? (es. 25.50)\n"
        f"Saldo disponibile: €{balance:.2f}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭️ Salta prezzo", callback_data="campaign:skip_price")],
        ])
    )
    return CAMPAIGN_PRICE


async def campaign_load_balance(update: Update, context: CallbackContext) -> int:
    """Permette all'utente di caricare crediti."""
    keyboard = [
        [InlineKeyboardButton("💶 Carica €50", callback_data="campaign:load:50")],
        [InlineKeyboardButton("💶 Carica €100", callback_data="campaign:load:100")],
        [InlineKeyboardButton("💶 Carica €250", callback_data="campaign:load:250")],
        [InlineKeyboardButton("✏️ Inserisci importo", callback_data="campaign:load:custom")],
        [InlineKeyboardButton("⏭️ Continua ugualmente", callback_data="campaign:skip_load")],
    ]
    await update.message.reply_text(
        "Scegli un importo da caricare oppure inserisci un importo personalizzato:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CAMPAIGN_LOAD_BALANCE


async def campaign_skip_price(update: Update, context: CallbackContext) -> int:
    """Salta il prezzo per inserzione e procede al CTA."""
    query = update.callback_query
    await query.answer()
    
    context.user_data["campaign_price"] = None
    
    # Procedi al CTA
    await query.edit_message_text(
        "📍 **Call to Action** (CTA) o note della campagna? (opzionale)\n\n"
        "❓ **Che cos'è il CTA?**\n"
        "È il messaggio che invita l'utente ad agire:\n\n"
        "✅ Esempi buoni:\n"
        "• 'Clicca il link in bio'\n"
        "• 'Scarica subito l'app'\n"
        "• 'Visita il nostro sito'\n"
        "• 'Iscriviti al canale'\n\n"
        "Scrivi il tuo CTA o lascia vuoto se non serve",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭️ Salta CTA", callback_data="campaign:skip_cta")],
        ])
    )
    return CAMPAIGN_CTA


async def campaign_price(update: Update, context: CallbackContext) -> int:
    """Chiede il prezzo per singolo post della campagna."""
    price_text = update.message.text.strip()
    try:
        price = float(price_text)
        if price <= 0:
            await update.message.reply_text(
                "Il prezzo deve essere positivo. Riprova:"
            )
            return CAMPAIGN_PRICE
    except ValueError:
        await update.message.reply_text(
            "Inserisci un numero valido (es. 25.50)"
        )
        return CAMPAIGN_PRICE
    
    context.user_data["campaign_price"] = price
    
    # Procedi al CTA (opzionale)
    await update.message.reply_text(
        f"📍 **Prezzo per inserzione**: €{price:.2f}\n\n"
        "📍 **Call to Action** (CTA) o note della campagna? (opzionale)\n\n"
        "❓ **Che cos'è il CTA?**\n"
        "È il messaggio che invita l'utente ad agire:\n\n"
        "✅ Esempi buoni:\n"
        "• 'Clicca il link in bio'\n"
        "• 'Scarica subito l'app'\n"
        "• 'Visita il nostro sito'\n"
        "• 'Iscriviti al canale'\n\n"
        "Scrivi il tuo CTA o lascia vuoto se non serve",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭️ Salta CTA", callback_data="campaign:skip_cta")],
        ])
    )
    return CAMPAIGN_CTA


async def campaign_skip_cta(update: Update, context: CallbackContext) -> int:
    """Salta il CTA opzionale e salva la campagna."""
    query = update.callback_query
    await query.answer()
    
    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END

    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        channel = add_channel(session, user, context.user_data["campaign_channel"])
        add_campaign(
            session,
            channel,
            name=context.user_data["campaign_name"],
            budget=context.user_data["campaign_budget"],
            call_to_action=None,  # nessun CTA
        )

    await query.edit_message_text("📣 Campagna registrata!", reply_markup=MENU_BUTTONS)
    return ConversationHandler.END


async def campaign_cta(update: Update, context: CallbackContext) -> int:
    cta = update.message.text.strip() if update.message.text else None
    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END

    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        channel = add_channel(session, user, context.user_data["campaign_channel"])
        add_campaign(
            session,
            channel,
            name=context.user_data["campaign_name"],
            budget=context.user_data["campaign_budget"],
            call_to_action=cta,
        )

    await update.message.reply_text("📣 Campagna registrata!", reply_markup=MENU_BUTTONS)
    return ConversationHandler.END


async def template_entry(update: Update, context: CallbackContext) -> int:
    """Begin a broadcast template conversation."""

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "Scegli un nome per il template broadcast"
        )
    return TEMPLATE_NAME


async def template_name(update: Update, context: CallbackContext) -> int:
    context.user_data["template_name"] = update.message.text.strip()
    await update.message.reply_text("Incolla il contenuto del broadcast")
    return TEMPLATE_CONTENT


async def template_content(update: Update, context: CallbackContext) -> int:
    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END

    content = update.message.text
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        add_template(session, user, context.user_data["template_name"], content)

    await update.message.reply_text("🧭 Template salvato!", reply_markup=MENU_BUTTONS)
    return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Operazione annullata", reply_markup=MENU_BUTTONS)
    return ConversationHandler.END


# ==================== Inside Ads Menu Handlers ====================


async def insideads_main_menu(update: Update, context: CallbackContext) -> None:
    """Show main Inside Ads menu."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("🎯 Inside Ads - Menu principale", reply_markup=MAIN_MENU_BUTTONS)
    else:
        await update.message.reply_text("🎯 Inside Ads - Menu principale", reply_markup=MAIN_MENU_BUTTONS)


async def insideads_earn_menu(update: Update, context: CallbackContext) -> None:
    """Show Earn (Guadagna) submenu."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "💰 Guadagna - Scegli come monetizzare il tuo canale:",
            reply_markup=EARN_MENU_BUTTONS,
        )


async def insideads_earn_editor(update: Update, context: CallbackContext) -> None:
    """Editore - Monetizza il contenuto."""
    query = update.callback_query
    if query:
        await query.answer()
        text = (
            "📝 Editore\n\n"
            "Monetizza il tuo contenuto e guadagna mostrando annunci sul tuo canale.\n\n"
            "🟢 GUADAGNA DENARO\n\n"
            "Descrizione: Mostra annunci al tuo pubblico e guadagna da ogni impressione e click."
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:earn")],
        ]))


async def insideads_buy_menu(update: Update, context: CallbackContext) -> None:
    """Show Buy (Acquista) menu - list available campaigns."""
    query = update.callback_query
    user_data = update.effective_user
    if not user_data:
        return
    
    if query:
        await query.answer()
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        balance = context.bot_data.get("inside_ads_services").get_user_balance(session, user)
    
    text = (
        f"🛒 Acquista Annunci\n\n"
        f"Saldo attuale: ${balance:.2f}\n\n"
        f"Qui puoi acquistare annunci su canali selezionati."
    )
    
    keyboard = [
        [InlineKeyboardButton("➕ Crea campagna", callback_data="insideads:buy:create")],
        [InlineKeyboardButton("📋 Le mie campagne", callback_data="insideads:buy:list")],
        [InlineKeyboardButton("🤖 Genera Contenuti AI", callback_data="ai:menu")],
        [InlineKeyboardButton("📊 Gestione Campagne Avanzate", callback_data="campaign:menu")],
        [InlineKeyboardButton("🧠 AI Optimization", callback_data="campaign:ai_optimize")],
        [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:main")],
    ]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def insideads_exchange_menu(update: Update, context: CallbackContext) -> None:
    """Show Exchange (Scambio) menu."""
    query = update.callback_query
    if query:
        await query.answer()
        text = (
            "🔄 Scambio Iscritti\n\n"
            "Sistema di scambio automatico di iscritti tra canali.\n"
            "Un unico pool comune, non interfierisce con i pagamenti.\n\n"
            "Totalmente gratuito!"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Metriche", callback_data="insideads:exchange:metrics")],
            [InlineKeyboardButton("➕ Configura scambio", callback_data="insideads:exchange:setup")],
            [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:main")],
        ]))


async def insideads_stats_menu(update: Update, context: CallbackContext) -> None:
    """Show Statistics dashboard."""
    query = update.callback_query
    user_data = update.effective_user
    if not user_data:
        return
    
    if query:
        await query.answer()
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        from .inside_ads_services import get_user_statistics
        stats = get_user_statistics(session, user)
    
    text = (
        "📊 Statistiche\n\n"
        f"💰 Saldo: ${stats['balance']:.2f}\n"
        f"📺 Canali: {stats['channels']}\n"
        f"📢 Campagne: {stats['campaigns']}\n"
        f"👥 Follower (7d): {stats['followers']}\n"
        f"🖱️ Click (7d): {stats['clicks']}\n"
        f"👁️ Visualizzazioni (7d): {stats['impressions']}"
    )
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📈 Pubblicit\u00e0", callback_data="insideads:stats:ads")],
            [InlineKeyboardButton("💵 Monetizzazione", callback_data="insideads:stats:monetization")],
            [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:main")],
        ]))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📈 Pubblicit\u00e0", callback_data="insideads:stats:ads")],
            [InlineKeyboardButton("💵 Monetizzazione", callback_data="insideads:stats:monetization")],
            [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:main")],
        ]))


async def insideads_buy_create(update: Update, context: CallbackContext) -> int:
    """Start campaign purchase flow."""
    query = update.callback_query
    if query:
        await query.answer()
    
    return await purchase_campaign_start(update, context)


async def insideads_buy_list(update: Update, context: CallbackContext) -> None:
    """Show user's campaigns."""
    query = update.callback_query
    user_data = update.effective_user
    if not user_data:
        return
    
    if query:
        await query.answer()
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        from .inside_ads_services import get_user_campaigns
        campaigns = get_user_campaigns(session, user)
    
    if not campaigns:
        text = "📋 Le mie campagne\n\nNessuna campagna creata ancora."
    else:
        text = "📋 Le mie campagne\n\n"
        for idx, camp in enumerate(campaigns[:5], 1):
            text += f"{idx}. {camp.name}\n   Budget: ${camp.budget or 0:.2f}\n"
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:buy")],
        ]))


async def insideads_exchange_metrics(update: Update, context: CallbackContext) -> None:
    """Show exchange metrics."""
    query = update.callback_query
    user_data = update.effective_user
    if not user_data:
        return
    
    if query:
        await query.answer()
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        channels = session.query(Channel).filter_by(user_id=user.id).all()
    
    text = "📊 Metriche Scambio\n\n"
    if not channels:
        text += "Nessun canale configurato ancora."
    else:
        for ch in channels[:3]:
            text += f"📺 {ch.handle}\n   Follower: 0\n   Click: 0\n\n"
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:exchange")],
        ]))


async def insideads_exchange_setup(update: Update, context: CallbackContext) -> None:
    """Setup exchange for user channels."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "⚙️ Configura Scambio\n\n"
            "Funzionalità di configurazione scambio non ancora disponibile.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:exchange")],
            ])
        )


async def insideads_stats_ads(update: Update, context: CallbackContext) -> None:
    """Show advertising statistics."""
    query = update.callback_query
    user_data = update.effective_user
    if not user_data:
        return
    
    if query:
        await query.answer()
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        from .inside_ads_services import get_user_statistics
        stats = get_user_statistics(session, user)
    
    text = (
        "📈 Pubblicità\n\n"
        f"Campagne attive: {stats['campaigns']}\n"
        f"👥 Follower (7d): {stats['followers']}\n"
        f"🖱️ Click (7d): {stats['clicks']}\n"
        f"👁️ Visualizzazioni (7d): {stats['impressions']}\n\n"
        f"Crea nuovo →"
    )
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Nuova campagna", callback_data="insideads:buy:create")],
            [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:stats")],
        ]))


async def insideads_stats_monetization(update: Update, context: CallbackContext) -> None:
    """Show monetization statistics."""
    query = update.callback_query
    user_data = update.effective_user
    if not user_data:
        return
    
    if query:
        await query.answer()
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        from .inside_ads_services import get_user_balance
        balance = get_user_balance(session, user)
    
    text = (
        "💵 Monetizzazione Canali\n\n"
        f"Canali attivi: 1\n"
        f"Entrate totali: ${balance:.2f}\n"
        f"Entrate (7d): $0.00\n\n"
        f"Configura nuovo →"
    )
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ Configura", callback_data="insideads:earn:editor")],
            [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:stats")],
        ]))


async def insideads_account_menu(update: Update, context: CallbackContext) -> None:
    """Show Account menu."""
    query = update.callback_query
    user_data = update.effective_user
    if not user_data:
        return
    
    if query:
        await query.answer()
    
    text = (
        f"👤 Account\n\n"
        f"👤 Nome: {user_data.first_name}\n"
        f"💬 Username: @{user_data.username or 'N/A'}\n\n"
        f"Opzioni:"
    )
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Transazioni", callback_data="insideads:account:transactions")],
            [InlineKeyboardButton("⚙️ Impostazioni", callback_data="insideads:account:settings")],
            [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:main")],
        ]))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Transazioni", callback_data="insideads:account:transactions")],
            [InlineKeyboardButton("⚙️ Impostazioni", callback_data="insideads:account:settings")],
            [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:main")],
        ]))


async def insideads_account_transactions(update: Update, context: CallbackContext) -> None:
    """Show user transactions."""
    query = update.callback_query
    user_data = update.effective_user
    if not user_data:
        return
    
    if query:
        await query.answer()
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        from .inside_ads_services import get_recent_transactions
        transactions = get_recent_transactions(session, user, days=30)
    
    text = "💳 Transazioni\n\n"
    if not transactions:
        text += "Nessuna transazione ancora."
    else:
        for tx in transactions[:5]:
            symbol = "+" if tx.transaction_type in ("earn", "refund") else "-"
            text += f"{symbol}${tx.amount:.2f} - {tx.description}\n"
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:account")],
        ]))


async def insideads_account_settings(update: Update, context: CallbackContext) -> None:
    """Show account settings."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "⚙️ Impostazioni Account\n\n"
            "Funzionalità di impostazioni non ancora disponibile.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:account")],
            ])
        )


# Purchase campaign flow handlers
async def purchase_campaign_start(update: Update, context: CallbackContext) -> int:
    """Start the campaign purchase flow - show available channels."""
    user_data = update.effective_user
    query = update.callback_query
    
    if query:
        await query.answer()
    
    # Get available channels
    with session_scope(context.bot_data["session_factory"]) as session:
        channels = list_available_channels_for_ads(session)
        
        if not channels:
            text = "❌ Nessun canale disponibile per la pubblicità al momento."
            buttons = [[InlineKeyboardButton("◀️ Indietro", callback_data="insideads:buy")]]
        else:
            text = "📢 Seleziona un canale dove pubblicare la tua campagna:\n\n"
            buttons = []
            for channel in channels[:10]:
                buttons.append([
                    InlineKeyboardButton(
                        f"@{channel.handle}",
                        callback_data=f"purchase:select_channel:{channel.id}"
                    )
                ])
            buttons.append([InlineKeyboardButton("◀️ Indietro", callback_data="insideads:buy")])
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    return SELECT_CAMPAIGN


async def purchase_campaign_select(update: Update, context: CallbackContext) -> int:
    """User selected a channel - ask for campaign details."""
    query = update.callback_query
    await query.answer()
    
    # Extract channel ID from callback
    data = query.data.split(":")
    channel_id = int(data[2])
    context.user_data["selected_channel_id"] = channel_id
    
    with session_scope(context.bot_data["session_factory"]) as session:
        from .models import Channel
        channel = session.query(Channel).filter_by(id=channel_id).first()
        if not channel:
            await query.edit_message_text("❌ Canale non trovato.")
            return SELECT_CAMPAIGN
        
        context.user_data["selected_channel_handle"] = channel.handle
    
    await query.edit_message_text(
        f"✍️ Inserisci il nome della tua campagna per @{context.user_data['selected_channel_handle']}:",
        reply_markup=None
    )
    
    return ENTER_AMOUNT


async def purchase_campaign_amount(update: Update, context: CallbackContext) -> int:
    """User entered campaign name - ask for budget."""
    campaign_name = update.message.text
    context.user_data["campaign_name"] = campaign_name
    
    await update.message.reply_text(
        f"💰 Qual è il budget per questa campagna? (in USD)\n\nCampagna: {campaign_name}",
        reply_markup=None
    )
    
    return SELECT_PAYMENT_PROVIDER


async def purchase_campaign_provider(update: Update, context: CallbackContext) -> int:
    """User entered budget - ask for payment provider."""
    try:
        budget = float(update.message.text)
        if budget <= 0:
            await update.message.reply_text("❌ Il budget deve essere maggiore di 0.")
            return SELECT_PAYMENT_PROVIDER
        
        context.user_data["budget"] = budget
        
        # Check balance
        user_data = update.effective_user
        with session_scope(context.bot_data["session_factory"]) as session:
            from .models import User
            ensure_user(session, user_data)
            user = session.query(User).filter_by(user_id=user_data.id).first()
            balance = get_user_balance(session, user)
            
            if balance.balance < budget:
                await update.message.reply_text(
                    f"❌ Saldo insufficiente.\n\nTuo saldo: ${balance.balance:.2f}\nBudget richiesto: ${budget:.2f}"
                )
                return SELECT_PAYMENT_PROVIDER
        
        # Show payment providers
        buttons = [
            [InlineKeyboardButton("💳 Stripe", callback_data="purchase:payment:stripe")],
            [InlineKeyboardButton("🅿️ PayPal", callback_data="purchase:payment:paypal")],
            [InlineKeyboardButton("❌ Annulla", callback_data="insideads:buy")],
        ]
        
        await update.message.reply_text(
            f"💳 Scegli metodo di pagamento:\n\n"
            f"Campagna: {context.user_data['campaign_name']}\n"
            f"Canale: @{context.user_data['selected_channel_handle']}\n"
            f"Budget: ${budget:.2f}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        return CONFIRM_PAYMENT
        
    except ValueError:
        await update.message.reply_text("❌ Inserisci un importo valido (es: 50.00)")
        return SELECT_PAYMENT_PROVIDER


async def purchase_campaign_confirm(update: Update, context: CallbackContext) -> int:
    """User selected payment provider - process payment."""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":")
    provider = data[2]
    
    user_data = update.effective_user
    
    try:
        with session_scope(context.bot_data["session_factory"]) as session:
            from .models import User, Channel
            
            ensure_user(session, user_data)
            user = session.query(User).filter_by(user_id=user_data.id).first()
            channel = session.query(Channel).filter_by(id=context.user_data["selected_channel_id"]).first()
            
            # Process payment through payment processor
            payment_processor = PaymentProcessor()
            budget = context.user_data["budget"]
            campaign_name = context.user_data["campaign_name"]
            
            # Create payment
            payment_result = payment_processor.process_payment(
                provider=provider,
                amount=int(budget * 100),  # Convert to cents
                currency="usd",
                description=f"Campaign: {campaign_name} on {channel.handle}",
                customer_email=user_data.username or "unknown@example.com"
            )
            
            if not payment_result or payment_result.get("status") not in ("succeeded", "pending", "created"):
                await query.edit_message_text(
                    f"❌ Errore nel pagamento.\n\n{payment_result.get('error', 'Unknown error') if payment_result else 'Unknown error'}"
                )
                return ConversationHandler.END
            
            # Record transaction
            add_transaction(
                session,
                user,
                "spend",
                budget,
                f"Campaign purchase on {channel.handle}",
                reference_id=channel.id
            )
            
            # Log purchase
            seller = channel.owner
            seller_earning = budget * 0.8
            add_transaction(
                session,
                seller,
                "earn",
                seller_earning,
                f"Ad revenue from campaign '{campaign_name}'",
                reference_id=channel.id
            )
            
            # Send notifications
            notification_dispatcher = NotificationDispatcher(context.bot)
            await notification_dispatcher.send_notification(
                user.user_id,
                NotificationType.CAMPAIGN_PURCHASED,
                {
                    "campaign_name": campaign_name,
                    "channel_handle": channel.handle,
                }
            )
            
            await notification_dispatcher.send_notification(
                seller.user_id,
                NotificationType.CAMPAIGN_EARNED,
                {
                    "amount": seller_earning,
                    "channel_handle": channel.handle,
                }
            )
            
            await query.edit_message_text(
                f"✅ Campagna acquistata con successo!\n\n"
                f"Campagna: {campaign_name}\n"
                f"Canale: @{channel.handle}\n"
                f"Budget: ${budget:.2f}\n\n"
                f"ID Transazione: {payment_result.get('payment_intent_id', 'N/A')}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Menu principale", callback_data="insideads:main")],
                ])
            )
            
    except Exception as e:
        logger.error(f"Payment processing error: {e}")
        await query.edit_message_text(
            f"❌ Errore durante il processamento del pagamento.\n\nTentare di nuovo più tardi."
        )
    
    return ConversationHandler.END


# Advanced campaign management handlers
async def campaign_management_menu(update: Update, context: CallbackContext) -> None:
    """Show campaign management menu."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🎬 Gestione Campagne Avanzata\n\n"
            "Opzioni disponibili:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Crea Campagna Multi-Variante", callback_data="campaign:create_multi")],
                [InlineKeyboardButton("✨ Genera Campagna con AI", callback_data="aigen:start")],
                [InlineKeyboardButton("📈 Visualizza Previsioni", callback_data="campaign:forecast")],
                [InlineKeyboardButton("🤖 AI Optimization", callback_data="campaign:ai_optimize")],
                [InlineKeyboardButton("💡 Suggerimenti Campagna", callback_data="campaign:suggestions")],
                [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:main")],
            ])
        )


async def campaign_create_multi(update: Update, context: CallbackContext) -> None:
    """Start creating multi-variant campaign."""
    query = update.callback_query
    user_data = update.effective_user
    if not user_data:
        return
    
    if query:
        await query.answer()
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        
        # Get user channels for targeting options
        channels = session.query(Channel).filter_by(user_id=user.id).all()
    
    if not channels:
        await query.edit_message_text(
            "❌ Non hai canali disponibili.\n\n"
            "Aggiungi prima un canale per poter creare campagne.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Indietro", callback_data="campaign:menu")],
            ])
        )
        return
    
    context.user_data["creating_campaign"] = {
        "step": "select_channels",
        "variant_count": 0
    }
    
    # Create channel selection keyboard
    keyboard = [[InlineKeyboardButton(f"📱 {ch.handle} ({ch.subscribers:,} iscritti)", callback_data=f"campaign_ch:{ch.id}")] for ch in channels]
    keyboard.append([InlineKeyboardButton("◀️ Indietro", callback_data="campaign:menu")])
    
    await query.edit_message_text(
        "🎨 Crea Campagna Multi-Variante\n\n"
        "Seleziona i canali target per la campagna:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def campaign_forecast(update: Update, context: CallbackContext) -> None:
    """Show performance forecast."""
    query = update.callback_query
    user_data = update.effective_user
    if not user_data:
        return
    
    if query:
        await query.answer()
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        
        # Get user's active campaigns
        campaigns = session.query(Campaign).filter_by(user_id=user.id).all()
    
    if not campaigns:
        await query.edit_message_text(
            "📊 Previsioni Disponibili\n\n"
            "Non hai ancora campagne attive.\n"
            "Crea una campagna per visualizzare le previsioni.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Indietro", callback_data="campaign:menu")],
            ])
        )
        return
    
    # Get latest campaign for forecast
    campaign = campaigns[-1]
    
    # Example forecast with realistic data
    forecast = PerformanceForecast.estimate_weekly_metrics(
        daily_impressions=5000,
        daily_ctr=3.5,
        daily_conversion=8.0,
        budget_per_day=20.0,
    )
    
    monthly_forecast = PerformanceForecast.estimate_monthly_metrics(
        daily_impressions=5000,
        daily_ctr=3.5,
        daily_conversion=8.0,
        budget_per_day=20.0,
    )
    
    text = (
        f"📊 Previsioni Campagna: {campaign.name}\n\n"
        f"**Settimanale:**\n"
        f"Impressioni: {forecast['impressions']:,}\n"
        f"Click: {forecast['clicks']:,}\n"
        f"Conversioni: {forecast['conversions']:,}\n"
        f"Budget: ${forecast['budget']:.2f}\n"
        f"CTR: {forecast['ctr']:.2f}%\n"
        f"CPA: ${forecast['cpa']:.2f}\n\n"
        f"**Mensile (stima):**\n"
        f"Impressioni: {monthly_forecast['impressions']:,}\n"
        f"Budget: ${monthly_forecast['budget']:.2f}\n"
        f"Potenziale ROI: {monthly_forecast['estimated_roi']:.1f}%"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Analisi Break-Even", callback_data="campaign:breakeven")],
            [InlineKeyboardButton("◀️ Indietro", callback_data="campaign:menu")],
        ])
    )


async def campaign_ai_optimize(update: Update, context: CallbackContext) -> None:
    """Apply AI optimization."""
    query = update.callback_query
    user_data = update.effective_user
    if not user_data:
        return
    
    if query:
        await query.answer()
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        
        # Get campaigns for analysis
        campaigns = session.query(Campaign).filter_by(user_id=user.id).all()
    
    if not campaigns:
        await query.edit_message_text(
            "🤖 AI Optimization\n\n"
            "Nessuna campagna disponibile per l'analisi.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Indietro", callback_data="campaign:menu")],
            ])
        )
        return
    
    # Get real campaign summary
    campaign = campaigns[-1]
    campaign_summary = {
        "ctr": min(5.0, max(0.5, (campaign.clicks or 0) / max(1, campaign.impressions or 1) * 100)),
        "cpa": 6.5,
        "roi": (campaign.conversions or 0) * 10 - (campaign.budget or 0),
        "spent": campaign.budget * 0.6,
        "budget": campaign.budget,
    }
    
    recommendations = SmartRecommendations.get_optimization_suggestions(
        campaign_summary=campaign_summary,
        variant_comparison={
            "best_ctr": campaign_summary["ctr"] * 1.5,
            "worst_ctr": campaign_summary["ctr"] * 0.5,
        }
    )
    
    text = f"🤖 AI Optimization per: {campaign.name}\n\n"
    if recommendations:
        for rec in recommendations:
            priority_emoji = "🔴" if rec["priority"] == "critical" else "🟠" if rec["priority"] == "high" else "🟡"
            text += f"{priority_emoji} **{rec['message']}**\n"
            text += f"   → {rec['action']}\n\n"
    else:
        text += "✅ Campagna in ottime condizioni!\n\n"
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Visualizza Previsioni", callback_data="campaign:forecast")],
            [InlineKeyboardButton("◀️ Indietro", callback_data="campaign:menu")],
        ])
    )


async def campaign_suggestions(update: Update, context: CallbackContext) -> None:
    """Show smart recommendations."""
    query = update.callback_query
    user_data = update.effective_user
    if not user_data:
        return
    
    if query:
        await query.answer()
    
    with with_session(context) as session:
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        
        campaigns = session.query(Campaign).filter_by(user_id=user.id).all()
    
    if not campaigns:
        suggestions_text = (
            "💡 Suggerimenti Intelligenti\n\n"
            "Nessuna campagna ancora disponibile.\n"
            "Crea la tua prima campagna per ricevere suggerimenti personalizzati!"
        )
    else:
        campaign = campaigns[-1]
        budget_spent = (campaign.budget or 0) * 0.6
        budget_remaining = (campaign.budget or 0) - budget_spent
        
        suggestions_text = f"💡 Suggerimenti per: {campaign.name}\n\n"
        
        if campaign.clicks and campaign.impressions:
            ctr = (campaign.clicks / campaign.impressions) * 100
            if ctr > 3:
                suggestions_text += "✅ **Variante A**: CTR eccellente (> 3%)\n   → Aumenta il budget per massimizzare\n\n"
            elif ctr < 1:
                suggestions_text += "⚠️ **Performance bassa**: CTR < 1%\n   → Considera di modificare il creativo\n\n"
        
        if budget_remaining > 0:
            days_left = 30 - (campaign.duration_days or 0)
            if days_left > 0:
                daily_pace = budget_remaining / days_left
                suggestions_text += f"💰 **Budget ottimale**: ${daily_pace:.2f}/giorno\n   → Ritmo di spesa bilanciato\n\n"
        
        suggestions_text += (
            "🎯 **Targeting ottimale**: Espandi a categorie correlate\n"
            "   → Potrebbe aumentare il reach del 25%\n\n"
            "📊 **Test A/B**: Crea una variante aggiuntiva\n"
            "   → Identifica i creativi migliori\n"
        )
    
    await query.edit_message_text(
        suggestions_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 AI Optimization", callback_data="campaign:ai_optimize")],
            [InlineKeyboardButton("◀️ Indietro", callback_data="campaign:menu")],
        ])
    )


# AI Content Generation Handlers
async def generate_post_menu(update: Update, context: CallbackContext) -> int:
    """Show AI content generation menu - verify channel and subscription first."""
    query = update.callback_query
    if query:
        await query.answer()

    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END
    
    # Verifica subscription e canale
    with with_session(context) as session:
        from .models import Channel, User
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        
        # Check subscription
        subscription = user.subscription_type or "gratis"
        if subscription == "gratis":
            error_text = (
                "🔒 Generatore di Contenuti AI è una feature premium\n\n"
                "✨ Per sbloccare questa feature, passa a un piano premium:\n"
                "💳 Piano Premium: €9.99/mese\n"
                "👑 Piano Pro: €29.99/mese"
            )
            
            keyboard = [
                [InlineKeyboardButton("💳 Upgrade a Premium", callback_data="upgrade:premium")],
                [InlineKeyboardButton("👑 Scopri Piano Pro", callback_data="upgrade:pro")],
                [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:main")],
            ]
            
            if query:
                await query.edit_message_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
            
            return ConversationHandler.END
        
        channels = session.query(Channel).filter_by(user_id=user.id).all()
        
        if not channels:
            # Nessun canale - mostra errore
            error_text = (
                "❌ Non hai canali registrati\n\n"
                "Per usare il Generatore di Contenuti AI, devi prima configurare almeno un canale.\n\n"
                "📌 Cosa fare:\n"
                "1. Vai su 'Impostazioni'\n"
                "2. Aggiungi il tuo bot/canale\n"
                "3. Torna qui e riprova"
            )
            
            keyboard = [[InlineKeyboardButton("◀️ Indietro", callback_data="insideads:main")]]
            
            if query:
                await query.edit_message_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
            
            return ConversationHandler.END
        
        # Salva il canale principale (il primo) in user_data per successivo utilizzo
        context.user_data["ai_channel_id"] = channels[0].id
        context.user_data["ai_channel"] = channels[0]
        context.user_data["user_subscription"] = subscription

    text = (
        "🤖 Generatore di Contenuti AI\n\n"
        "Genera post e annunci con AI:\n"
        "• Ad copy accattivante\n"
        "• Headline professionali\n"
        "• Social media posts\n"
        "• Campagne complete\n"
        "• A/B test variations"
    )

    keyboard = [
        [InlineKeyboardButton("✍️ Genera Post", callback_data="ai:generate_post")],
        [InlineKeyboardButton("📰 Crea Headline", callback_data="ai:generate_headline")],
        [InlineKeyboardButton("🎯 Ad Copy", callback_data="ai:generate_ad")],
        [InlineKeyboardButton("🎨 Campagna Completa", callback_data="ai:generate_campaign")],
        [InlineKeyboardButton("🧪 Test A/B", callback_data="ai:ab_test")],
        [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:main")],
    ]

    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    return SELECT_TONE


async def ai_generate_post_start(update: Update, context: CallbackContext) -> int:
    """Start post generation - skip topic input, auto-detect from channel."""
    query = update.callback_query
    if query:
        await query.answer()

    context.user_data["generation_type"] = "post"
    
    # Estrai topic dal canale configurato
    channel = context.user_data.get("ai_channel")
    if channel and channel.topic:
        context.user_data["ai_topic"] = channel.topic
    else:
        # Fallback: usa il nome del canale o un generico
        channel_name = channel.title if channel else "il tuo canale"
        context.user_data["ai_topic"] = f"Contenuto per {channel_name}"

    text = "🎯 Seleziona il tono del messaggio:\n\n• Professional - Formale e serio\n• Friendly - Cordiale e accogliente\n• Urgent - Fretta e scadenza\n• Playful - Divertente e leggero"

    keyboard = [
        [InlineKeyboardButton("💼 Professional", callback_data="ai:tone_professional")],
        [InlineKeyboardButton("😊 Friendly", callback_data="ai:tone_friendly")],
        [InlineKeyboardButton("⚡ Urgent", callback_data="ai:tone_urgent")],
        [InlineKeyboardButton("😄 Playful", callback_data="ai:tone_playful")],
    ]

    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    return SELECT_TONE




async def ai_tone_selected(update: Update, context: CallbackContext) -> int:
    """Process tone selection and show platform choice."""
    query = update.callback_query
    await query.answer()

    # Extract tone from callback
    tone_map = {
        "ai:tone_professional": ToneType.PROFESSIONAL,
        "ai:tone_friendly": ToneType.FRIENDLY,
        "ai:tone_urgent": ToneType.URGENT,
        "ai:tone_playful": ToneType.PLAYFUL,
    }

    context.user_data["ai_tone"] = tone_map.get(query.data, ToneType.FRIENDLY)

    text = "📱 Dove pubblicherai questo contenuto?\n\n• Instagram - Con hashtags\n• Facebook - Con emoji\n• Telegram - Conciso\n• Twitter - Max 280 caratteri"

    keyboard = [
        [InlineKeyboardButton("📷 Instagram", callback_data="ai:platform_instagram")],
        [InlineKeyboardButton("👍 Facebook", callback_data="ai:platform_facebook")],
        [InlineKeyboardButton("✈️ Telegram", callback_data="ai:platform_telegram")],
        [InlineKeyboardButton("🐦 Twitter", callback_data="ai:platform_twitter")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_PLATFORM


async def ai_generate_content(update: Update, context: CallbackContext) -> int:
    """Generate and display AI content."""
    query = update.callback_query
    await query.answer()

    # Extract platform
    platform_map = {
        "ai:platform_instagram": "instagram",
        "ai:platform_facebook": "facebook",
        "ai:platform_telegram": "telegram",
        "ai:platform_twitter": "twitter",
    }

    platform = platform_map.get(query.data, "instagram")
    topic = context.user_data.get("ai_topic", "il tuo prodotto")
    tone = context.user_data.get("ai_tone", ToneType.FRIENDLY)

    # Generate content
    generator = AIContentGenerator()
    content = generator.generate_ad_copy(topic, tone=tone)
    optimized = generator.optimize_for_platform(content.text, platform)

    # Prepare response
    text = f"""
🤖 Contenuto Generato per {platform.upper()}

📝 Tono: {tone.value}
📌 Argomento: {topic}

─────────────────────
{optimized}
─────────────────────

Variazioni:
"""

    # Add variations
    if content.variations:
        for i, var in enumerate(content.variations, 1):
            text += f"\n{i}. {var}\n"

    keyboard = [
        [InlineKeyboardButton("📋 Copia", callback_data="ai:copy_content")],
        [InlineKeyboardButton("🔄 Rigenera", callback_data="ai:generate_post")],
        [InlineKeyboardButton("🤖 Menu AI", callback_data="ai:menu")],
        [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:main")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


# ============================================================================
# AI CAMPAIGN GENERATION HANDLERS
# ============================================================================

async def aigen_start(update: Update, context: CallbackContext) -> int:
    """Inizia il flusso di generazione campagne con AI."""
    query = update.callback_query
    if query:
        await query.answer()
    
    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END
    
    # Check subscription
    with with_session(context) as session:
        from .models import User
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        
        # Verifica il tipo di subscription
        subscription = user.subscription_type or "gratis"
        
        if subscription == "gratis":
            # Messaggio per utenti gratis
            text = (
                "🔒 Genera Campagna con AI è una feature premium\n\n"
                "Questo strumento analizza il tuo canale/bot e genera campagne personalizzate "
                "usando intelligenza artificiale.\n\n"
                "✨ Per sbloccare questa feature, passa a un piano premium:\n"
                "💳 Piano Premium: €9.99/mese\n"
                "👑 Piano Pro: €29.99/mese\n\n"
                "Contatta @AdsbotSupport per saperne di più sui piani disponibili."
            )
            
            keyboard = [
                [InlineKeyboardButton("💳 Upgrade a Premium", callback_data="upgrade:premium")],
                [InlineKeyboardButton("👑 Scopri Piano Pro", callback_data="upgrade:pro")],
                [InlineKeyboardButton("◀️ Indietro", callback_data="menu:main")],
            ]
            
            if query:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            
            return ConversationHandler.END
        
        # Utente premium o pro - salva il tipo di subscription
        context.user_data["user_subscription"] = subscription
    
    # Procedi con selezione canale
    text = "🎯 Seleziona il canale per il quale generare campagne personalizzate:\n\n"
    
    with with_session(context) as session:
        from .models import Channel
        channels = session.query(Channel).filter_by(user_id=user.id).all()
        
        if not channels:
            text = "❌ Non hai canali registrati. Aggiungine uno prima di continuare."
            if query:
                await query.edit_message_text(text)
            else:
                await update.message.reply_text(text)
            return ConversationHandler.END
        
        # Crea bottoni per ogni canale
        keyboard = []
        for channel in channels:
            button_text = f"@{channel.handle}"
            if channel.title:
                button_text += f" ({channel.title})"
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"aigen:channel:{channel.id}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("❌ Annulla", callback_data="menu:main")
        ])
        
        if query:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    return AIGEN_SELECT_CHANNEL


async def aigen_channel_selected(update: Update, context: CallbackContext) -> int:
    """Canale selezionato - scegli piattaforma e tono."""
    query = update.callback_query
    await query.answer()
    
    # Estrai channel_id dal callback
    channel_id = int(query.data.split(":")[-1])
    context.user_data["aigen_channel_id"] = channel_id
    
    # Salva il canale nel context per successivo utilizzo
    with with_session(context) as session:
        from .models import Channel
        channel = session.query(Channel).filter_by(id=channel_id).first()
        if channel:
            context.user_data["aigen_channel_handle"] = channel.handle
            context.user_data["aigen_channel_title"] = channel.title
            context.user_data["aigen_channel_topic"] = channel.topic
    
    # Scegli piattaforma (valido per PREMIUM e PRO)
    text = (
        "📱 **Scegli la piattaforma** su cui vuoi pubblicare:\n\n"
        "• Telegram - Conciso e diretto\n"
        "• Instagram - Con hashtag e emoji\n"
        "• Facebook - Descrittivo e social\n"
        "• Twitter/X - Max 280 caratteri"
    )
    
    keyboard = [
        [InlineKeyboardButton("📱 Telegram", callback_data="aigen:platform:telegram")],
        [InlineKeyboardButton("📷 Instagram", callback_data="aigen:platform:instagram")],
        [InlineKeyboardButton("👍 Facebook", callback_data="aigen:platform:facebook")],
        [InlineKeyboardButton("🐦 Twitter/X", callback_data="aigen:platform:twitter")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return AIGEN_SELECTING_PLATFORM


async def aigen_platform_selected(update: Update, context: CallbackContext) -> int:
    """Piattaforma selezionata - chiedi tono."""
    query = update.callback_query
    await query.answer()
    
    # Estrai piattaforma dal callback
    platform = query.data.split(":")[-1]
    context.user_data["aigen_platform"] = platform
    
    text = (
        "🎯 **Scegli il tono della campagna:**\n\n"
        "• 💼 Professional - Formale e serio\n"
        "• 😊 Friendly - Cordiale e accogliente\n"
        "• ⚡ Aggressive - Urgente e stimolante\n"
        "• 😄 Playful - Divertente e leggero"
    )
    
    keyboard = [
        [InlineKeyboardButton("💼 Professional", callback_data="aigen:tone:professional")],
        [InlineKeyboardButton("😊 Friendly", callback_data="aigen:tone:friendly")],
        [InlineKeyboardButton("⚡ Aggressive", callback_data="aigen:tone:aggressive")],
        [InlineKeyboardButton("😄 Playful", callback_data="aigen:tone:playful")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return AIGEN_SELECTING_TONE


async def aigen_tone_selected(update: Update, context: CallbackContext) -> int:
    """Tono selezionato - genera campagna con ChatGPT."""
    query = update.callback_query
    await query.answer()
    
    # Estrai tono dal callback
    tone = query.data.split(":")[-1]
    context.user_data["aigen_tone"] = tone
    
    # Mostra messaggio di generazione
    text = "🔍 Analizzando il tuo canale...\n\n⏳ Sto provvedendo a creare la tua campagna personalizzata..."
    await query.edit_message_text(text)
    
    try:
        from .config import Config
        from .chatgpt_integration import ChatGPTCampaignGenerator
        
        config = Config.load()
        gpt_generator = ChatGPTCampaignGenerator(config.openai_api_key)
        
        channel_id = context.user_data.get("aigen_channel_id")
        platform = context.user_data.get("aigen_platform", "telegram")
        tone = context.user_data.get("aigen_tone", "professional")
        
        with with_session(context) as session:
            from .models import Channel
            
            channel = session.query(Channel).filter_by(id=channel_id).first()
            if not channel:
                await query.edit_message_text("❌ Canale non trovato")
                return ConversationHandler.END
            
            # Genera campagna con ChatGPT specifico per piattaforma e tono
            campaign_content = gpt_generator.generate_campaign_for_platform(
                channel=channel,
                platform=platform,
                tone=tone
            )
            
            if campaign_content:
                # Salva il contenuto generato nel context
                context.user_data["aigen_gpt_campaign"] = campaign_content
                
                # Mostra il risultato con testo copiabile
                result_text = (
                    f"✨ **Campagna per {platform.upper()}**\n\n"
                    f"**Tono:** {tone}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{campaign_content.title}\n\n"
                    f"{campaign_content.description}\n\n"
                    f"→ {campaign_content.cta_text}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"👥 **Target:** {campaign_content.target_audience}\n"
                    f"🏷️ **Keywords:** {', '.join(campaign_content.keywords)}"
                )
                
                keyboard = [
                    [InlineKeyboardButton("📋 Copia Campagna", callback_data="aigen:copy_campaign")],
                ]
                
                # Aggiungi il bottone "Crea Campagna" solo per Telegram
                if platform == "telegram":
                    keyboard.append([InlineKeyboardButton("✅ Crea Campagna", callback_data="aigen:create_from_gpt")])
                
                keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="menu:main")])
                
                await query.edit_message_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard))
                return ConversationHandler.END
            else:
                await query.edit_message_text("❌ Errore nella generazione della campagna")
                return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"Error generating campaign: {e}")
        await query.edit_message_text(f"❌ Errore: {str(e)[:100]}")
        return ConversationHandler.END


async def aigen_copy_campaign(update: Update, context: CallbackContext) -> None:
    """Copia la campagna negli appunti."""
    query = update.callback_query
    await query.answer()
    
    campaign_content = context.user_data.get("aigen_gpt_campaign")
    platform = context.user_data.get("aigen_platform", "telegram")
    
    if not campaign_content:
        await query.answer("❌ Campagna non trovata", show_alert=True)
        return
    
    # Crea il testo copiabile
    copyable_text = (
        f"{campaign_content.title}\n\n"
        f"{campaign_content.description}\n\n"
        f"→ {campaign_content.cta_text}"
    )
    
    # Mostra messaggio con testo copiabile
    copy_text = (
        f"✅ **Campagna pronta per {platform.upper()}**\n\n"
        f"📋 **Copia il testo sottostante:**\n\n"
        f"```\n{copyable_text}\n```\n\n"
        f"Usa questo testo direttamente su {platform.upper()}!"
    )
    
    keyboard = []
    
    # Aggiungi bottone "Crea Campagna" solo per Telegram
    if platform == "telegram":
        keyboard.append([InlineKeyboardButton("✅ Crea Campagna nel Bot", callback_data="aigen:create_from_gpt")])
    else:
        # Per altre piattaforme, mostra info sulla pubblicazione
        copy_text += (
            f"\n\n💡 **Vuoi pubblicare automaticamente?**\n"
            f"Possiamo provvedere noi alla pubblicazione tramite un'app dedicata.\n"
            f"Contattaci per i dettagli!"
        )
    
    keyboard.append([InlineKeyboardButton("◀️ Indietro", callback_data="menu:main")])
    
    await query.edit_message_text(copy_text, reply_markup=InlineKeyboardMarkup(keyboard))


async def aigen_create_from_gpt(update: Update, context: CallbackContext) -> int:
    """Crea campagna da ChatGPT."""
    query = update.callback_query
    await query.answer()
    
    user_data = update.effective_user
    campaign_content = context.user_data.get("aigen_gpt_campaign")
    
    if not campaign_content:
        await query.edit_message_text("❌ Errore: campagna non trovata")
        return ConversationHandler.END
    
    try:
        with with_session(context) as session:
            from .models import Campaign, User, Channel
            
            user = ensure_user(
                session,
                telegram_id=user_data.id,
                username=user_data.username,
                first_name=user_data.first_name,
                language_code=user_data.language_code,
            )
            
            channel_id = context.user_data.get("aigen_channel_id")
            channel = session.query(Channel).filter_by(id=channel_id).first() if channel_id else None
            
            # Crea la campagna nel database
            campaign = Campaign(
                user_id=user.id,
                name=campaign_content.title,
                description=campaign_content.description,
                cta_text=campaign_content.cta_text,
                budget=campaign_content.suggested_budget,
                offer_type="auto_generated",
                status="draft",
            )
            
            if channel:
                campaign.channel_id = channel.id
            
            session.add(campaign)
            session.commit()
            
            success_text = (
                f"🎉 **Campagna Creata!**\n\n"
                f"**Titolo:** {campaign_content.title}\n\n"
                f"**Budget:** €{campaign_content.suggested_budget:.2f}\n\n"
                f"La campagna è stata salvata in bozza.\n"
                f"Puoi visualizzarla e modificarla nel tuo pannello campagne."
            )
            
            keyboard = [
                [InlineKeyboardButton("🏠 Menu Principale", callback_data="menu:home")],
                [InlineKeyboardButton("📊 Le Mie Campagne", callback_data="campaign:list")],
            ]
            
            await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard))
            return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"Error creating campaign from GPT: {e}")
        await query.edit_message_text(f"❌ Errore nella creazione: {str(e)[:100]}")
        return ConversationHandler.END


async def aigen_show_campaign_suggestion(
    update: Update,
    context: CallbackContext,
) -> int:
    """Mostra un suggerimento di campagna."""
    query = update.callback_query
    if query:
        await query.answer()
    
    suggestions = context.user_data.get("aigen_suggestions", [])
    index = context.user_data.get("aigen_suggestion_index", 0)
    
    if index >= len(suggestions):
        # Fine dei suggerimenti
        text = "✅ Ho generato tutti i suggerimenti di campagne personalizzate!\n\n"
        text += "Puoi tornare indietro e selezionare un'altra campagna, oppure iniziare a crearle."
        
        keyboard = [
            [InlineKeyboardButton("📊 Rivedi Campagne", callback_data="aigen:review_all")],
            [InlineKeyboardButton("◀️ Torna al menu", callback_data="menu:main")],
        ]
        
        if query:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        
        return ConversationHandler.END
    
    suggestion = suggestions[index]
    analysis = context.user_data.get("aigen_analysis")
    
    # Formatta il messaggio con il suggerimento
    text = f"""
{suggestion.title}

📌 Descrizione:
{suggestion.description}

💰 Budget Consigliato: €{suggestion.recommended_budget:.2f}
📈 Reach Stimato: ~{suggestion.estimated_reach:,.0f} impressioni
💬 Engagement Stimato: ~{suggestion.estimated_engagement:,.0f} interazioni
📊 ROI Atteso: {suggestion.expected_roi:.1f}x

🎯 Focus Contenuto: {suggestion.content_focus}
⏱ Durata: {suggestion.timing.get('duration', 'N/A')}
📱 Frequenza: {suggestion.timing.get('frequency', 'N/A')}

💡 Motivo di questo suggerimento:
{suggestion.reasoning}

📌 Targeting:
• Interessi: {', '.join(suggestion.targeting.get('interests', [])[:3])}
• Comportamento: {suggestion.targeting.get('behavior', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Campagna {index + 1} di {len(suggestions)}
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Crea questa campagna", callback_data=f"aigen:create:{index}")],
        [InlineKeyboardButton("➡️ Prossima campagna", callback_data="aigen:next_suggestion")],
        [InlineKeyboardButton("⬅️ Precedente", callback_data="aigen:prev_suggestion") if index > 0 else None],
        [InlineKeyboardButton("◀️ Annulla", callback_data="menu:main")],
    ]
    
    # Rimuovi bottoni None
    keyboard = [[btn for btn in row if btn] for row in keyboard if any(row)]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    return AIGEN_REVIEW_CAMPAIGNS


async def aigen_next_suggestion(update: Update, context: CallbackContext) -> int:
    """Passa al prossimo suggerimento."""
    index = context.user_data.get("aigen_suggestion_index", 0)
    context.user_data["aigen_suggestion_index"] = index + 1
    
    return await aigen_show_campaign_suggestion(update, context)


async def aigen_prev_suggestion(update: Update, context: CallbackContext) -> int:
    """Torna al precedente suggerimento."""
    index = context.user_data.get("aigen_suggestion_index", 0)
    context.user_data["aigen_suggestion_index"] = max(0, index - 1)
    
    return await aigen_show_campaign_suggestion(update, context)


async def aigen_create_campaign(update: Update, context: CallbackContext) -> int:
    """Crea la campagna selezionata."""
    query = update.callback_query
    await query.answer()
    
    # Estrai l'indice dal callback
    suggestion_index = int(query.data.split(":")[-1])
    suggestions = context.user_data.get("aigen_suggestions", [])
    
    if suggestion_index >= len(suggestions):
        await query.edit_message_text("❌ Campagna non trovata.")
        return ConversationHandler.END
    
    suggestion = suggestions[suggestion_index]
    channel_id = context.user_data.get("aigen_channel_id")
    channel_handle = context.user_data.get("aigen_channel_handle")
    
    try:
        with with_session(context) as session:
            from .models import Campaign
            
            # Crea la campagna nel database
            campaign = Campaign(
                channel_id=channel_id,
                name=suggestion.title,
                budget=suggestion.recommended_budget,
                call_to_action=suggestion.content_focus,
            )
            
            session.add(campaign)
            session.commit()
            
            # Mostra messaggio di successo con opzioni next steps
            text = f"""
✅ Campagna Creata!

📌 {suggestion.title}
📊 Budget: €{suggestion.recommended_budget:.2f}
🎯 Canale: @{channel_handle}

La campagna è stata salvata nel tuo account.

Prossimi passi:
1️⃣ Genera contenuti AI personalizzati
2️⃣ Rivedi e personalizza i testi
3️⃣ Imposta il budget e le date
4️⃣ Avvia la campagna

Cosa vuoi fare ora?
"""
            
            keyboard = [
                [InlineKeyboardButton("🤖 Genera Contenuti", callback_data=f"aigen:generate_content:{campaign.id}")],
                [InlineKeyboardButton("🎨 Personalizza", callback_data=f"aigen:edit:{campaign.id}")],
                [InlineKeyboardButton("➡️ Prossima campagna", callback_data="aigen:next_suggestion")],
                [InlineKeyboardButton("◀️ Torna al menu", callback_data="menu:main")],
            ]
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        await query.edit_message_text(f"❌ Errore nella creazione: {str(e)[:100]}")
    
    return ConversationHandler.END


def build_application(config: Config) -> Application:
    """Configure the bot application and handlers."""

    application = Application.builder().token(config.bot_token).build()
    session_factory = create_session_factory(config)
    application.bot_data["session_factory"] = session_factory

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("insideads", insideads_main_menu))

    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("addchannel", add_channel_entry),
                CallbackQueryHandler(add_channel_entry, pattern=r"^menu:add_channel$"),
            ],
            states={
                ADD_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_channel_save)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )

    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("goal", goal_entry),
                CallbackQueryHandler(goal_entry, pattern=r"^menu:goals$"),
            ],
            states={
                GOAL_CHANNEL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, goal_channel),
                    CallbackQueryHandler(goal_search_channel, pattern=r"^goal:search_channel$"),
                    CallbackQueryHandler(goal_channel_selected, pattern=r"^goal:select_channel:\d+$"),
                    CallbackQueryHandler(goal_channel_selected, pattern=r"^goal:new:\d+$"),
                    CallbackQueryHandler(goal_channel_selected, pattern=r"^goal:edit:\d+$"),
                ],
                GOAL_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, goal_target)],
                GOAL_DEADLINE: [
                    CallbackQueryHandler(goal_skip_deadline, pattern=r"^goal:skip_deadline$"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, goal_deadline)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )

    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("offer", offer_entry),
                CallbackQueryHandler(offer_entry, pattern=r"^menu:offers$"),
            ],
            states={
                OFFER_CHANNEL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, offer_channel),
                    CallbackQueryHandler(offer_search_channel, pattern=r"^offer:search_channel$"),
                    CallbackQueryHandler(offer_channel_selected, pattern=r"^offer:select_channel:\d+$"),
                ],
                OFFER_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, offer_type)],
                OFFER_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, offer_price)],
                OFFER_NOTES: [
                    CallbackQueryHandler(offer_skip_notes, pattern=r"^offer:skip_notes$"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, offer_notes)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )

    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("campaign", campaign_disclaimer),
                CallbackQueryHandler(campaign_disclaimer, pattern=r"^menu:campaign$"),
            ],
            states={
                CAMPAIGN_CHANNEL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, campaign_channel),
                    CallbackQueryHandler(campaign_payment_request, pattern=r"^campaign:proceed$"),
                    CallbackQueryHandler(campaign_search_channel, pattern=r"^campaign:search_channel$"),
                    CallbackQueryHandler(campaign_channel_selected, pattern=r"^campaign:select_channel:\d+$"),
                ],
                CAMPAIGN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, campaign_name)],
                CAMPAIGN_BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, campaign_budget)],
                CAMPAIGN_LOAD_BALANCE: [
                    CallbackQueryHandler(campaign_load_balance, pattern=r"^campaign:load:"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, campaign_load_balance),
                ],
                CAMPAIGN_PRICE: [
                    CallbackQueryHandler(campaign_skip_price, pattern=r"^campaign:skip_price$"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, campaign_price)
                ],
                CAMPAIGN_CTA: [
                    CallbackQueryHandler(campaign_skip_cta, pattern=r"^campaign:skip_cta$"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, campaign_cta)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )

    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("template", template_entry),
                CallbackQueryHandler(template_entry, pattern=r"^menu:template$"),
            ],
            states={
                TEMPLATE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, template_name)],
                TEMPLATE_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, template_content)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )

    application.add_handler(CallbackQueryHandler(stats, pattern=r"^menu:stats$"))
    application.add_handler(CallbackQueryHandler(show_channel_stats, pattern=r"^stats:channel:\d+$"))
    application.add_handler(CallbackQueryHandler(open_menu, pattern=r"^menu:home$"))

    # Inside Ads handlers
    application.add_handler(CallbackQueryHandler(insideads_main_menu, pattern=r"^insideads:main$"))
    application.add_handler(CallbackQueryHandler(insideads_earn_menu, pattern=r"^insideads:earn$"))
    application.add_handler(CallbackQueryHandler(insideads_earn_editor, pattern=r"^insideads:earn:editor$"))
    application.add_handler(CallbackQueryHandler(insideads_buy_menu, pattern=r"^insideads:buy$"))
    application.add_handler(CallbackQueryHandler(insideads_buy_create, pattern=r"^insideads:buy:create$"))
    application.add_handler(CallbackQueryHandler(insideads_buy_list, pattern=r"^insideads:buy:list$"))
    application.add_handler(CallbackQueryHandler(insideads_exchange_menu, pattern=r"^insideads:exchange$"))
    application.add_handler(CallbackQueryHandler(insideads_exchange_metrics, pattern=r"^insideads:exchange:metrics$"))
    application.add_handler(CallbackQueryHandler(insideads_exchange_setup, pattern=r"^insideads:exchange:setup$"))
    application.add_handler(CallbackQueryHandler(insideads_stats_menu, pattern=r"^insideads:stats$"))
    application.add_handler(CallbackQueryHandler(insideads_stats_ads, pattern=r"^insideads:stats:ads$"))
    application.add_handler(CallbackQueryHandler(insideads_stats_monetization, pattern=r"^insideads:stats:monetization$"))
    application.add_handler(CallbackQueryHandler(insideads_account_menu, pattern=r"^insideads:account$"))
    application.add_handler(CallbackQueryHandler(insideads_account_transactions, pattern=r"^insideads:account:transactions$"))
    application.add_handler(CallbackQueryHandler(insideads_account_settings, pattern=r"^insideads:account:settings$"))

    # Advanced campaign handlers
    application.add_handler(CallbackQueryHandler(campaign_management_menu, pattern=r"^campaign:menu$"))
    application.add_handler(CallbackQueryHandler(campaign_create_multi, pattern=r"^campaign:create_multi$"))
    application.add_handler(CallbackQueryHandler(campaign_forecast, pattern=r"^campaign:forecast$"))
    application.add_handler(CallbackQueryHandler(campaign_ai_optimize, pattern=r"^campaign:ai_optimize$"))
    application.add_handler(CallbackQueryHandler(campaign_suggestions, pattern=r"^campaign:suggestions$"))

    # Purchase campaign conversation handler
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CallbackQueryHandler(purchase_campaign_start, pattern=r"^purchase:start$"),
                CallbackQueryHandler(purchase_campaign_start, pattern=r"^insideads:buy:create$"),
            ],
            states={
                SELECT_CAMPAIGN: [
                    CallbackQueryHandler(purchase_campaign_select, pattern=r"^purchase:select_channel:\d+$"),
                ],
                ENTER_AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, purchase_campaign_amount),
                ],
                SELECT_PAYMENT_PROVIDER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, purchase_campaign_provider),
                ],
                CONFIRM_PAYMENT: [
                    CallbackQueryHandler(purchase_campaign_confirm, pattern=r"^purchase:payment:(stripe|paypal)$"),
                ],
            },
            fallbacks=[
                CallbackQueryHandler(insideads_buy_menu, pattern=r"^insideads:buy$"),
                CommandHandler("cancel", cancel),
            ],
        )
    )

    # AI Campaign Generation Handler
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CallbackQueryHandler(aigen_start, pattern=r"^aigen:start$"),
            ],
            states={
                AIGEN_SELECT_CHANNEL: [
                    CallbackQueryHandler(aigen_channel_selected, pattern=r"^aigen:channel:\d+$"),
                ],
                AIGEN_SELECTING_PLATFORM: [
                    CallbackQueryHandler(aigen_platform_selected, pattern=r"^aigen:platform:(telegram|instagram|facebook|twitter)$"),
                ],
                AIGEN_SELECTING_TONE: [
                    CallbackQueryHandler(aigen_tone_selected, pattern=r"^aigen:tone:(professional|friendly|aggressive|playful)$"),
                ],
                AIGEN_REVIEW_CAMPAIGNS: [
                    CallbackQueryHandler(aigen_next_suggestion, pattern=r"^aigen:next_suggestion$"),
                    CallbackQueryHandler(aigen_prev_suggestion, pattern=r"^aigen:prev_suggestion$"),
                    CallbackQueryHandler(aigen_create_campaign, pattern=r"^aigen:create:\d+$"),
                    CallbackQueryHandler(aigen_copy_campaign, pattern=r"^aigen:copy_campaign$"),
                    CallbackQueryHandler(aigen_create_from_gpt, pattern=r"^aigen:create_from_gpt$"),
                ],
            },
            fallbacks=[
                CallbackQueryHandler(open_menu, pattern=r"^menu:main$"),
                CommandHandler("cancel", cancel),
            ],
        )
    )

    # AI Content Generation Handler
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CallbackQueryHandler(generate_post_menu, pattern=r"^ai:menu$"),
                CallbackQueryHandler(ai_generate_post_start, pattern=r"^ai:generate_post$"),
            ],
            states={
                SELECT_TONE: [
                    CallbackQueryHandler(ai_tone_selected, pattern=r"^ai:tone_(professional|friendly|urgent|playful)$"),
                ],
                SELECT_PLATFORM: [
                    CallbackQueryHandler(ai_generate_content, pattern=r"^ai:platform_(instagram|facebook|telegram|twitter)$"),
                ],
            },
            fallbacks=[
                CallbackQueryHandler(generate_post_menu, pattern=r"^ai:menu$"),
                CommandHandler("cancel", cancel),
            ],
        )
    )

    # AI Content Callbacks
    application.add_handler(CallbackQueryHandler(generate_post_menu, pattern=r"^ai:menu$"))
    application.add_handler(CallbackQueryHandler(ai_generate_post_start, pattern=r"^ai:generate_(post|headline|ad|campaign)$"))
    
    # Upgrade/Payment Callbacks
    application.add_handler(CallbackQueryHandler(upgrade_plan_selected, pattern=r"^upgrade:(premium|pro)$"))
    application.add_handler(CallbackQueryHandler(upgrade_paypal, pattern=r"^upgrade:paypal:(premium|pro)$"))
    application.add_handler(CallbackQueryHandler(upgrade_test, pattern=r"^upgrade:test:(premium|pro)$"))
    application.add_handler(CallbackQueryHandler(upgrade_confirmed, pattern=r"^upgrade:confirmed:(premium|pro)$"))

    return application


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    config = Config.load()
    application = build_application(config)
    logger.info("Starting Adsbot...")
    application.run_polling()


if __name__ == "__main__":
    run()
