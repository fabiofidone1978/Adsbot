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
from .analytics import (
    EditorAnalytics,
    AdvertiserAnalytics,
    PlatformAnalytics,
    ReportExporter,
)
from .scheduler import (
    init_scheduler,
    stop_scheduler,
    get_scheduler_status,
)
from .verification import (
    IdentityVerification,
    RiskScorer,
    DisputeResolver,
    AccountSecurity,
)


logger = logging.getLogger(__name__)


async def safe_query_answer(query) -> bool:
    """Safely answer callback query, ignoring old/invalid query errors."""
    if not query:
        return False
    try:
        await query.answer()
        return True
    except Exception:
        # Callback query too old, invalid, or already answered - ignore silently
        return False


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
    # Marketplace Advertiser states
    MARKETPLACE_ORDER_DURATION,
    MARKETPLACE_ORDER_CONTENT,
    MARKETPLACE_ORDER_REVIEW,
    MARKETPLACE_ORDER_CONFIRM,
) = range(34)


# Old menu (kept for backward compatibility)
MENU_BUTTONS = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("Aggiungi canale", callback_data="menu:add_channel"),
            InlineKeyboardButton("Statistiche", callback_data="menu:stats"),
        ],
        [
            InlineKeyboardButton("Offerte ADV", callback_data="menu:offers"),
            InlineKeyboardButton("Campagna", callback_data="menu:campaign"),
        ],
        [
            InlineKeyboardButton("Creazione Campagna AI", callback_data="aigen:start"),
        ],
    ]
)

# Inside Ads main menu
MAIN_MENU_BUTTONS = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("Guadagna", callback_data="insideads:earn")],
        [InlineKeyboardButton("Acquista", callback_data="insideads:buy")],
        [InlineKeyboardButton("Scambio", callback_data="insideads:exchange")],
        [InlineKeyboardButton("Statistiche", callback_data="insideads:stats")],
        [InlineKeyboardButton("Account", callback_data="insideads:account")],
    ]
)

# Earn submenu (Guadagna)
EARN_MENU_BUTTONS = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("Editore", callback_data="insideads:earn:editor")],
        [InlineKeyboardButton("Inserizionista", callback_data="insideads:earn:advertiser")],
        [InlineKeyboardButton("Iscritti gratis", callback_data="insideads:earn:free")],
        [InlineKeyboardButton("Analisi canale", callback_data="insideads:earn:analysis")],
        [InlineKeyboardButton("Indietro", callback_data="insideads:main")],
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
        "Benvenuto su AdsBot - Marketplace ADV Telegram\n"
        "Crea campagne, monetizza il tuo canale, vendi spazi pubblicitari."
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
    await safe_query_answer(query)
    
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


def _format_payment_type(payment_type: str) -> str:
    """Convert payment type to human-readable format."""
    payment_types = {
        "per_clic": "Per Clic (CPC)",
        "per_iscritto": "Per Iscritto (CPA)",
        "massimo": "Budget Massimo"
    }
    return payment_types.get(payment_type, payment_type)


async def offer_gratis_disclaimer(update: Update, context: CallbackContext) -> int:
    """Show disclaimer about Offerte ADV for gratis users - explain services without granting access."""
    
    query = update.callback_query
    if query:
        await query.answer()
    
    text = (
        "Servizio Pubblicitario - Campagne ADV\n\n"
        "Creiamo e pubblichiamo le tue campagne pubblicitarie su gruppi Telegram da 1000 a 20000 utenti.\n\n"
        "Cosa Include il Servizio:\n"
        "  • Creazione della campagna personalizzata\n"
        "  • Generazione AI di creatività (titoli, descrizioni, immagini)\n"
        "  • Pubblicazione automatica su gruppi Telegram (1K-20K utenti)\n"
        "  • Reportistica dettagliata delle performance\n\n"
        "Modelli di Pagamento:\n"
        "  • CPC - Paghi per click ricevuti\n"
        "  • CPA - Paghi per conversioni/iscrizioni\n"
        "  • Budget Massimo - Paghi un importo fisso\n\n"
        "Tracciamento in Tempo Reale:\n"
        "  • Visualizza performance della campagna\n"
        "  • Controlla il budget utilizzato\n"
        "  • Metriche dettagliate per ottimizzare\n\n"
        "Questa funzione richiede PREMIUM\n\n"
        "Fai upgrade a Premium per lanciare la tua campagna pubblicitaria!"
    )
    
    keyboard = [
        [InlineKeyboardButton("Upgrade a Premium", callback_data="menu:upgrade")],
        [InlineKeyboardButton("Torna al menu", callback_data="menu:home")],
    ]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    return ConversationHandler.END


async def offer_entry(update: Update, context: CallbackContext) -> int:
    """Begin an offer conversation - show subscription check or channel selection menu."""

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
        subscription_type = user.subscription_type
        from .models import Channel
        channels = session.query(Channel).filter_by(user_id=user.id).all()

    # Check if user is gratis - show disclaimer instead
    if subscription_type == "gratis":
        return await offer_gratis_disclaimer(update, context)

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
    
    # Avvia il nuovo flusso con tipo di pagamento
    await offer_payment_type(update, context)
    return "OFFER_PAYMENT_TYPE"


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


async def offer_payment_type(update: Update, context: CallbackContext) -> int:
    """Select payment type for the advertising campaign."""
    query = update.callback_query
    if query:
        await query.answer()
    
    text = (
        "💳 **Modello per la Campagna**\n\n"
        "cosa desideri dalla tua campagna:\n\n"
        "1️⃣  **Per Clic (CPC)**\n"
        "   Aumenta il numero di click\n\n"
        "2️⃣  **Per Iscritto (CPA)**\n"
        "   aumenta il numero dei tuoi iscritti\n\n"
        "Scrivi: 1 oppure 2"
    )
    
    if query:
        await query.edit_message_text(text)
    else:
        await update.message.reply_text(text)
    
    return "OFFER_PAYMENT_TYPE"


async def offer_payment_type_selected(update: Update, context: CallbackContext) -> int:
    """Handle payment type selection."""
    choice = update.message.text.strip()
    
    # Mapping da numero a tipo di pagamento
    payment_types = {
        "1": "per_clic",
        "2": "per_iscritto"
    }
    
    if choice not in payment_types:
        await update.message.reply_text(
            "❌ Scelta non valida. Scrivi: 1 oppure 2"
        )
        return "OFFER_PAYMENT_TYPE"
    
    payment_type = payment_types[choice]
    context.user_data["offer_payment_type"] = payment_type
    
    # Mostra form di pagamento
    keyboard = [
        [InlineKeyboardButton("💳 Paga ora", callback_data="offer:payment:proceed")],
        [InlineKeyboardButton("❌ Annulla", callback_data="menu:home")],
    ]
    
    await update.message.reply_text(
        "💳 **Pagamento Richiesto**\n\n"
        "Procedi al pagamento per creare e pubblicare la tua campagna.\n"
        "(In produzione: integrazione PayPal/Stripe)\n\n"
        "Nota: Applichiamo una commissione del 10% sui servizi di creazione e pubblicazione."
    )
    if update.message:
        await update.message.reply_text(
            "Seleziona un'opzione:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    return "OFFER_PAYMENT"


async def offer_payment(update: Update, context: CallbackContext) -> int:
    """Handle payment processing."""
    query = update.callback_query
    if not query:
        return "OFFER_PAYMENT"
    
    await query.answer()
    
    if query.data == "offer:payment:proceed":
        # Simula il pagamento (in produzione: PayPal/Stripe)
        # Per ora, mostriamo un form per inserire l'importo
        await query.edit_message_text(
            "💰 **Investimento nella Campagna**\n\n"
            "Quanto vuoi investire nella tua campagna? (es: 100.00)\n\n"
            "Nota: Applichiamo una commissione del 10% sui servizi di creazione e pubblicazione."
        )
        return "OFFER_DEPOSIT"
    
    return "OFFER_PAYMENT"


async def offer_deposit(update: Update, context: CallbackContext) -> int:
    """Handle deposit amount input - manages MINIMUM PRICE with arrows, calculates total deposit.
    
    The user sees and manipulates the MINIMUM PRICE (prezzo_minimo).
    The total deposit is calculated as: deposit = prezzo_minimo / 0.8
    """
    
    # Initialize minimum price (starting point €0.10)
    if "offer_minimum_price" not in context.user_data:
        context.user_data["offer_minimum_price"] = 0.10
    
    query = update.callback_query
    
    # Handle callback from arrow buttons
    if query:
        await query.answer()
        current_min_price = context.user_data["offer_minimum_price"]
        
        if query.data == "offer:deposit:increase":
            # Increase minimum price by €0.10
            context.user_data["offer_minimum_price"] = round(current_min_price + 0.10, 2)
        elif query.data == "offer:deposit:decrease":
            # Decrease minimum price by €0.10 (minimum €0.10)
            if current_min_price > 0.10:
                context.user_data["offer_minimum_price"] = round(current_min_price - 0.10, 2)
        elif query.data == "offer:deposit:confirm":
            # Confirm the minimum price and calculate total deposit
            min_price = context.user_data["offer_minimum_price"]
            # Total deposit = min_price / 0.8 (since min_price = deposit * 0.8)
            final_deposit = min_price / 0.8
            context.user_data["offer_deposit"] = final_deposit
            context.user_data["offer_minimum_price_chosen"] = min_price
            
            commission = final_deposit * 0.10
            budget_after_commission = final_deposit - commission
            
            context.user_data["offer_budget_available"] = budget_after_commission
            
            await query.edit_message_text(
                f"✅ **Investimento Confermato**\n\n"
                f"Prezzo Minimo Scelto: €{min_price:.2f}\n"
                f"Investimento totale: €{final_deposit:.2f}\n"
                f"Commissione (10%): €{commission:.2f}\n"
                f"Budget per la campagna: €{budget_after_commission:.2f}\n\n"
                f"Procederemo con la pubblicazione della tua campagna."
            )
            
            # Auto-proceed to interaction price after 2 seconds
            import asyncio
            await asyncio.sleep(2)
            
            context.user_data["offer_weekly_budget"] = budget_after_commission
            
            # Initialize interaction price
            if "offer_interaction_price_current" not in context.user_data:
                context.user_data["offer_interaction_price_current"] = 0.10
            
            # Show interactive form with arrows
            budget_available = budget_after_commission
            current_price = context.user_data["offer_interaction_price_current"]
            
            # Calculate offers based on current price
            min_offer = current_price * 0.8
            avg_offer = current_price * 1.0
            max_offer = budget_available
            
            keyboard = [
                [InlineKeyboardButton("⬆️", callback_data="offer:interaction:increase")],
                [InlineKeyboardButton(f"€{min_offer:.2f}", 
                                     callback_data="offer:interaction:dummy")],
                [InlineKeyboardButton("⬇️", callback_data="offer:interaction:decrease")],
                [InlineKeyboardButton("✅ Conferma", callback_data="offer:interaction:confirm")],
            ]
            
            text = (
                "🤖 **Prezzo di Interazione**\n\n"
                f"Prezzo attuale: €{current_price:.2f}\n"
                f"Budget disponibile: €{budget_available:.2f}\n\n"
                "Usa le frecce per regolare il prezzo o scrivi direttamente il valore\n"
                f"(Minimo: €0.10, Massimo: €{budget_available:.2f})\n\n"
                "📊 **Offerte Calcolate:**\n"
                f"• Offerta minima: €{min_offer:.2f}\n"
                f"• Prezzo medio ora: €{avg_offer:.2f}\n"
                f"• Offerta massima: €{max_offer:.2f}\n"
                f"  ⚠️ Scegliendo questa opzione il tuo budget verrà terminato\n\n"
                "Quando sei soddisfatto, clicca ✅ Conferma"
            )
            
            await update.effective_message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            return "OFFER_INTERACTION_PRICE"
        
        # Show updated form with current minimum price
        current_min_price = context.user_data["offer_minimum_price"]
        
        keyboard = [
            [InlineKeyboardButton("⬆️", callback_data="offer:deposit:increase")],
            [InlineKeyboardButton(f"€{current_min_price:.2f}", 
                                 callback_data="offer:deposit:dummy")],
            [InlineKeyboardButton("⬇️", callback_data="offer:deposit:decrease")],
            [InlineKeyboardButton("✅ Conferma", callback_data="offer:deposit:confirm")],
        ]
        
        # Calculate total deposit from minimum price
        total_deposit = current_min_price / 0.8
        commission = total_deposit * 0.10
        budget_available = total_deposit - commission
        
        text = (
            "💰 **Investimento nella Campagna**\n\n"
            f"Prezzo Minimo: €{current_min_price:.2f}\n"
            f"Investimento totale: €{total_deposit:.2f}\n"
            f"Commissione (10%): €{commission:.2f}\n"
            f"Budget per la campagna: €{budget_available:.2f}\n\n"
            "Usa le frecce per regolare il prezzo minimo\n"
            "(Minimo: €0.10)\n\n"
            "Quando sei soddisfatto, clicca ✅ Conferma"
        )
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return "OFFER_DEPOSIT"
    
    # Handle text input (user types amount manually)
    try:
        min_price = float(update.message.text.strip())
        if min_price < 0.10:
            raise ValueError("Prezzo minimo deve essere 0.10")
    except ValueError:
        await update.message.reply_text("❌ Inserisci un numero valido (es: 5.00, minimo €0.10)")
        return "OFFER_DEPOSIT"
    
    # Set the minimum price
    context.user_data["offer_minimum_price"] = min_price
    
    # Calculate total deposit from minimum price
    total_deposit = min_price / 0.8
    commission = total_deposit * 0.10
    budget_available = total_deposit - commission
    
    # Show form with arrows to adjust minimum price
    keyboard = [
        [InlineKeyboardButton("⬆️", callback_data="offer:deposit:increase")],
        [InlineKeyboardButton(f"€{min_price:.2f}", 
                             callback_data="offer:deposit:dummy")],
        [InlineKeyboardButton("⬇️", callback_data="offer:deposit:decrease")],
        [InlineKeyboardButton("✅ Conferma", callback_data="offer:deposit:confirm")],
    ]
    
    text = (
        "💰 **Investimento nella Campagna**\n\n"
        f"Prezzo Minimo: €{min_price:.2f}\n"
        f"Investimento totale: €{total_deposit:.2f}\n"
        f"Commissione (10%): €{commission:.2f}\n"
        f"Budget per la campagna: €{budget_available:.2f}\n\n"
        "Usa le frecce per regolare il prezzo minimo o scrivi direttamente il valore\n"
        "(Minimo: €0.10)\n\n"
        "Quando sei soddisfatto, clicca ✅ Conferma"
    )
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return "OFFER_DEPOSIT"


async def offer_interaction_price(update: Update, context: CallbackContext) -> int:
    """Handle interaction price input - direct text input with validation."""
    # Inizializza il prezzo se non esiste
    if "offer_interaction_price_current" not in context.user_data:
        context.user_data["offer_interaction_price_current"] = 0.10
    
    query = update.callback_query
    budget_available = context.user_data.get("offer_budget_available", 0)
    
    # Gestisci input di testo (numero scritto manualmente)
    if update.message and not query:
        try:
            price = float(update.message.text.strip())
            
            if price < 0.10:
                await update.message.reply_text("❌ Prezzo minimo: €0.10")
                return "OFFER_INTERACTION_PRICE"
            if price > budget_available:
                await update.message.reply_text(f"❌ Prezzo massimo: €{budget_available:.2f}")
                return "OFFER_INTERACTION_PRICE"
        except ValueError:
            await update.message.reply_text("❌ Inserisci un numero valido (es: 0.50)")
            return "OFFER_INTERACTION_PRICE"
        
        # Imposta il nuovo prezzo e mostra il form aggiornato
        context.user_data["offer_interaction_price_current"] = price
        query = None  # Continua per mostrare il form aggiornato
    
    if query:
        await query.answer()
        
        if query.data == "offer:interaction:confirm":
            # Conferma il prezzo
            final_price = context.user_data["offer_interaction_price_current"]
            context.user_data["offer_interaction_price"] = final_price
            
            # Calcola offerta minima, media, massima
            budget = context.user_data.get("offer_budget_available", 0)
            min_offer = final_price * 0.8
            avg_offer = final_price * 1.0
            max_offer = budget
            
            context.user_data["offer_min"] = min_offer
            context.user_data["offer_avg"] = avg_offer
            context.user_data["offer_max"] = max_offer
            context.user_data["offer_languages"] = "it"  # Solo italiano
            
            # Salva l'offerta nel database
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
                
                # Crea l'offerta con tutti i nuovi campi
                offer = add_offer(
                    session,
                    channel,
                    context.user_data.get("offer_type", OfferType.post),  # default type
                    context.user_data.get("offer_price", context.user_data.get("offer_deposit", 0)),
                    notes=None,
                )
                
                # Aggiorna i campi aggiuntivi
                offer.payment_type = context.user_data["offer_payment_type"]
                offer.weekly_budget = context.user_data.get("offer_deposit", 0)
                offer.interaction_price = final_price
                offer.target_languages = "it"  # Solo italiano
                offer.min_offer = min_offer
                offer.max_offer = max_offer
                offer.minimum_price_chosen = min_offer  # Salva il prezzo minimo scelto
                offer.remaining_budget = budget  # Inizializza il budget rimanente
                
                session.commit()

            success_text = (
                "✅ **Campagna Pubblicata!**\n\n"
                f"📱 Canale Target: {context.user_data['offer_channel']}\n"
                f"💳 Modello Pagamento: {_format_payment_type(context.user_data['offer_payment_type'])}\n"
                f"💰 Investimento Totale: €{context.user_data.get('offer_deposit', 0):.2f}\n"
                f"🔖 Prezzo per Interazione: €{final_price:.2f}\n"
                f"💸 Costo per Post: €{min_offer:.2f}\n"
                f"🌍 Mercato: Italia 🇮🇹\n\n"
                "📊 **Stima Offerte:**\n"
                f"• Minima: €{min_offer:.2f}\n"
                f"• Media: €{avg_offer:.2f}\n"
                f"• Massima: €{max_offer:.2f}\n\n"
                "🤖 La tua campagna sarà generata automaticamente con creatività AI!\n"
                "👀 Monitora performance nelle statistiche."
            )
            
            await query.edit_message_text(success_text, reply_markup=MENU_BUTTONS)
            return ConversationHandler.END
    
    # Mostra il form semplice con input diretto
    current_price = context.user_data["offer_interaction_price_current"]
    budget_available = context.user_data.get("offer_budget_available", 0)
    
    # Calcola le offerte in base al prezzo attuale
    min_offer = current_price * 0.8
    avg_offer = current_price * 1.0
    max_offer = budget_available
    
    keyboard = [
        [InlineKeyboardButton("✅ Conferma", callback_data="offer:interaction:confirm")],
    ]
    
    text = (
        "🤖 **Prezzo di Interazione**\n\n"
        f"Prezzo attuale: €{current_price:.2f}\n"
        f"Budget disponibile: €{budget_available:.2f}\n\n"
        "Scrivi il nuovo prezzo (es: 0.50)\n"
        f"Intervallo: €0.10 - €{budget_available:.2f}\n\n"
        "📊 **Offerte Calcolate:**\n"
        f"• Offerta minima: €{min_offer:.2f}\n"
        f"• Prezzo medio ora: €{avg_offer:.2f}\n"
        f"• Offerta massima: €{max_offer:.2f}\n"
        f"  ⚠️ Scegliendo questa opzione il tuo budget verrà terminato\n\n"
        "Quando sei soddisfatto, clicca ✅ Conferma"
    )
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    return "OFFER_INTERACTION_PRICE"


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
    
    plan = "premium"  # Unico piano disponibile
    plan_name = "Premium"
    
    context.user_data["upgrade_plan"] = plan
    context.user_data["upgrade_plan_name"] = plan_name
    
    # Mostra il form di pagamento
    payment_text = (
        "👑 **Piano Premium - Accesso Completo**\n\n"
        "✅ Genera Campagne Personalizzate con AI\n"
        "✅ Generatore Contenuti AI\n"
        "✅ Gestione Offerte Pubblicitarie\n"
        "✅ Statistiche Avanzate\n"
        "✅ Supporto Prioritario\n\n"
        "💰 **Importo: A tua scelta (minimo €10)\n"
        "📊 Commissione: 10% trattenuta per i nostri servizi**\n\n"
        "Es: Versi €100 → Tu ricevi €90 (10% = €10 ai nostri servizi)\n\n"
        "💳 **Procedi al pagamento:**"
    )
    
    keyboard = [
        [InlineKeyboardButton("💳 Inserisci Importo", callback_data="upgrade:enter_amount")],
        [InlineKeyboardButton("🧪 Test (€0.00)", callback_data="upgrade:test:premium")],
        [InlineKeyboardButton("◀️ Indietro", callback_data="menu:campaign")],
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
        f"✅ Upgrade Completato!\n\n"
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
        "👑 **Accesso Premium Richiesto**\n\n"
        "La creazione di campagne personalizzate con AI richiede l'accesso Premium.\n\n"
        "**Piano Premium - Accesso Completo**\n"
        "✅ Genera Campagne Personalizzate con AI\n"
        "✅ Generatore Contenuti AI\n"
        "✅ Gestione Offerte Pubblicitarie\n"
        "✅ Statistiche Avanzate\n\n"
        "💰 **Versamento Una Tantum**\n"
        "📊 Commissione: 10% trattenuta per i nostri servizi\n\n"
        "Scegli l'importo per procedere:"
    )
    
    keyboard = [
        [InlineKeyboardButton("💳 Versare Importo", callback_data="upgrade:premium")],
        [InlineKeyboardButton("🧪 Test (€0.00)", callback_data="upgrade:test:premium")],
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
        
        # Check subscription
        subscription = user.subscription_type or "gratis"
        if subscription == "gratis":
            error_text = (
                "🔒 **Creazione Campagne è esclusivo per Premium**\n\n"
                "Questo servizio ti permette di creare e gestire campagne pubblicitarie.\n\n"
                "👑 **Piano Premium - Accesso Completo**\n"
                "✅ Crea Campagne Personalizzate\n"
                "✅ Genera Campagne con AI\n"
                "✅ Generatore Contenuti AI\n"
                "✅ Gestione Offerte Pubblicitarie\n\n"
                "💰 **Versamento Una Tantum (A tua scelta)**\n"
                "📊 Commissione: 10% per i nostri servizi"
            )
            
            keyboard = [
                [InlineKeyboardButton("💳 Versare Importo per Premium", callback_data="upgrade:premium")],
                [InlineKeyboardButton("◀️ Indietro", callback_data="menu:main")],
            ]
            
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
            
            return ConversationHandler.END
        
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
        await query.edit_message_text("Menu Principale - AdsBot Marketplace", reply_markup=MAIN_MENU_BUTTONS)
    else:
        await update.message.reply_text("Menu Principale - AdsBot Marketplace", reply_markup=MAIN_MENU_BUTTONS)


async def insideads_earn_menu(update: Update, context: CallbackContext) -> None:
    """Show Earn (Guadagna) submenu."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "💰 Guadagna - Scegli come monetizzare il tuo canale:",
            reply_markup=EARN_MENU_BUTTONS,
        )


async def marketplace_editor_menu(update: Update, context: CallbackContext) -> None:
    """Editor marketplace menu - choose to add channel or view marketplace."""
    query = update.callback_query
    user_data = update.effective_user
    if not user_data:
        return
    
    if query:
        await query.answer()
    
    text = (
        "🏪 **Marketplace Editore**\n\n"
        "Monetizza il tuo canale Telegram!\n\n"
        "Registra il tuo canale nel marketplace e guadagna quando gli inserzionisti comprano spazi pubblicitari nel tuo canale."
    )
    
    keyboard = [
        [InlineKeyboardButton("➕ Registra Canale", callback_data="marketplace:editor:register_channel")],
        [InlineKeyboardButton("📊 I Miei Canali", callback_data="marketplace:editor:my_channels")],
        [InlineKeyboardButton("📬 Ordini in Sospeso", callback_data="marketplace:editor:incoming_orders")],
        [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:earn")],
    ]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def marketplace_editor_register_channel(update: Update, context: CallbackContext) -> None:
    """Editor selects channel to register in marketplace."""
    query = update.callback_query
    user_data = update.effective_user
    if not query or not user_data:
        return
    
    await query.answer()
    
    with with_session(context) as session:
        from .models import Channel, ChannelListing
        
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        
        # Get channels not yet in marketplace
        admin_channels = session.query(Channel).filter_by(user_id=user.id).all()
        registered_channel_ids = session.query(ChannelListing.channel_id).all()
        registered_ids = {r[0] for r in registered_channel_ids}
        
        unregistered = [c for c in admin_channels if c.id not in registered_ids]
        
        if not unregistered:
            text = (
                "📝 Registra Canale\n\n"
                "❌ Tutti i tuoi canali sono già nel marketplace, oppure non hai canali.\n\n"
                "Aggiungi un nuovo canale per metterlo in vendita."
            )
            keyboard = [
                [InlineKeyboardButton("➕ Aggiungi Canale", callback_data="menu:add_channel")],
                [InlineKeyboardButton("◀️ Indietro", callback_data="marketplace:editor:menu")],
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        # Show unregistered channels
        text = "📝 **Seleziona Canale da Registrare**\n\n"
        keyboard = []
        
        for channel in unregistered[:10]:
            text += f"• {channel.title or f'@{channel.handle}'}\n"
            keyboard.append([InlineKeyboardButton(
                f"Registra {channel.title or f'@{channel.handle}'}",
                callback_data=f"marketplace:editor:set_price:{channel.id}"
            )])
        
        keyboard.append([InlineKeyboardButton("◀️ Indietro", callback_data="marketplace:editor:menu")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def marketplace_editor_set_price(update: Update, context: CallbackContext) -> None:
    """Editor sets price for channel - bot suggests price based on subscriber count."""
    query = update.callback_query
    user_data = update.effective_user
    if not query or not user_data:
        return
    
    await query.answer()
    
    # Extract channel_id
    try:
        channel_id = int(query.data.split(":")[3])
    except (IndexError, ValueError):
        await query.answer("❌ Errore", show_alert=True)
        return
    
    with with_session(context) as session:
        from .models import Channel, ChannelListing
        
        channel = session.query(Channel).filter_by(
            id=channel_id,
            user_id=user_data.id
        ).first()
        
        if not channel:
            await query.edit_message_text("❌ Canale non trovato")
            return
        
        # Try to get reach from Telegram API
        try:
            chat = await context.bot.get_chat(chat_id=channel.telegram_id)
            subscribers = chat.get_member_count() if hasattr(chat, 'get_member_count') else 0
            reach_24h = max(subscribers // 5, 100)  # Stima: 20% degli iscritti in 24h
        except:
            subscribers = 0
            reach_24h = 100
        
        # Calculate suggested price (based on reach)
        # Formula: €0.0005 per reach punto
        suggested_price = max(reach_24h * 0.0005, 0.50)  # Minimo €0.50
        
        channel_name = channel.title or f"@{channel.handle}"
        
        text = (
            f"💰 **Imposta Prezzo - {channel_name}**\n\n"
            f"📊 **Dati Canale:**\n"
            f"• Iscritti: {subscribers}\n"
            f"• Reach 24h (stimata): {reach_24h}\n\n"
            f"💡 **Prezzo Suggerito:** €{suggested_price:.2f} per post\n\n"
            f"Scrivi il prezzo che vuoi (es: 2.50, minimo €0.50):"
        )
        
        # Save channel_id for next step
        context.user_data["marketplace_channel_id"] = channel_id
        context.user_data["marketplace_suggested_price"] = suggested_price
        
        keyboard = [
            [InlineKeyboardButton(f"✅ Accetta €{suggested_price:.2f}", callback_data=f"marketplace:editor:confirm_price:{channel_id}:{suggested_price:.2f}")],
            [InlineKeyboardButton("✏️ Scrivi Prezzo Personalizzato", callback_data="marketplace:editor:custom_price")],
            [InlineKeyboardButton("◀️ Indietro", callback_data="marketplace:editor:register_channel")],
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def marketplace_editor_confirm_price(update: Update, context: CallbackContext) -> None:
    """Editor confirms price and channel goes live in marketplace."""
    query = update.callback_query
    user_data = update.effective_user
    if not query or not user_data:
        return
    
    await query.answer()
    
    # Extract channel_id and price
    try:
        parts = query.data.split(":")
        channel_id = int(parts[3])
        price = float(parts[4])
    except (IndexError, ValueError):
        await query.answer("❌ Errore", show_alert=True)
        return
    
    with with_session(context) as session:
        from .models import Channel, ChannelListing
        from datetime import datetime
        
        channel = session.query(Channel).filter_by(
            id=channel_id,
            user_id=user_data.id
        ).first()
        
        if not channel:
            await query.edit_message_text("❌ Canale non trovato")
            return
        
        # Get channel data
        try:
            chat = await context.bot.get_chat(chat_id=channel.telegram_id)
            subscribers = chat.get_member_count() if hasattr(chat, 'get_member_count') else 0
        except:
            subscribers = 0
        
        # Create listing
        listing = ChannelListing(
            channel_id=channel_id,
            user_id=user_data.id,
            price=price,
            subscribers=subscribers,
            reach_24h=max(subscribers // 5, 100),
            quality_score=0.7,  # Default quality
            is_active=True,
            is_available=True
        )
        
        session.add(listing)
        session.commit()
        
        channel_name = channel.title or f"@{channel.handle}"
        
        text = (
            f"✅ **Canale Registrato nel Marketplace!**\n\n"
            f"📱 **Canale:** {channel_name}\n"
            f"💰 **Prezzo:** €{price:.2f} per post\n"
            f"📊 **Iscritti:** {subscribers}\n\n"
            f"🎯 Il tuo canale è ora visibile agli inserzionisti!\n\n"
            f"Quando un inserzionista compra uno spazio nel tuo canale, riceverai una notifica e potrai pubblica il post."
        )
        
        keyboard = [
            [InlineKeyboardButton("📊 I Miei Canali", callback_data="marketplace:editor:my_channels")],
            [InlineKeyboardButton("🏪 Torna Marketplace", callback_data="marketplace:editor:menu")],
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def marketplace_editor_my_channels(update: Update, context: CallbackContext) -> None:
    """Show editor their registered channels with current status."""
    query = update.callback_query
    user_data = update.effective_user
    if not query or not user_data:
        return
    
    await query.answer()
    
    with with_session(context) as session:
        from .models import ChannelListing
        
        listings = session.query(ChannelListing).filter_by(user_id=user_data.id).all()
        
        if not listings:
            text = (
                "📊 I Miei Canali\n\n"
                "❌ Non hai canali registrati nel marketplace.\n\n"
                "Registrane uno per iniziare a guadagnare!"
            )
            keyboard = [
                [InlineKeyboardButton("➕ Registra Canale", callback_data="marketplace:editor:register_channel")],
                [InlineKeyboardButton("◀️ Indietro", callback_data="marketplace:editor:menu")],
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        text = "📊 **I Miei Canali nel Marketplace**\n\n"
        keyboard = []
        
        for listing in listings:
            status = "🟢 Disponibile" if listing.is_available else "🔴 In transazione"
            text += (
                f"• {listing.channel.title or f'@{listing.channel.handle}'}\n"
                f"  💰 Prezzo: €{listing.price:.2f}\n"
                f"  👥 Iscritti: {listing.subscribers}\n"
                f"  {status}\n\n"
            )
        
        keyboard.append([InlineKeyboardButton("◀️ Indietro", callback_data="marketplace:editor:menu")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def marketplace_editor_pending_orders(update: Update, context: CallbackContext) -> None:
    """Show editor orders waiting for confirmation."""
    query = update.callback_query
    user_data = update.effective_user
    if not query or not user_data:
        return
    
    await query.answer()
    
    with with_session(context) as session:
        from .models import MarketplaceOrder, OrderStatus
        
        pending = session.query(MarketplaceOrder).filter(
            MarketplaceOrder.seller_id == user_data.id,
            MarketplaceOrder.status == OrderStatus.pending
        ).all()
        
        if not pending:
            text = (
                "⏳ **Ordini in Attesa**\n\n"
                "✅ Non hai ordini in attesa.\n\n"
                "Quando un inserzionista compra uno spazio nel tuo canale, lo vedrai qui."
            )
            keyboard = [
                [InlineKeyboardButton("◀️ Indietro", callback_data="marketplace:editor:menu")],
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        text = "⏳ **Ordini in Attesa di Conferma**\n\n"
        keyboard = []
        
        for order in pending[:10]:
            payment_model = "CPC" if order.channel_listing_id else "Fisso"
            text += (
                f"📋 Ordine #{order.id}\n"
                f"💰 Prezzo: €{order.price:.2f}\n"
                f"⏱️ Durata: {order.duration_hours}h\n"
                f"📝 Tipo: {payment_model}\n\n"
            )
            keyboard.append([InlineKeyboardButton(
                f"Dettagli Ordine #{order.id}",
                callback_data=f"marketplace:editor:confirm_order:{order.id}"
            )])
        
        keyboard.append([InlineKeyboardButton("◀️ Indietro", callback_data="marketplace:editor:menu")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def insideads_earn_editor(update: Update, context: CallbackContext) -> None:
    """Editore - Monetizza il contenuto - MARKETPLACE."""
    await marketplace_editor_menu(update, context)


async def offer_editor_view(update: Update, context: CallbackContext) -> None:
    """Show offer details to editor - NO investment amount shown."""
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    # Extract offer ID from callback_data
    try:
        offer_id = int(query.data.split(":")[3])
    except (IndexError, ValueError):
        await query.answer("❌ Errore", show_alert=True)
        return
    
    with with_session(context) as session:
        from .models import PromoOffer
        offer = session.query(PromoOffer).filter_by(id=offer_id).first()
        
        if not offer:
            await query.edit_message_text("❌ Offerta non trovata")
            return
        
        # Show offer details WITHOUT investment amount
        payment_type = "Per Clic (CPC)" if offer.payment_type == "per_clic" else "Per Iscritto (CPA)"
        
        text = (
            f"💼 **Dettagli Offerta #{offer.id}**\n\n"
            f"📊 **Modello di Pagamento:** {payment_type}\n"
            f"💰 **Costo per Interazione:** €{offer.interaction_price:.2f}\n"
            f"🎯 **Lingue Target:** {offer.target_languages}\n"
            f"📱 **Tipo:** Post/Story\n\n"
            f"📈 **Stima Guadagni:**\n"
            f"• Minimo: €{offer.min_offer:.2f}\n"
            f"• Medio: €{offer.interaction_price:.2f}\n"
            f"• Massimo: €{offer.max_offer:.2f}\n\n"
            "✅ Clicca 'Accetta' per iniziare a pubblicare questa campagna"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Accetta", callback_data=f"offer:editor:accept:{offer_id}")],
            [InlineKeyboardButton("◀️ Torna alle offerte", callback_data="insideads:earn:editor")],
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def offer_editor_accept(update: Update, context: CallbackContext) -> None:
    """Editor accepts an offer - shows available posts to publish."""
    query = update.callback_query
    user_data = update.effective_user
    if not query or not user_data:
        return
    
    await query.answer()
    
    # Extract offer ID
    try:
        offer_id = int(query.data.split(":")[3])
    except (IndexError, ValueError):
        await query.answer("❌ Errore", show_alert=True)
        return
    
    with with_session(context) as session:
        from .models import PromoOffer, Channel, OfferChannel
        from sqlalchemy import and_
        
        # Get the offer
        offer = session.query(PromoOffer).filter_by(id=offer_id).first()
        if not offer:
            await query.edit_message_text("❌ Offerta non trovata")
            return
        
        # Get user's channels where they are admin
        admin_channels = session.query(Channel).filter_by(user_id=user_data.id).all()
        
        if not admin_channels:
            await query.edit_message_text(
                "❌ Errore: Non hai canali amministrati.\n\n"
                "Aggiungi un canale prima di accettare offerte."
            )
            return
        
        # Ask editor which channel to use
        text = (
            f"💼 **Accetta Offerta #{offer.id}**\n\n"
            "📱 **Seleziona il canale dove pubblicare gli annunci:**\n\n"
        )
        
        keyboard = []
        for idx, channel in enumerate(admin_channels[:10], 1):
            channel_name = channel.title or f"@{channel.handle}"
            members = channel.members or "?"
            text += f"{idx}. {channel_name} ({members} iscritti)\n"
            keyboard.append([InlineKeyboardButton(
                f"Usa {channel_name}",
                callback_data=f"offer:editor:select_channel:{offer_id}:{channel.id}"
            )])
        
        keyboard.append([InlineKeyboardButton("◀️ Indietro", callback_data="insideads:earn:editor")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def offer_editor_select_channel(update: Update, context: CallbackContext) -> None:
    """Editor selects channel for publishing - verify bot has privileges."""
    query = update.callback_query
    user_data = update.effective_user
    if not query or not user_data:
        return
    
    await query.answer()
    
    # Extract offer_id and channel_id
    try:
        parts = query.data.split(":")
        offer_id = int(parts[3])
        channel_id = int(parts[4])
    except (IndexError, ValueError):
        await query.answer("❌ Errore", show_alert=True)
        return
    
    with with_session(context) as session:
        from .models import PromoOffer, Channel
        
        # Verify offer exists
        offer = session.query(PromoOffer).filter_by(id=offer_id).first()
        if not offer:
            await query.edit_message_text("❌ Offerta non trovata")
            return
        
        # Verify channel belongs to user
        channel = session.query(Channel).filter_by(
            id=channel_id,
            user_id=user_data.id
        ).first()
        
        if not channel:
            await query.edit_message_text("❌ Canale non trovato o non sei amministratore")
            return
        
        channel_name = channel.title or f"@{channel.handle}"
        
        # Try to verify bot has privileges in the channel
        try:
            # Get bot info
            bot_info = await context.bot.get_me()
            
            # Try to get channel admins - this will fail if bot is not member/admin
            try:
                # Check if bot is in the channel by trying to get bot's chat member info
                bot_member = await context.bot.get_chat_member(chat_id=channel.telegram_id, user_id=bot_info.id)
                
                # Check if bot has required permissions
                if bot_member.status not in ["administrator", "creator"]:
                    # Bot is member but not admin
                    text = (
                        f"⚠️ **Privilegi Insufficienti**\n\n"
                        f"📱 **Canale:** {channel_name}\n\n"
                        f"❌ Il bot non è amministratore nel canale.\n\n"
                        f"**Come risolvere:**\n"
                        f"1. Apri il canale: {channel.handle or 'il tuo canale'}\n"
                        f"2. Vai in Gestisci Canale → Amministratori\n"
                        f"3. Aggiungi @{bot_info.username} come amministratore\n"
                        f"4. Dai questi permessi:\n"
                        f"   ✅ Pubblica messaggi\n"
                        f"   ✅ Modifica messaggi\n"
                        f"   ✅ Cancella messaggi\n\n"
                        f"Poi riprova!"
                    )
                    
                    keyboard = [
                        [InlineKeyboardButton("✅ Ho dato i privilegi", callback_data=f"offer:editor:verify:{offer_id}:{channel_id}")],
                        [InlineKeyboardButton("◀️ Scegli altro canale", callback_data="insideads:earn:editor")],
                    ]
                    
                    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
                    return
                
                # Bot is admin - proceed
                has_permissions = True
                
            except Exception as e:
                # Bot is not in channel at all
                logger.warning(f"Bot not in channel: {e}")
                has_permissions = False
        
        except Exception as e:
            logger.error(f"Error checking bot privileges: {e}")
            has_permissions = False
        
        if not has_permissions:
            # Bot is not in the channel
            bot_info = await context.bot.get_me()
            text = (
                f"⚠️ **Bot Non Presente nel Canale**\n\n"
                f"📱 **Canale:** {channel_name}\n\n"
                f"❌ Il bot non è stato aggiunto al canale.\n\n"
                f"**Come risolvere:**\n"
                f"1. Apri il canale: {channel.handle or 'il tuo canale'}\n"
                f"2. Aggiungi il bot @{bot_info.username}\n"
                f"3. Vai in Gestisci Canale → Amministratori\n"
                f"4. Promuovi @{bot_info.username} a amministratore\n"
                f"5. Dai questi permessi:\n"
                f"   ✅ Pubblica messaggi\n"
                f"   ✅ Modifica messaggi\n"
                f"   ✅ Cancella messaggi\n\n"
                f"Poi riprova!"
            )
            
            keyboard = [
                [InlineKeyboardButton("✅ Ho aggiunto il bot", callback_data=f"offer:editor:verify:{offer_id}:{channel_id}")],
                [InlineKeyboardButton("◀️ Scegli altro canale", callback_data="insideads:earn:editor")],
            ]
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        # Bot has permissions - proceed to show posts
        context.user_data["editor_accepted_offer"] = offer_id
        context.user_data["editor_selected_channel"] = channel_id
        context.user_data["editor_channel_name"] = channel_name
        
        payment_type = "CPC" if offer.payment_type == "per_clic" else "CPA"
        
        text = (
            f"📝 **Post Disponibili per Pubblicazione**\n\n"
            f"📱 **Canale:** {channel_name}\n"
            f"💼 **Offerta:** #{offer_id}\n"
            f"📊 **Modello:** {payment_type}\n"
            f"💰 **Pagamento:** €{offer.interaction_price:.2f} per interazione\n\n"
            "✅ **Bot verificato - Pronto per pubblicare!**\n\n"
            "📋 **Post da pubblicare:**\n\n"
            "⏳ Generazione post in corso...\n"
            "(I post verranno generati dalla campagna dell'inserzionista)"
        )
        
        keyboard = [
            [InlineKeyboardButton("🤖 Genera con AI", callback_data=f"offer:editor:generate:{offer_id}:{channel_id}")],
            [InlineKeyboardButton("⏰ Programmazione", callback_data=f"offer:editor:schedule:{offer_id}:{channel_id}")],
            [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:earn:editor")],
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def offer_editor_verify(update: Update, context: CallbackContext) -> None:
    """Editor confirms they added the bot - verify again."""
    query = update.callback_query
    user_data = update.effective_user
    if not query or not user_data:
        return
    
    await query.answer("🔍 Verificando privilegi del bot...")
    
    # Extract IDs
    try:
        parts = query.data.split(":")
        offer_id = int(parts[3])
        channel_id = int(parts[4])
    except (IndexError, ValueError):
        await query.answer("❌ Errore", show_alert=True)
        return
    
    with with_session(context) as session:
        from .models import PromoOffer, Channel
        
        offer = session.query(PromoOffer).filter_by(id=offer_id).first()
        channel = session.query(Channel).filter_by(
            id=channel_id,
            user_id=user_data.id
        ).first()
        
        if not offer or not channel:
            await query.edit_message_text("❌ Offerta o canale non trovato")
            return
        
        channel_name = channel.title or f"@{channel.handle}"
        
        try:
            bot_info = await context.bot.get_me()
            bot_member = await context.bot.get_chat_member(chat_id=channel.telegram_id, user_id=bot_info.id)
            
            if bot_member.status not in ["administrator", "creator"]:
                await query.edit_message_text(
                    f"❌ Il bot non è ancora amministratore nel canale {channel_name}.\n\n"
                    "Assicurati di aver promosso il bot e datogli i permessi corretti."
                )
                return
            
            # Success - proceed
            context.user_data["editor_accepted_offer"] = offer_id
            context.user_data["editor_selected_channel"] = channel_id
            context.user_data["editor_channel_name"] = channel_name
            
            payment_type = "CPC" if offer.payment_type == "per_clic" else "CPA"
            
            text = (
                f"✅ **Bot Verificato Con Successo!**\n\n"
                f"📱 **Canale:** {channel_name}\n"
                f"💼 **Offerta:** #{offer_id}\n"
                f"📊 **Modello:** {payment_type}\n"
                f"💰 **Pagamento:** €{offer.interaction_price:.2f} per interazione\n\n"
                "🚀 **Pronto per pubblicare i post!**"
            )
            
            keyboard = [
                [InlineKeyboardButton("🤖 Genera con AI", callback_data=f"offer:editor:generate:{offer_id}:{channel_id}")],
                [InlineKeyboardButton("⏰ Programmazione", callback_data=f"offer:editor:schedule:{offer_id}:{channel_id}")],
                [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:earn:editor")],
            ]
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        
        except Exception as e:
            logger.error(f"Error verifying bot: {e}")
            await query.edit_message_text(
                f"❌ Errore nella verifica.\n\n"
                f"Dettagli: {str(e)[:100]}"
            )
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
        [InlineKeyboardButton("📚 Catalogo Inserzionista", callback_data="marketplace:advertiser:catalog")],
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
        f"👥 Iscritti: {stats['followers']}\n"
        f"🖱️ Clic (7d): {stats['clicks']}\n"
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
        f"👥 Iscritti: {stats['followers']}\n"
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
                "🔒 **Generatore di Contenuti AI è esclusivo per Premium**\n\n"
                "Questo strumento genera contenuti personalizzati per i tuoi canali "
                "usando intelligenza artificiale.\n\n"
                "👑 **Piano Premium - Accesso Completo**\n"
                "✅ Genera Campagne Personalizzate con AI\n"
                "✅ Generatore Contenuti AI\n"
                "✅ Gestione Offerte Pubblicitarie\n"
                "✅ Statistiche Avanzate\n\n"
                "💰 **Versamento Una Tantum (A tua scelta)**\n"
                "📊 Commissione: 10% trattenuta per i nostri servizi\n\n"
                "Es: Versi €100 → Tu ricevi €90"
            )
            
            keyboard = [
                [InlineKeyboardButton("💳 Versare Importo per Premium", callback_data="upgrade:premium")],
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
        "• Post ADV personalizzati\n"
        "• Campagne complete\n"
        "• Varianti per test A/B"
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

    text = "Seleziona stile comunicativo della creatività ADV (necessario per Telegram):"

    keyboard = [
        [InlineKeyboardButton("Telegram", callback_data="ai:platform_telegram")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_PLATFORM


async def ai_generate_content(update: Update, context: CallbackContext) -> int:
    """Generate and display AI content."""
    query = update.callback_query
    await query.answer()

    # Extract platform
    platform_map = {
        "ai:platform_telegram": "telegram",
    }

    platform = platform_map.get(query.data, "telegram")
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
                "🔒 **Genera Campagna con AI è esclusivo per Premium**\n\n"
                "Questo strumento analizza il tuo canale e genera campagne personalizzate "
                "usando intelligenza artificiale avanzata.\n\n"
                "👑 **Piano Premium - Accesso Completo**\n"
                "✅ Genera Campagne Personalizzate con AI\n"
                "✅ Generatore Contenuti AI\n"
                "✅ Gestione Offerte Pubblicitarie\n"
                "✅ Statistiche Avanzate\n\n"
                "💰 **Versamento Una Tantum (A tua scelta)**\n"
                "📊 Commissione: 10% trattenuta per i nostri servizi\n"
                "Es: Versi €100 → Tu ricevi €90 (10% ai nostri servizi)\n\n"
                "🔓 Sblocca adesso per iniziare!"
            )
            
            keyboard = [
                [InlineKeyboardButton("💳 Versare Importo per Premium", callback_data="upgrade:premium")],
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
    text = "Piattaforma: Telegram ADV"
    
    keyboard = [
        [InlineKeyboardButton("Telegram", callback_data="aigen:platform:telegram")],
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
    
    text = "Seleziona stile comunicativo della creatività ADV (necessario per Telegram):"
    
    keyboard = [
        [InlineKeyboardButton("Professional", callback_data="aigen:tone:professional")],
        [InlineKeyboardButton("Friendly", callback_data="aigen:tone:friendly")],
        [InlineKeyboardButton("Aggressive", callback_data="aigen:tone:aggressive")],
        [InlineKeyboardButton("Playful", callback_data="aigen:tone:playful")],
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
    text = "Generazione in corso..."
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


# ============================================================================
# FASE 2: EDITOR MARKETPLACE - Notifiche e Accettazione Ordini (Task 12)
# ============================================================================

async def marketplace_editor_notify_new_order(
    context: CallbackContext,
    editor_user_id: int,
    order_id: int,
    advertiser_username: str,
    channel_name: str,
    price: float,
    duration: int,
    content_preview: str,
) -> None:
    """Notifica l'editore di un nuovo ordine PENDING."""
    
    text = (
        f"📬 **Nuovo Ordine in Sospeso!**\n\n"
        f"👤 Inserizionista: @{advertiser_username}\n"
        f"📺 Canale: {channel_name}\n"
        f"💰 Prezzo: €{price:.2f}\n"
        f"⏱️ Durata: {duration} ore\n\n"
        f"**Contenuto da pubblicare:**\n"
        f"```\n{content_preview}\n```\n\n"
        f"Vuoi accettare questo ordine?"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Accetta", callback_data=f"marketplace:editor:accept_order:{order_id}")],
        [InlineKeyboardButton("❌ Rifiuta", callback_data=f"marketplace:editor:reject_order:{order_id}")],
        [InlineKeyboardButton("👁️ Visualizza Dettagli", callback_data=f"marketplace:editor:view_order:{order_id}")],
    ]
    
    try:
        await context.bot.send_message(
            chat_id=editor_user_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        logger.info(f"✅ Notifica inviata al editor {editor_user_id} per ordine #{order_id}")
    except Exception as e:
        logger.error(f"❌ Errore invio notifica editore {editor_user_id}: {e}")


async def marketplace_editor_accept_order(update: Update, context: CallbackContext) -> None:
    """Editore accetta ordine - Update OrderState PENDING → CONFIRMED."""
    query = update.callback_query
    await query.answer("Ordine accettato! ✅")
    
    order_id = int(query.data.split(":")[-1])
    user_data = update.effective_user
    if not user_data:
        return
    
    with with_session(context) as session:
        from .models import MarketplaceOrder, OrderState, Payment, PaymentStatus
        from datetime import datetime
        
        order = session.query(MarketplaceOrder).filter_by(id=order_id).first()
        if not order:
            await query.edit_message_text("❌ Ordine non trovato")
            return
        
        if order.status != OrderState.PENDING:
            await query.edit_message_text(
                f"⚠️ Ordine non è più in sospeso (Status: {order.status.value})"
            )
            return
        
        # Update ordine
        order.status = OrderState.CONFIRMED
        order.confirmed_at = datetime.now()
        order.editor_user_id = user_data.id
        
        # Update pagamento
        payment = session.query(Payment).filter_by(order_id=order_id).first()
        if payment:
            payment.status = PaymentStatus.CONFIRMED
        
        session.commit()
        
        order_id_final = order.id
        advertiser_id = order.advertiser_id
        channel_listing_id = order.channel_listing_id
        content = order.content_text[:100]
        price = payment.amount if payment else 0
    
    text = (
        f"✅ **Ordine Accettato!**\n\n"
        f"ID Ordine: #{order_id_final}\n"
        f"Status: CONFIRMED\n\n"
        f"Pubblicherai il post entro le prossime 24 ore.\n"
        f"L'inserzionista è già stato pagato.\n\n"
        f"Ricorda:\n"
        f"• Pubblica il contenuto fornito\n"
        f"• Mantieni la durata specificata\n"
        f"• Dopo la fine → Ordine auto-completa"
    )
    
    keyboard = [
        [InlineKeyboardButton("📋 Visualizza Ordine", callback_data=f"marketplace:editor:view_order:{order_id_final}")],
        [InlineKeyboardButton("📱 Miei Ordini", callback_data="marketplace:editor:incoming_orders")],
        [InlineKeyboardButton("◀️ Menu Principale", callback_data="insideads:earn")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Notifica inserzionista che ordine è stato confermato
    try:
        advertiser_text = (
            f"✅ **Ordine Confermato!**\n\n"
            f"ID: #{order_id_final}\n"
            f"Editore ha accettato il tuo ordine.\n"
            f"Il post sarà pubblicato entro le prossime 24 ore.\n\n"
            f"💰 Importo: €{price:.2f}\n"
            f"Puoi tracciare lo stato in 'Le mie Campagne'"
        )
        
        await context.bot.send_message(
            chat_id=advertiser_id,
            text=advertiser_text,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"Notifica inserzionista non inviata: {e}")


async def marketplace_editor_reject_order(update: Update, context: CallbackContext) -> None:
    """Editore rifiuta ordine - Update OrderState PENDING → CANCELLED, Refund."""
    query = update.callback_query
    await query.answer("Ordine rifiutato")
    
    order_id = int(query.data.split(":")[-1])
    
    with with_session(context) as session:
        from .models import MarketplaceOrder, OrderState, Payment, PaymentStatus
        from datetime import datetime
        
        order = session.query(MarketplaceOrder).filter_by(id=order_id).first()
        if not order:
            await query.edit_message_text("❌ Ordine non trovato")
            return
        
        if order.status != OrderState.PENDING:
            await query.edit_message_text(
                f"⚠️ Ordine non è più in sospeso (Status: {order.status.value})"
            )
            return
        
        # Update ordine
        order.status = OrderState.CANCELLED
        order.cancelled_at = datetime.now()
        order.cancellation_reason = "REJECTED_BY_EDITOR"
        
        # Update pagamento - Refund
        payment = session.query(Payment).filter_by(order_id=order_id).first()
        if payment:
            payment.status = PaymentStatus.REFUNDED
            payment.refund_date = datetime.now()
        
        # Registra transazione di rimborso
        from .models import MoneyTransaction
        refund_transaction = MoneyTransaction(
            from_user_id=None,  # Platform refund
            to_user_id=order.advertiser_id,
            amount=payment.amount if payment else 0,
            transaction_type="ORDER_REFUND",
            order_id=order_id,
            created_at=datetime.now(),
            created_by_user_id=update.effective_user.id,
        )
        session.add(refund_transaction)
        
        # Ricarica saldo inserzionista
        from .inside_ads_services import add_transaction
        add_transaction(
            session,
            user_id=order.advertiser_id,
            amount=payment.amount if payment else 0,
            transaction_type="ORDER_REFUND",
            description=f"Rimborso ordine #{order_id} rifiutato da editore",
        )
        
        session.commit()
        
        order_id_final = order.id
        advertiser_id = order.advertiser_id
        refund_amount = payment.amount if payment else 0
    
    text = (
        f"❌ **Ordine Rifiutato**\n\n"
        f"ID Ordine: #{order_id_final}\n"
        f"Status: CANCELLED\n\n"
        f"✅ Rimborso completo (€{refund_amount:.2f}) all'inserzionista."
    )
    
    keyboard = [
        [InlineKeyboardButton("📱 Miei Ordini", callback_data="marketplace:editor:incoming_orders")],
        [InlineKeyboardButton("◀️ Menu Principale", callback_data="insideads:earn")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Notifica inserzionista del rifiuto
    try:
        advertiser_text = (
            f"❌ **Ordine Rifiutato**\n\n"
            f"ID: #{order_id_final}\n"
            f"Purtroppo l'editore ha rifiutato il tuo ordine.\n\n"
            f"💰 Rimborso: €{refund_amount:.2f}\n"
            f"Il saldo è stato ricaricato automaticamente.\n\n"
            f"Puoi provare con un altro canale dal catalogo."
        )
        
        await context.bot.send_message(
            chat_id=advertiser_id,
            text=advertiser_text,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"Notifica rifiuto non inviata a inserzionista: {e}")


async def marketplace_editor_incoming_orders(update: Update, context: CallbackContext) -> None:
    """Mostra ordini PENDING per editore."""
    query = update.callback_query
    user_data = update.effective_user
    if not user_data:
        return
    
    if query:
        await query.answer()
    
    with with_session(context) as session:
        from .models import MarketplaceOrder, OrderState, ChannelListing, User
        
        # Recupera utente editore
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        
        # Query: Ordini PENDING per questo editore
        incoming_orders = session.query(MarketplaceOrder).filter(
            MarketplaceOrder.status == OrderState.PENDING,
            ChannelListing.user_id == user.id,
        ).join(
            ChannelListing,
            MarketplaceOrder.channel_listing_id == ChannelListing.id
        ).all()
    
    if not incoming_orders:
        text = (
            f"📬 Ordini in Sospeso\n\n"
            f"Non hai ordini in attesa di approvazione.\n"
            f"Gli ordini appariranno qui quando gli inserzionisti\n"
            f"creeranno campagne sui tuoi canali."
        )
        
        keyboard = [
            [InlineKeyboardButton("📝 Miei Canali", callback_data="marketplace:editor:my_channels")],
            [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:earn")],
        ]
        
        if query:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Mostra lista ordini PENDING
    text = (
        f"📬 Ordini in Sospeso\n\n"
        f"Hai {len(incoming_orders)} ordini in attesa di approvazione:\n\n"
    )
    
    keyboard = []
    for i, order in enumerate(incoming_orders[:5], 1):  # Max 5 per pagina
        advertiser = session.query(User).filter_by(id=order.advertiser_id).first()
        advertiser_name = f"@{advertiser.username}" if advertiser and advertiser.username else f"User_{advertiser.id}"
        
        text += (
            f"{i}. **Ordine #{order.id}**\n"
            f"   📤 Da: {advertiser_name}\n"
            f"   💰 Prezzo: €{order.channel_listing.suggested_price if order.channel_listing else 'N/A':.2f}\n"
            f"   ⏱️ Durata: {order.duration_hours}h\n"
            f"   📝 Preview: {order.content_text[:30]}...\n\n"
        )
        
        button_text = f"📋 Ordine #{order.id} da {advertiser_name[:12]}"
        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=f"marketplace:editor:view_order:{order.id}")
        ])
    
    keyboard.append([InlineKeyboardButton("◀️ Indietro", callback_data="insideads:earn")])
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def marketplace_editor_view_order(update: Update, context: CallbackContext) -> None:
    """Visualizza dettagli completi dell'ordine."""
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    order_id = int(query.data.split(":")[-1])
    
    with with_session(context) as session:
        from .models import MarketplaceOrder, OrderState, User
        
        order = session.query(MarketplaceOrder).filter_by(id=order_id).first()
        if not order:
            await query.edit_message_text("❌ Ordine non trovato")
            return
        
        advertiser = session.query(User).filter_by(id=order.advertiser_id).first()
        advertiser_name = f"@{advertiser.username}" if advertiser and advertiser.username else f"User_{advertiser.id}"
    
    text = (
        f"📋 **Dettagli Ordine #{order_id}**\n\n"
        f"**Status:** {order.status.value}\n"
        f"**Data Creazione:** {order.created_at.strftime('%d/%m/%Y %H:%M') if order.created_at else 'N/A'}\n\n"
        f"**Inserizionista:**\n"
        f"👤 {advertiser_name}\n\n"
        f"**Dettagli Campagna:**\n"
        f"💰 Prezzo: €{order.channel_listing.suggested_price if order.channel_listing else 0:.2f}\n"
        f"⏱️ Durata: {order.duration_hours} ore\n"
        f"📺 Canale: {order.channel_listing.channel_handle if order.channel_listing else 'N/A'}\n\n"
        f"**Contenuto da Pubblicare:**\n"
        f"```\n{order.content_text}\n```"
    )
    
    keyboard = []
    if order.status == OrderState.PENDING:
        keyboard = [
            [InlineKeyboardButton("✅ Accetta Ordine", callback_data=f"marketplace:editor:accept_order:{order_id}")],
            [InlineKeyboardButton("❌ Rifiuta Ordine", callback_data=f"marketplace:editor:reject_order:{order_id}")],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(f"⚠️ Status: {order.status.value}", callback_data="noop")],
        ]
    
    keyboard.append([InlineKeyboardButton("◀️ Torna agli Ordini", callback_data="marketplace:editor:incoming_orders")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# ============================================================================
# FASE 2: ADVERTISER MARKETPLACE - Catalogo Inserzionista
# ============================================================================

async def marketplace_advertiser_catalog(update: Update, context: CallbackContext) -> None:
    """Show advertiser marketplace catalog with available channels."""
    query = update.callback_query
    user_data = update.effective_user
    if not user_data:
        return
    
    if query:
        await query.answer()
    
    # Se viene da un filtro, recupera i filtri dal contesto
    filters_text = context.user_data.get("marketplace_filters_text", "Nessun filtro attivo")
    
    with with_session(context) as session:
        from .models import ChannelListing, Channel, ChannelState
        from sqlalchemy import and_, or_
        
        # Costruisci query base per i canali disponibili
        query_channels = session.query(ChannelListing).filter(
            ChannelListing.is_available == True
        )
        
        # Applica filtri se presenti nel contesto
        if "category" in context.user_data:
            query_channels = query_channels.filter(
                ChannelListing.category == context.user_data["category"]
            )
        
        if "min_price" in context.user_data:
            query_channels = query_channels.filter(
                ChannelListing.suggested_price >= context.user_data["min_price"]
            )
        
        if "max_price" in context.user_data:
            query_channels = query_channels.filter(
                ChannelListing.suggested_price <= context.user_data["max_price"]
            )
        
        if "min_reach" in context.user_data:
            query_channels = query_channels.filter(
                ChannelListing.reach_24h >= context.user_data["min_reach"]
            )
        
        channels = query_channels.limit(10).all()
    
    text = (
        f"🛍️ Catalogo Inserzionista\n\n"
        f"Filtri attivi: {filters_text}\n\n"
        f"Canali disponibili: {len(channels)}\n\n"
    )
    
    if not channels:
        text += "❌ Nessun canale disponibile con i filtri selezionati."
        keyboard = [
            [InlineKeyboardButton("🔍 Modifica Filtri", callback_data="marketplace:advertiser:filter")],
            [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:buy")],
        ]
    else:
        # Crea lista di canali
        keyboard = []
        for channel in channels[:5]:  # Mostra max 5 canali per pagina
            channel_name = f"@{channel.channel_handle}" if channel.channel_handle else f"#{channel.id}"
            price_str = f"€{channel.suggested_price:.2f}" if channel.suggested_price else "Offerta"
            reach_str = f"{channel.reach_24h:,}" if channel.reach_24h else "N/A"
            
            button_text = f"📺 {channel_name[:15]} | €{channel.suggested_price:.1f} | 👁️ {reach_str}"
            keyboard.append([
                InlineKeyboardButton(
                    button_text, 
                    callback_data=f"marketplace:advertiser:view:{channel.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔍 Modifica Filtri", callback_data="marketplace:advertiser:filter")])
        keyboard.append([InlineKeyboardButton("◀️ Indietro", callback_data="insideads:buy")])
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def marketplace_advertiser_filter(update: Update, context: CallbackContext) -> None:
    """Show filter menu for channel catalog."""
    query = update.callback_query
    if query:
        await query.answer()
    
    text = (
        "🔍 Seleziona Filtri\n\n"
        "Scegli come filtrare i canali disponibili:"
    )
    
    keyboard = [
        [InlineKeyboardButton("📂 Per Categoria", callback_data="marketplace:advertiser:filter:category")],
        [InlineKeyboardButton("💰 Per Prezzo", callback_data="marketplace:advertiser:filter:price")],
        [InlineKeyboardButton("👁️ Per Reach Minimo", callback_data="marketplace:advertiser:filter:reach")],
        [InlineKeyboardButton("⭐ Per Engagement", callback_data="marketplace:advertiser:filter:engagement")],
        [InlineKeyboardButton("🔄 Reimposta Filtri", callback_data="marketplace:advertiser:filter:reset")],
        [InlineKeyboardButton("✅ Applica Filtri", callback_data="marketplace:advertiser:catalog")],
        [InlineKeyboardButton("◀️ Indietro", callback_data="marketplace:advertiser:catalog")],
    ]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def marketplace_advertiser_view_channel_details(update: Update, context: CallbackContext) -> None:
    """Show detailed information about a specific channel."""
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    # Estrai channel_id dal callback
    channel_id = int(query.data.split(":")[-1])
    
    with with_session(context) as session:
        from .models import ChannelListing, Channel
        
        channel_listing = session.query(ChannelListing).filter_by(id=channel_id).first()
        if not channel_listing:
            await query.edit_message_text("❌ Canale non trovato")
            return
        
        channel = session.query(Channel).filter_by(id=channel_listing.channel_id).first()
    
    # Calcola statistiche
    quality_score = getattr(channel_listing, 'quality_score', 4.5)
    engagement_rate = getattr(channel_listing, 'engagement_rate', 2.5)
    
    text = (
        f"📺 Dettagli Canale\n\n"
        f"**Informazioni:**\n"
        f"• Nome: @{channel_listing.channel_handle}\n"
        f"• Categoria: {channel_listing.category or 'N/A'}\n"
        f"• Titolo: {channel_listing.title or 'N/A'}\n\n"
        f"**Metriche:**\n"
        f"• 👥 Iscritti: {channel_listing.subscribers:,}\n"
        f"• 👁️ Visualizzazioni (24h): {channel_listing.reach_24h:,}\n"
        f"• ⭐ Qualità: {quality_score}/5.0\n"
        f"• 🔥 Engagement: {engagement_rate:.1f}%\n\n"
        f"**Prezzo:**\n"
        f"• 💰 Suggerito: €{channel_listing.suggested_price:.2f}\n"
        f"• Min: €{getattr(channel_listing, 'min_price', channel_listing.suggested_price * 0.8):.2f}\n"
        f"• Max: €{getattr(channel_listing, 'max_price', channel_listing.suggested_price * 1.2):.2f}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("📝 Crea Ordine", callback_data=f"marketplace:advertiser:order:start:{channel_id}")],
        [InlineKeyboardButton("📊 Visualizza Storico", callback_data=f"marketplace:advertiser:history:{channel_id}")],
        [InlineKeyboardButton("◀️ Torna al Catalogo", callback_data="marketplace:advertiser:catalog")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def marketplace_advertiser_create_order(update: Update, context: CallbackContext) -> int:
    """Start order creation flow - Step 1: Select duration."""
    query = update.callback_query
    if not query:
        return ConversationHandler.END
    
    await query.answer()
    
    # Estrai channel_id dal callback
    channel_id = int(query.data.split(":")[-1])
    context.user_data["order_channel_id"] = channel_id
    
    with with_session(context) as session:
        from .models import ChannelListing
        channel_listing = session.query(ChannelListing).filter_by(id=channel_id).first()
        context.user_data["order_channel_name"] = channel_listing.channel_handle if channel_listing else "Sconosciuto"
        context.user_data["order_channel_price"] = channel_listing.suggested_price if channel_listing else 0
    
    text = (
        f"📝 Crea Ordine - Step 1/4\n\n"
        f"Canale: @{context.user_data['order_channel_name']}\n"
        f"Prezzo: €{context.user_data['order_channel_price']:.2f}\n\n"
        f"Seleziona la durata della campagna:"
    )
    
    keyboard = [
        [InlineKeyboardButton("⏱️ 6 Ore", callback_data="marketplace:advertiser:order:duration:6")],
        [InlineKeyboardButton("⏱️ 12 Ore", callback_data="marketplace:advertiser:order:duration:12")],
        [InlineKeyboardButton("⏱️ 24 Ore", callback_data="marketplace:advertiser:order:duration:24")],
        [InlineKeyboardButton("❌ Annulla", callback_data="marketplace:advertiser:catalog")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Usa STATE per tracciare il flusso
    return MARKETPLACE_ORDER_DURATION


async def marketplace_advertiser_order_duration_selected(update: Update, context: CallbackContext) -> int:
    """Step 2: Upload content."""
    query = update.callback_query
    if not query:
        return ConversationHandler.END
    
    await query.answer()
    
    # Estrai durata dal callback
    duration = int(query.data.split(":")[-1])
    context.user_data["order_duration"] = duration
    
    text = (
        f"📝 Crea Ordine - Step 2/4\n\n"
        f"Canale: @{context.user_data['order_channel_name']}\n"
        f"Durata: {duration} ore\n"
        f"Prezzo: €{context.user_data['order_channel_price']:.2f}\n\n"
        f"Invia il contenuto (testo + opzionale: foto/video)"
    )
    
    await query.edit_message_text(text)
    
    return MARKETPLACE_ORDER_CONTENT


async def marketplace_advertiser_order_content_received(update: Update, context: CallbackContext) -> int:
    """Step 3: Review order."""
    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END
    
    # Salva il contenuto
    content_text = update.message.text or update.message.caption or "[Media only]"
    
    # Valida il contenuto usando ContentValidator
    from .services import ContentValidator
    is_valid, error_msg = ContentValidator.validate(content_text, strict=False)
    
    if not is_valid:
        text = (
            f"❌ Contenuto non valido\n\n"
            f"Errore: {error_msg}\n\n"
            f"Per favore, riprova con un contenuto diverso."
        )
        
        keyboard = [
            [InlineKeyboardButton("✏️ Invia di nuovo", callback_data="marketplace:advertiser:order:edit_content")],
            [InlineKeyboardButton("❌ Annulla ordine", callback_data="marketplace:advertiser:catalog")],
        ]
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return 51  # Rimani in MARKETPLACE_ORDER_CONTENT
    
    context.user_data["order_content"] = content_text[:200]  # Limita a 200 chars per preview
    
    total_price = context.user_data["order_channel_price"]
    
    text = (
        f"📝 Crea Ordine - Step 3/4 (REVIEW)\n\n"
        f"**Dettagli Ordine:**\n"
        f"• Canale: @{context.user_data['order_channel_name']}\n"
        f"• Durata: {context.user_data['order_duration']} ore\n"
        f"• Prezzo: €{total_price:.2f}\n\n"
        f"**Contenuto:**\n"
        f"{context.user_data['order_content']}\n\n"
        f"✅ Contenuto validato. Confermi l'ordine?"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Conferma e Paga", callback_data="marketplace:advertiser:order:confirm")],
        [InlineKeyboardButton("✏️ Modifica Contenuto", callback_data="marketplace:advertiser:order:edit_content")],
        [InlineKeyboardButton("❌ Annulla", callback_data="marketplace:advertiser:catalog")],
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    return MARKETPLACE_ORDER_REVIEW


async def marketplace_advertiser_order_confirm(update: Update, context: CallbackContext) -> int:
    """Step 4: Process payment and create order."""
    query = update.callback_query
    if not query:
        return ConversationHandler.END
    
    await query.answer()
    
    user_data = update.effective_user
    if not user_data:
        return ConversationHandler.END
    
    with with_session(context) as session:
        from .models import (
            User, MarketplaceOrder, OrderState, ChannelListing,
            Payment, PaymentStatus, MoneyTransaction
        )
        from datetime import datetime, timedelta
        
        # Recupera utente
        user = ensure_user(
            session,
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            language_code=user_data.language_code,
        )
        
        # Recupera canale
        channel_listing = session.query(ChannelListing).filter_by(
            id=context.user_data["order_channel_id"]
        ).first()
        
        if not channel_listing:
            await query.edit_message_text("❌ Canale non trovato")
            return ConversationHandler.END
        
        # Controlla saldo
        from .inside_ads_services import get_user_balance
        balance = get_user_balance(session, user)
        total_price = context.user_data["order_channel_price"]
        
        if balance < total_price:
            text = (
                f"❌ Saldo insufficiente\n\n"
                f"Saldo: €{balance:.2f}\n"
                f"Necessari: €{total_price:.2f}\n"
                f"Mancano: €{total_price - balance:.2f}"
            )
            keyboard = [
                [InlineKeyboardButton("💰 Ricarica Saldo", callback_data="insideads:account:topup")],
                [InlineKeyboardButton("◀️ Indietro", callback_data="marketplace:advertiser:catalog")],
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            return ConversationHandler.END
        
        # Crea ordine
        now = datetime.now()
        order = MarketplaceOrder(
            advertiser_id=user.id,
            channel_listing_id=channel_listing.id,
            status=OrderState.PENDING,
            content_text=context.user_data.get("order_content", ""),
            duration_hours=context.user_data.get("order_duration", 24),
            created_at=now,
            created_by_user_id=user.id,
        )
        session.add(order)
        session.flush()  # Genera l'ID dell'ordine
        
        # Crea pagamento
        payment = Payment(
            order_id=order.id,
            amount=total_price,
            commission_rate=0.10,  # 10% commission
            status=PaymentStatus.PAID,
            payment_date=now,
            created_by_user_id=user.id,
        )
        session.add(payment)
        
        # Registra transazione
        transaction = MoneyTransaction(
            from_user_id=user.id,
            to_user_id=channel_listing.user_id,
            amount=total_price * 0.9,  # 90% all'editore
            transaction_type="ORDER_PAYMENT",
            order_id=order.id,
            created_at=now,
            created_by_user_id=user.id,
        )
        session.add(transaction)
        
        # Deduci dal saldo dell'inserzionista
        from .inside_ads_services import add_transaction as add_trans
        add_trans(
            session,
            user_id=user.id,
            amount=-total_price,
            transaction_type="ORDER_PAYMENT",
            description=f"Pagamento ordine per @{channel_listing.channel_handle}",
        )
        
        session.commit()
        
        order_id = order.id
        editor_user_id = channel_listing.user_id
        content_preview = context.user_data.get("order_content", "")[:100]
    
    # Notifica l'editore del nuovo ordine (TASK 12)
    try:
        await marketplace_editor_notify_new_order(
            context=context,
            editor_user_id=editor_user_id,
            order_id=order_id,
            advertiser_username=user.username,
            channel_name=channel_listing.channel_handle,
            price=total_price,
            duration=context.user_data.get("order_duration", 24),
            content_preview=content_preview,
        )
    except Exception as e:
        logger.error(f"Errore nell'invio della notifica editore: {e}")
    
    text = (
        f"✅ Ordine Creato Con Successo!\n\n"
        f"**ID Ordine:** #{order_id}\n"
        f"**Canale:** @{context.user_data['order_channel_name']}\n"
        f"**Durata:** {context.user_data['order_duration']} ore\n"
        f"**Importo:** €{total_price:.2f}\n\n"
        f"L'editore riceverà una notifica del tuo annuncio.\n"
        f"Lo stato dell'ordine sarà disponibile in 'Le mie campagne'."
    )
    
    keyboard = [
        [InlineKeyboardButton("📋 Visualizza Ordine", callback_data=f"marketplace:advertiser:order:view:{order_id}")],
        [InlineKeyboardButton("🛍️ Continua Shopping", callback_data="marketplace:advertiser:catalog")],
        [InlineKeyboardButton("📊 Le mie Campagne", callback_data="insideads:buy:list")],
        [InlineKeyboardButton("🏠 Menu Principale", callback_data="insideads:main")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Pulisci context
    context.user_data.clear()
    
    return ConversationHandler.END


# ============================================================================
# TASK 14 - VERIFICA ADMIN CANALE (FASE 6)
# ============================================================================

async def verify_channel_admin(user_id: int, channel_id: int, context: CallbackContext) -> dict:
    """
    Verifica che l'utente sia admin del canale Telegram prima della registrazione editore.
    
    Args:
        user_id: Telegram user ID
        channel_id: Telegram channel/group ID
        context: CallbackContext
    
    Returns:
        dict con chiavi:
        - is_admin: bool
        - username: str
        - status: str ("VERIFIED", "NOT_ADMIN", "ERROR")
        - verified_at: datetime
        - error_message: str (se applicabile)
    """
    try:
        # Get chat member to verify admin status
        chat_member = await context.bot.get_chat_member(channel_id, user_id)
        
        # Check if user has admin privileges
        is_admin = chat_member.status in ["creator", "administrator"]
        
        verification_log = {
            "user_id": user_id,
            "channel_id": channel_id,
            "is_admin": is_admin,
            "status": "VERIFIED" if is_admin else "NOT_ADMIN",
            "verified_at": datetime.now(),
            "error_message": None if is_admin else f"Utente non è admin del canale. Status: {chat_member.status}",
        }
        
        # Log verification attempt
        logger.info(f"Verifica admin - User: {user_id}, Channel: {channel_id}, Is Admin: {is_admin}")
        
        # Save to database for audit trail
        try:
            with with_session(context) as session:
                from .models import AdminAuditLog
                audit = AdminAuditLog(
                    user_id=user_id,
                    action="CHANNEL_ADMIN_VERIFICATION",
                    details=str(verification_log),
                    status="SUCCESS" if is_admin else "FAILED",
                    created_at=datetime.now(),
                )
                session.add(audit)
                session.commit()
        except Exception as audit_error:
            logger.error(f"Errore nel logging verifica admin: {audit_error}")
        
        return verification_log
    
    except Exception as e:
        logger.error(f"Errore nella verifica admin del canale: {e}")
        return {
            "user_id": user_id,
            "channel_id": channel_id,
            "is_admin": False,
            "status": "ERROR",
            "verified_at": datetime.now(),
            "error_message": str(e),
        }


async def editor_register_verify_admin(update: Update, context: CallbackContext) -> None:
    """Handler che richiede verifica admin prima di registrare editore."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Retrieve channel ID from context (should be set by previous handler)
    channel_id = context.user_data.get("editor_channel_id")
    if not channel_id:
        await query.answer("❌ Errore: Channel ID non trovato", show_alert=True)
        return
    
    with with_session(context) as session:
        from .models import Channel
        
        # Verifica admin status
        verification = await verify_channel_admin(user_id, channel_id, context)
        
        if not verification["is_admin"]:
            text = (
                f"❌ **Verifica Admin Non Riuscita**\n\n"
                f"Non sei amministratore del canale {channel_id}.\n"
                f"Per registrarti come editore devi essere admin del canale.\n\n"
                f"**Errore:** {verification['error_message']}"
            )
            keyboard = [
                [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:sell")],
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        # Admin verified - proceed with registration
        text = (
            f"✅ **Admin Verificato!**\n\n"
            f"Sei stato confermato come amministratore del canale.\n"
            f"Procedendo con la registrazione come editore..."
        )
        await query.edit_message_text(text)
        
        # Proceed with editor registration
        context.user_data["editor_verified"] = True
        # Call the actual registration function


# ============================================================================
# TASK 15 - STORICO ORDINI EDITORE (FASE 2)
# ============================================================================

async def marketplace_editor_order_history(update: Update, context: CallbackContext) -> None:
    """
    Mostra storico completo degli ordini (completati, cancellati) per editore con statistiche.
    """
    query = update.callback_query
    user_id = update.effective_user.id
    
    await query.answer()
    
    with with_session(context) as session:
        from .models import MarketplaceOrder, OrderState, ChannelListing, User
        from sqlalchemy import func
        
        # Query storico ordini (escludendo PENDING e DRAFT)
        history_orders = (
            session.query(MarketplaceOrder)
            .join(ChannelListing, MarketplaceOrder.channel_listing_id == ChannelListing.id)
            .filter(
                ChannelListing.user_id == user_id,
                MarketplaceOrder.status.in_([OrderState.COMPLETED, OrderState.CANCELLED, OrderState.DISPUTED]),
            )
            .order_by(MarketplaceOrder.created_at.desc())
            .limit(20)
            .all()
        )
        
        # Calcola statistiche
        stats_query = session.query(
            func.count(MarketplaceOrder.id).label("total_orders"),
            func.sum(MarketplaceOrder.total_price).label("total_earned"),
            func.avg(MarketplaceOrder.total_price).label("avg_price"),
        ).join(ChannelListing, MarketplaceOrder.channel_listing_id == ChannelListing.id).filter(
            ChannelListing.user_id == user_id,
            MarketplaceOrder.status == OrderState.COMPLETED,
        )
        
        stats = stats_query.first()
        
        total_orders = stats.total_orders or 0
        total_earned = stats.total_earned or 0.0
        avg_price = stats.avg_price or 0.0
        
        # Calcola completion rate
        all_orders_count = (
            session.query(func.count(MarketplaceOrder.id))
            .join(ChannelListing, MarketplaceOrder.channel_listing_id == ChannelListing.id)
            .filter(ChannelListing.user_id == user_id)
            .scalar()
        )
        
        completion_rate = (total_orders / all_orders_count * 100) if all_orders_count > 0 else 0.0
    
    text = (
        f"📊 **Storico Ordini**\n\n"
        f"**Statistiche Generali:**\n"
        f"  📈 Ordini Completati: {total_orders}\n"
        f"  💰 Totale Guadagnato: €{total_earned:.2f}\n"
        f"  💵 Prezzo Medio: €{avg_price:.2f}\n"
        f"  ✅ Tasso Completamento: {completion_rate:.1f}%\n\n"
    )
    
    if history_orders:
        text += "**Ultimi Ordini:**\n\n"
        for i, order in enumerate(history_orders[:5], 1):
            status_emoji = "✅" if order.status == OrderState.COMPLETED else "❌" if order.status == OrderState.CANCELLED else "⚠️"
            text += (
                f"{i}. {status_emoji} Order #{order.id}\n"
                f"   💰 €{order.total_price:.2f} | "
                f"   ⏱️ {order.duration}h | "
                f"   📅 {order.created_at.strftime('%d/%m/%Y')}\n"
            )
    else:
        text += "❌ Nessun ordine nello storico."
    
    keyboard = [
        [InlineKeyboardButton("📬 Ordini in Sospeso", callback_data="marketplace:editor:incoming_orders")],
        [InlineKeyboardButton("◀️ Menu Editore", callback_data="insideads:sell")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# ============================================================================
# FASE 3 - ADMIN PANEL
# ============================================================================

async def admin_main_menu(update: Update, context: CallbackContext) -> None:
    """Main admin panel menu."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    await query.answer()
    
    # Verify admin access
    with with_session(context) as session:
        from .models import User, UserRole
        user = session.query(User).filter(User.telegram_user_id == user_id).first()
        
        if not user or user.role != UserRole.ADMIN:
            text = "❌ Accesso Negato. Solo amministratori possono accedere al pannello admin."
            keyboard = [[InlineKeyboardButton("◀️ Indietro", callback_data="insideads:main")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            return
    
    text = (
        f"🔧 **Pannello Amministrazione**\n\n"
        f"Gestione della piattaforma InsideAds\n\n"
        f"Seleziona un'opzione:"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Approva Canali", callback_data="admin:approve_channels")],
        [InlineKeyboardButton("🚫 Sospendi Utenti", callback_data="admin:suspend_users")],
        [InlineKeyboardButton("💰 Override Prezzo", callback_data="admin:override_price")],
        [InlineKeyboardButton("⚖️ Gestisci Dispute", callback_data="admin:manage_disputes")],
        [InlineKeyboardButton("📋 Log Audit", callback_data="admin:audit_logs")],
        [InlineKeyboardButton("📊 Report Statistiche", callback_data="admin:statistics")],
        [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:main")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_approve_channels(update: Update, context: CallbackContext) -> None:
    """Admin: Approve pending channels."""
    query = update.callback_query
    await query.answer()
    
    with with_session(context) as session:
        from .models import Channel, ChannelState
        
        pending_channels = session.query(Channel).filter(
            Channel.state == ChannelState.PENDING_APPROVAL
        ).limit(10).all()
    
    if not pending_channels:
        text = "✅ Nessun canale in attesa di approvazione."
        keyboard = [[InlineKeyboardButton("◀️ Indietro", callback_data="admin:main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    text = "📋 **Canali in Attesa di Approvazione**\n\n"
    keyboard = []
    
    for channel in pending_channels:
        text += f"• @{channel.handle} (Subscribers: {channel.subscribers})\n"
        keyboard.append([
            InlineKeyboardButton(f"✅ Approva #{channel.id}", callback_data=f"admin:approve_channel:{channel.id}"),
            InlineKeyboardButton(f"❌ Rifiuta #{channel.id}", callback_data=f"admin:reject_channel:{channel.id}"),
        ])
    
    keyboard.append([InlineKeyboardButton("◀️ Indietro", callback_data="admin:main")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_approve_channel_action(update: Update, context: CallbackContext) -> None:
    """Admin: Approve single channel."""
    query = update.callback_query
    
    # Extract channel_id from callback_data
    parts = query.data.split(":")
    channel_id = int(parts[2])
    
    with with_session(context) as session:
        from .models import Channel, ChannelState, AdminAuditLog
        
        channel = session.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            await query.answer("❌ Canale non trovato", show_alert=True)
            return
        
        # Update channel state
        channel.state = ChannelState.ACTIVE
        
        # Log admin action
        audit = AdminAuditLog(
            user_id=update.effective_user.id,
            action="APPROVE_CHANNEL",
            details=f"Channel ID: {channel_id}, Handle: @{channel.handle}",
            status="SUCCESS",
            created_at=datetime.now(),
        )
        session.add(audit)
        session.commit()
    
    text = f"✅ Canale @{channel.handle} approvato con successo!"
    keyboard = [[InlineKeyboardButton("📋 Prossimi Canali", callback_data="admin:approve_channels")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_suspend_user(update: Update, context: CallbackContext) -> None:
    """Admin: Suspend users."""
    query = update.callback_query
    await query.answer()
    
    text = (
        "🚫 **Sospendi Utente**\n\n"
        "Inserisci l'ID Telegram dell'utente da sospendere:\n\n"
        "_Messaggio: Rispondi con l'ID Telegram_"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Indietro", callback_data="admin:main")]]
    
    context.user_data["admin_action"] = "suspend_user"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_manage_disputes(update: Update, context: CallbackContext) -> None:
    """Admin: Manage open disputes."""
    query = update.callback_query
    await query.answer()
    
    with with_session(context) as session:
        from .models import DisputeTicket, DisputeStatus
        
        open_disputes = session.query(DisputeTicket).filter(
            DisputeTicket.status == DisputeStatus.OPEN
        ).limit(5).all()
    
    if not open_disputes:
        text = "✅ Nessuna disputa aperta."
        keyboard = [[InlineKeyboardButton("◀️ Indietro", callback_data="admin:main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    text = "⚖️ **Dispute Aperte**\n\n"
    keyboard = []
    
    for dispute in open_disputes:
        text += f"• Disputa #{dispute.id} - Order: #{dispute.order_id}\n"
        keyboard.append([InlineKeyboardButton(f"📋 Dettagli #{dispute.id}", callback_data=f"admin:dispute_detail:{dispute.id}")])
    
    keyboard.append([InlineKeyboardButton("◀️ Indietro", callback_data="admin:main")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_view_audit_logs(update: Update, context: CallbackContext) -> None:
    """Admin: View audit logs."""
    query = update.callback_query
    await query.answer()
    
    with with_session(context) as session:
        from .models import AdminAuditLog
        
        recent_logs = session.query(AdminAuditLog).order_by(
            AdminAuditLog.created_at.desc()
        ).limit(10).all()
    
    text = "📋 **Log Audit Recenti**\n\n"
    
    for log in recent_logs:
        text += (
            f"• {log.action} - {log.status}\n"
            f"  User: {log.user_id} | {log.created_at.strftime('%d/%m %H:%M')}\n\n"
        )
    
    if not recent_logs:
        text = "Nessun log disponibile."
    
    keyboard = [[InlineKeyboardButton("◀️ Indietro", callback_data="admin:main")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_platform_stats(update: Update, context: CallbackContext) -> None:
    """Admin: View platform statistics."""
    query = update.callback_query
    await query.answer()
    
    with with_session(context) as session:
        from .models import User, Channel, MarketplaceOrder, OrderState
        from sqlalchemy import func
        
        total_users = session.query(func.count(User.id)).scalar()
        total_channels = session.query(func.count(Channel.id)).scalar()
        total_orders = session.query(func.count(MarketplaceOrder.id)).scalar()
        completed_orders = session.query(func.count(MarketplaceOrder.id)).filter(
            MarketplaceOrder.status == OrderState.COMPLETED
        ).scalar()
        total_revenue = session.query(func.sum(MarketplaceOrder.total_price)).filter(
            MarketplaceOrder.status == OrderState.COMPLETED
        ).scalar()
    
    completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0.0
    platform_revenue_10pct = (total_revenue * 0.1) if total_revenue else 0.0
    
    text = (
        f"📊 **Statistiche Piattaforma**\n\n"
        f"👥 Utenti Totali: {total_users or 0}\n"
        f"📢 Canali Registrati: {total_channels or 0}\n"
        f"📦 Ordini Totali: {total_orders or 0}\n"
        f"✅ Ordini Completati: {completed_orders or 0} ({completion_rate:.1f}%)\n\n"
        f"💰 Revenue Totale: €{total_revenue:.2f}" if total_revenue else "€0.00" + "\n"
        f"🏦 Commissione Platform (10%): €{platform_revenue_10pct:.2f}"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Indietro", callback_data="admin:main")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


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
                "OFFER_PAYMENT_TYPE": [MessageHandler(filters.TEXT & ~filters.COMMAND, offer_payment_type_selected)],
                "OFFER_PAYMENT": [CallbackQueryHandler(offer_payment, pattern=r"^offer:payment:")],
                "OFFER_DEPOSIT": [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, offer_deposit),
                    CallbackQueryHandler(offer_deposit, pattern=r"^offer:deposit:(increase|decrease|confirm|dummy)$"),
                ],
                "OFFER_INTERACTION_PRICE": [
                    CallbackQueryHandler(offer_interaction_price, pattern=r"^offer:interaction:(increase|decrease|confirm|dummy)$"),
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
    
    # Marketplace Editor handlers
    application.add_handler(CallbackQueryHandler(marketplace_editor_menu, pattern=r"^marketplace:editor:menu$"))
    application.add_handler(CallbackQueryHandler(marketplace_editor_register_channel, pattern=r"^marketplace:editor:register_channel$"))
    application.add_handler(CallbackQueryHandler(marketplace_editor_set_price, pattern=r"^marketplace:editor:set_price:\d+$"))
    application.add_handler(CallbackQueryHandler(marketplace_editor_confirm_price, pattern=r"^marketplace:editor:confirm_price:\d+:[\d.]+$"))
    application.add_handler(CallbackQueryHandler(marketplace_editor_my_channels, pattern=r"^marketplace:editor:my_channels$"))
    application.add_handler(CallbackQueryHandler(marketplace_editor_pending_orders, pattern=r"^marketplace:editor:pending_orders$"))
    
    # Old offer handlers (deprecated, but kept for compatibility)
    application.add_handler(CallbackQueryHandler(offer_editor_view, pattern=r"^offer:editor:view:\d+$"))
    application.add_handler(CallbackQueryHandler(offer_editor_accept, pattern=r"^offer:editor:accept:\d+$"))
    application.add_handler(CallbackQueryHandler(offer_editor_select_channel, pattern=r"^offer:editor:select_channel:\d+:\d+$"))
    application.add_handler(CallbackQueryHandler(offer_editor_verify, pattern=r"^offer:editor:verify:\d+:\d+$"))
    
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

    # Marketplace Advertiser handlers (FASE 2)
    application.add_handler(CallbackQueryHandler(marketplace_advertiser_catalog, pattern=r"^marketplace:advertiser:catalog$"))
    application.add_handler(CallbackQueryHandler(marketplace_advertiser_filter, pattern=r"^marketplace:advertiser:filter$"))
    application.add_handler(CallbackQueryHandler(marketplace_advertiser_view_channel_details, pattern=r"^marketplace:advertiser:view:\d+$"))

    # Marketplace Editor handlers - Notifications (FASE 2 Task 12)
    application.add_handler(CallbackQueryHandler(marketplace_editor_accept_order, pattern=r"^marketplace:editor:accept_order:\d+$"))
    application.add_handler(CallbackQueryHandler(marketplace_editor_reject_order, pattern=r"^marketplace:editor:reject_order:\d+$"))
    
    # Marketplace Editor handlers - Order Management (FASE 2 Task 13)
    application.add_handler(CallbackQueryHandler(marketplace_editor_incoming_orders, pattern=r"^marketplace:editor:incoming_orders$"))
    application.add_handler(CallbackQueryHandler(marketplace_editor_view_order, pattern=r"^marketplace:editor:view_order:\d+$"))

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

    # Marketplace Advertiser Order Creation Handler (FASE 2)
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CallbackQueryHandler(marketplace_advertiser_create_order, pattern=r"^marketplace:advertiser:order:start:\d+$"),
            ],
            states={
                MARKETPLACE_ORDER_DURATION: [
                    CallbackQueryHandler(marketplace_advertiser_order_duration_selected, pattern=r"^marketplace:advertiser:order:duration:(6|12|24)$"),
                ],
                MARKETPLACE_ORDER_CONTENT: [
                    MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, marketplace_advertiser_order_content_received),
                ],
                MARKETPLACE_ORDER_REVIEW: [
                    CallbackQueryHandler(marketplace_advertiser_order_confirm, pattern=r"^marketplace:advertiser:order:confirm$"),
                    CallbackQueryHandler(marketplace_advertiser_create_order, pattern=r"^marketplace:advertiser:order:edit_content$"),
                ],
            },
            fallbacks=[
                CallbackQueryHandler(marketplace_advertiser_catalog, pattern=r"^marketplace:advertiser:catalog$"),
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
                    CallbackQueryHandler(aigen_platform_selected, pattern=r"^aigen:platform:telegram$"),
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
                    CallbackQueryHandler(ai_generate_content, pattern=r"^ai:platform_telegram$"),
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
    application.add_handler(CallbackQueryHandler(upgrade_plan_selected, pattern=r"^upgrade:premium$"))
    application.add_handler(CallbackQueryHandler(upgrade_paypal, pattern=r"^upgrade:paypal:premium$"))
    application.add_handler(CallbackQueryHandler(upgrade_test, pattern=r"^upgrade:test:premium$"))
    application.add_handler(CallbackQueryHandler(upgrade_confirmed, pattern=r"^upgrade:confirmed:premium$"))

    # Task 14 - Channel Admin Verification Handlers
    application.add_handler(CallbackQueryHandler(editor_register_verify_admin, pattern=r"^marketplace:editor:verify_admin$"))

    # Task 15 - Editor Order History Handler
    application.add_handler(CallbackQueryHandler(marketplace_editor_order_history, pattern=r"^marketplace:editor:order_history$"))

    # FASE 3 - Admin Panel Handlers
    application.add_handler(CallbackQueryHandler(admin_main_menu, pattern=r"^admin:main$"))
    application.add_handler(CallbackQueryHandler(admin_approve_channels, pattern=r"^admin:approve_channels$"))
    application.add_handler(CallbackQueryHandler(admin_approve_channel_action, pattern=r"^admin:approve_channel:\d+$"))
    application.add_handler(CallbackQueryHandler(admin_suspend_user, pattern=r"^admin:suspend_users$"))
    application.add_handler(CallbackQueryHandler(admin_manage_disputes, pattern=r"^admin:manage_disputes$"))
    application.add_handler(CallbackQueryHandler(admin_view_audit_logs, pattern=r"^admin:audit_logs$"))
    application.add_handler(CallbackQueryHandler(admin_platform_stats, pattern=r"^admin:statistics$"))

    return application


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    config = Config.load()
    application = build_application(config)
    logger.info("Starting Adsbot...")
    application.run_polling()


if __name__ == "__main__":
    run()
