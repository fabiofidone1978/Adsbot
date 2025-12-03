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
from .ai_content import (
    AIContentGenerator,
    ContentType,
    ToneType,
    ContentRequest,
    ContentTemplateLibrary,
)
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
    CAMPAIGN_CTA,
    TEMPLATE_NAME,
    TEMPLATE_CONTENT,
    # Purchase campaign states
    SELECT_CAMPAIGN,
    ENTER_AMOUNT,
    SELECT_PAYMENT_PROVIDER,
    CONFIRM_PAYMENT,
) = range(18)
    # AI Content Generation states
    GENERATE_TOPIC,
    SELECT_TONE,
    SELECT_PLATFORM,
    REVIEW_CONTENT,
) = range(22)


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
    """Send quick user statistics."""

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
    text = f"📊 Statistiche rapide:\n{format_summary(summary)}"
    try:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, reply_markup=MENU_BUTTONS)
        else:
            await update.message.reply_text(text, reply_markup=MENU_BUTTONS)
    except Exception as e:
        if hasattr(e, 'message') and 'Message is not modified' in str(e):
            pass
        elif 'Message is not modified' in str(e):
            pass
        else:
            raise


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
    """Begin a growth goal conversation."""

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "Per quale canale vuoi impostare un obiettivo? (@username)"
        )
    return GOAL_CHANNEL


async def goal_channel(update: Update, context: CallbackContext) -> int:
    context.user_data["goal_channel"] = update.message.text.strip()
    await update.message.reply_text("Quanti membri vuoi raggiungere? (numero intero)")
    return GOAL_TARGET


async def goal_target(update: Update, context: CallbackContext) -> int:
    try:
        target = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Inserisci un numero valido")
        return GOAL_TARGET

    context.user_data["goal_target"] = target
    await update.message.reply_text(
        "Qual è la deadline? (YYYY-MM-DD) oppure lascia vuoto per nessuna"
    )
    return GOAL_DEADLINE


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
    """Begin an offer conversation."""

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "Per quale canale vuoi creare un'offerta? (@username)"
        )
    return OFFER_CHANNEL


async def offer_channel(update: Update, context: CallbackContext) -> int:
    context.user_data["offer_channel"] = update.message.text.strip()
    await update.message.reply_text(
        "Che tipo di offerta? (shoutout, post, pinned, takeover)"
    )
    return OFFER_TYPE


async def offer_type(update: Update, context: CallbackContext) -> int:
    offer_type_value = update.message.text.strip().lower()
    try:
        offer_type_enum = OfferType(offer_type_value)
    except ValueError:
        await update.message.reply_text(
            "Tipo non valido. Usa: shoutout, post, pinned, takeover"
        )
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
        "Note opzionali? Puoi descrivere il formato o lasciare vuoto"
    )
    return OFFER_NOTES


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


async def campaign_entry(update: Update, context: CallbackContext) -> int:
    """Begin a campaign conversation."""

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "Su quale canale vuoi lanciare la campagna? (@username)"
        )
    return CAMPAIGN_CHANNEL


async def campaign_channel(update: Update, context: CallbackContext) -> int:
    context.user_data["campaign_channel"] = update.message.text.strip()
    await update.message.reply_text("Nome della campagna?")
    return CAMPAIGN_NAME


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
    await update.message.reply_text("Call to action o note della campagna?")
    return CAMPAIGN_CTA


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
        [InlineKeyboardButton("📊 Gestione Campagne Avanzate", callback_data="campaign:menu")],
        [InlineKeyboardButton("🤖 AI Optimization", callback_data="campaign:ai_optimize")],
            keyboard = [
                [InlineKeyboardButton("➕ Crea campagna", callback_data="insideads:buy:create")],
                [InlineKeyboardButton("📋 Le mie campagne", callback_data="insideads:buy:list")],
                [InlineKeyboardButton("🤖 Genera Contenuti AI", callback_data="ai:menu")],
                [InlineKeyboardButton("📊 Gestione Campagne Avanzate", callback_data="campaign:menu")],
                [InlineKeyboardButton("🧠 AI Optimization", callback_data="campaign:ai_optimize")],
                [InlineKeyboardButton("◀️ Indietro", callback_data="insideads:main")],
            ]
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
        channels = session.query(Channel).filter_by(owner_id=user.id).all()
    
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
        """Show AI content generation menu."""
        query = update.callback_query
        if query:
            await query.answer()
    
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
    
        return GENERATE_TOPIC


    async def ai_generate_post_start(update: Update, context: CallbackContext) -> int:
        """Start post generation."""
        query = update.callback_query
        if query:
            await query.answer()
    
        context.user_data["generation_type"] = "post"
    
        text = "📝 Quale argomento vuoi usare per il post?\n\nEsempio: 'Nuovo corso di marketing online'"
    
        if query:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
    
        return GENERATE_TOPIC


    async def ai_generate_topic_input(update: Update, context: CallbackContext) -> int:
        """Receive topic and show tone selection."""
        topic = update.message.text
        context.user_data["ai_topic"] = topic
    
        text = "🎯 Seleziona il tono del messaggio:\n\n• Professional - Formale e serio\n• Friendly - Cordiale e accogliente\n• Urgent - Fretta e scadenza\n• Playful - Divertente e leggero"
    
        keyboard = [
            [InlineKeyboardButton("💼 Professional", callback_data="ai:tone_professional")],
            [InlineKeyboardButton("😊 Friendly", callback_data="ai:tone_friendly")],
            [InlineKeyboardButton("⚡ Urgent", callback_data="ai:tone_urgent")],
            [InlineKeyboardButton("😄 Playful", callback_data="ai:tone_playful")],
        ]
    
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
                GOAL_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, goal_channel)],
                GOAL_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, goal_target)],
                GOAL_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, goal_deadline)],
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
                OFFER_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, offer_channel)],
                OFFER_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, offer_type)],
                OFFER_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, offer_price)],
                OFFER_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, offer_notes)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )

    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("campaign", campaign_entry),
                CallbackQueryHandler(campaign_entry, pattern=r"^menu:campaign$"),
            ],
            states={
                CAMPAIGN_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, campaign_channel)],
                CAMPAIGN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, campaign_name)],
                CAMPAIGN_BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, campaign_budget)],
                CAMPAIGN_CTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, campaign_cta)],
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

    return application

    # AI Content Generation Handler
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CallbackQueryHandler(generate_post_menu, pattern=r"^ai:menu$"),
                CallbackQueryHandler(ai_generate_post_start, pattern=r"^ai:generate_post$"),
            ],
            states={
                GENERATE_TOPIC: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, ai_generate_topic_input),
                ],
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


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    config = Config.load()
    application = build_application(config)
    logger.info("Starting Adsbot...")
    application.run_polling()


if __name__ == "__main__":
    run()
 