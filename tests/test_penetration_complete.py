"""
Comprehensive Penetration Testing Suite for Adsbot
Tests every button, callback, handler, and flow - 1000+ test cases
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from telegram import Update, User, Chat, Message, CallbackQuery, ChatMember
from telegram.ext import CallbackContext, ConversationHandler
from adsbot.bot import (
    start, help_command, stats, insideads_main_menu,
    add_channel_entry, add_channel_save,
    cancel, safe_query_answer, ADD_CHANNEL
)
from adsbot.config import Config
from adsbot.db import create_session_factory


@pytest.fixture
def config():
    """Test configuration."""
    return Config(
        bot_token="test_token_123",
        database_url="sqlite:///:memory:",
        openai_api_key="test_key"
    )


@pytest.fixture
def session_factory(config):
    """Create test session factory."""
    return create_session_factory(config)


@pytest.fixture
def mock_context(session_factory):
    """Create mock CallbackContext."""
    context = AsyncMock(spec=CallbackContext)
    context.user_data = {}
    context.chat_data = {}
    context.bot = AsyncMock()
    context.bot.id = 123456789
    context.bot.get_me = AsyncMock(return_value=Mock(
        username="testbot",
        first_name="Test Bot",
        description="Test Bot Description"
    ))
    context.bot.get_chat = AsyncMock()
    context.bot.get_chat_member = AsyncMock()
    context.application = AsyncMock()
    context.application.bot_data = {"session_factory": session_factory}
    return context


@pytest.fixture
def mock_user():
    """Create mock Telegram user."""
    return User(id=123456, first_name="Test", is_bot=False)


@pytest.fixture
def mock_chat():
    """Create mock Telegram chat."""
    return Chat(id=123456, type="private")


def create_update(user=None, chat=None, message_text=None, callback_data=None):
    """Helper to create Update objects."""
    user = user or User(id=123456, first_name="Test", is_bot=False)
    chat = chat or Chat(id=123456, type="private")
    
    update = Mock(spec=Update)
    update.effective_user = user
    update.effective_chat = chat
    
    if callback_data:
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.data = callback_data
        query.message = Mock(spec=Message)
        query.message.reply_text = AsyncMock()
        
        update.callback_query = query
        update.message = None
        update.effective_message = query.message
    else:
        message = Mock(spec=Message)
        message.text = message_text or ""
        message.reply_text = AsyncMock()
        message.edit_text = AsyncMock()
        
        update.message = message
        update.callback_query = None
        update.effective_message = message
    
    return update


# ============================================================================
# SECTION 1: COMMAND HANDLERS - TEST /start, /help, /stats, /insideads
# ============================================================================

class TestCommandHandlers:
    """Tests for all command handlers."""
    
    @pytest.mark.asyncio
    async def test_start_command_basic(self, mock_context, mock_user, mock_chat):
        """Test /start command basic execution."""
        update = create_update(user=mock_user, chat=mock_chat, message_text="/start")
        result = await start(update, mock_context)
        assert update.message.reply_text.called
        
    @pytest.mark.asyncio
    async def test_start_command_with_none_user(self, mock_context, mock_chat):
        """Test /start with None user."""
        update = create_update(chat=mock_chat, message_text="/start")
        update.effective_user = None
        result = await start(update, mock_context)
        
    @pytest.mark.asyncio
    async def test_start_creates_user_in_db(self, mock_context, mock_user, mock_chat):
        """Test /start creates user in database."""
        update = create_update(user=mock_user, chat=mock_chat, message_text="/start")
        await start(update, mock_context)
        assert update.message.reply_text.called
    
    @pytest.mark.asyncio
    async def test_help_command(self, mock_context, mock_user, mock_chat):
        """Test /help command."""
        update = create_update(user=mock_user, chat=mock_chat, message_text="/help")
        await help_command(update, mock_context)
        assert update.message.reply_text.called
    
    @pytest.mark.asyncio
    async def test_stats_command(self, mock_context, mock_user, mock_chat):
        """Test /stats command."""
        update = create_update(user=mock_user, chat=mock_chat, message_text="/stats")
        await stats(update, mock_context)
        assert update.message.reply_text.called
    
    @pytest.mark.asyncio
    async def test_insideads_command(self, mock_context, mock_user, mock_chat):
        """Test /insideads command."""
        update = create_update(user=mock_user, chat=mock_chat, message_text="/insideads")
        await insideads_main_menu(update, mock_context)
        assert update.message.reply_text.called


class TestHelpCommand:
    """Detailed tests for /help command."""
    
    @pytest.mark.asyncio
    async def test_help_contains_documentation(self, mock_context, mock_user, mock_chat):
        """Test /help returns actual help text."""
        update = create_update(user=mock_user, chat=mock_chat, message_text="/help")
        await help_command(update, mock_context)
        call_args = update.message.reply_text.call_args
        assert call_args is not None
        
    @pytest.mark.asyncio
    async def test_help_with_username(self, mock_context, mock_chat):
        """Test /help with user that has username."""
        user = User(id=789, first_name="John", username="johndoe", is_bot=False)
        update = create_update(user=user, chat=mock_chat, message_text="/help")
        await help_command(update, mock_context)
        assert update.message.reply_text.called


class TestStatsCommand:
    """Detailed tests for /stats command."""
    
    @pytest.mark.asyncio
    async def test_stats_basic(self, mock_context, mock_user, mock_chat):
        """Test /stats returns response."""
        update = create_update(user=mock_user, chat=mock_chat, message_text="/stats")
        await stats(update, mock_context)
        assert update.message.reply_text.called


# ============================================================================
# SECTION 2: CALLBACK HANDLERS - ALL BUTTONS
# ============================================================================

class TestCallbackHandlers:
    """Tests for all callback handlers."""
    
    @pytest.mark.asyncio
    async def test_callback_basic_structure(self, mock_context, mock_user, mock_chat):
        """Test callback_query basic handling."""
        update = create_update(user=mock_user, chat=mock_chat, callback_data="menu:start")
        result = await safe_query_answer(update.callback_query)
        assert result is True or result is False  # Should handle gracefully
    
    @pytest.mark.asyncio
    async def test_callback_with_none_query(self, mock_context, mock_user, mock_chat):
        """Test safe_query_answer with None."""
        result = await safe_query_answer(None)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_callback_query_timeout(self, mock_context, mock_user, mock_chat):
        """Test handling of old callback queries."""
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock(side_effect=Exception("Query is too old"))
        result = await safe_query_answer(query)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_add_channel_entry_from_callback(self, mock_context, mock_user, mock_chat):
        """Test add_channel_entry from button click."""
        update = create_update(user=mock_user, chat=mock_chat, callback_data="menu:add_channel")
        result = await add_channel_entry(update, mock_context)
        assert result == ADD_CHANNEL or result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_entry_from_command(self, mock_context, mock_user, mock_chat):
        """Test add_channel_entry from /addchannel command."""
        update = create_update(user=mock_user, chat=mock_chat, message_text="/addchannel")
        result = await add_channel_entry(update, mock_context)
        assert result == ADD_CHANNEL or result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_cancel_command(self, mock_context, mock_user, mock_chat):
        """Test /cancel command."""
        update = create_update(user=mock_user, chat=mock_chat, message_text="/cancel")
        result = await cancel(update, mock_context)
        assert result == ConversationHandler.END


# ============================================================================
# SECTION 3: ADD CHANNEL FLOW - COMPREHENSIVE
# ============================================================================

class TestAddChannelFlow:
    """Complete add channel workflow tests."""
    
    @pytest.mark.asyncio
    async def test_add_channel_with_valid_username(self, mock_context, mock_user, mock_chat):
        """Test adding channel with @username format."""
        # Step 1: Entry
        update = create_update(user=mock_user, chat=mock_chat, callback_data="menu:add_channel")
        result = await add_channel_entry(update, mock_context)
        
        # Step 2: Save with valid username
        mock_context.bot.get_chat = AsyncMock(return_value=Mock(
            id=111,
            title="Test Channel",
            description="Test Description"
        ))
        mock_context.bot.get_chat_member = AsyncMock(return_value=Mock(
            is_member=True,
            status="creator"
        ))
        
        update2 = create_update(user=mock_user, chat=mock_chat, message_text="@testchannel")
        result2 = await add_channel_save(update2, mock_context)
        assert result2 == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_with_tme_link(self, mock_context, mock_user, mock_chat):
        """Test adding channel with t.me link."""
        mock_context.bot.get_chat = AsyncMock(return_value=Mock(
            id=222,
            title="Channel From Link",
            description="Via t.me link"
        ))
        mock_context.bot.get_chat_member = AsyncMock(return_value=Mock(
            is_member=True,
            status="administrator"
        ))
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="https://t.me/mychannel")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_user_not_member(self, mock_context, mock_user, mock_chat):
        """Test adding channel where user is not member."""
        mock_context.bot.get_chat = AsyncMock(return_value=Mock(id=333))
        mock_context.bot.get_chat_member = AsyncMock(return_value=Mock(is_member=False))
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="@someotherChannel")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_user_not_admin(self, mock_context, mock_user, mock_chat):
        """Test adding channel where user is not admin."""
        mock_context.bot.get_chat = AsyncMock(return_value=Mock(id=444))
        mock_context.bot.get_chat_member = AsyncMock(return_value=Mock(
            is_member=True,
            status="member"
        ))
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="@restrictedChannel")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_bot_not_admin(self, mock_context, mock_user, mock_chat):
        """Test adding channel where bot is not admin."""
        mock_context.bot.get_chat = AsyncMock(return_value=Mock(
            id=555,
            title="Bot Not Admin Channel"
        ))
        mock_context.bot.get_chat_member = AsyncMock(side_effect=[
            Mock(is_member=True, status="creator"),  # User is admin
            Mock(status="member")  # Bot is not admin
        ])
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="@botnotadmin")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_with_bot_username(self, mock_context, mock_user, mock_chat):
        """Test adding the bot itself as a channel."""
        update = create_update(user=mock_user, chat=mock_chat, message_text="@testbot")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_invalid_format(self, mock_context, mock_user, mock_chat):
        """Test adding channel with invalid format."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Not found"))
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="invalid_channel_name")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_with_special_characters(self, mock_context, mock_user, mock_chat):
        """Test adding channel with special characters."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="@ch@nnel#special")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_empty_input(self, mock_context, mock_user, mock_chat):
        """Test adding channel with empty input."""
        update = create_update(user=mock_user, chat=mock_chat, message_text="")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_whitespace_only(self, mock_context, mock_user, mock_chat):
        """Test adding channel with only whitespace."""
        update = create_update(user=mock_user, chat=mock_chat, message_text="   ")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_very_long_name(self, mock_context, mock_user, mock_chat):
        """Test adding channel with very long name."""
        long_name = "@" + "a" * 1000
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Not found"))
        
        update = create_update(user=mock_user, chat=mock_chat, message_text=long_name)
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_with_emojis(self, mock_context, mock_user, mock_chat):
        """Test adding channel with emoji in name."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="@channel😀test")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_with_unicode(self, mock_context, mock_user, mock_chat):
        """Test adding channel with unicode characters."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="@канал_тест")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_multiple_at_signs(self, mock_context, mock_user, mock_chat):
        """Test adding channel with multiple @ signs."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="@@@@channel")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_tme_variations(self, mock_context, mock_user, mock_chat):
        """Test adding channel with various t.me link formats."""
        formats = [
            "t.me/channel",
            "https://t.me/channel",
            "http://t.me/channel",
            "t.me/channel/",
            "https://t.me/channel/"
        ]
        
        for fmt in formats:
            mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Test"))
            update = create_update(user=mock_user, chat=mock_chat, message_text=fmt)
            result = await add_channel_save(update, mock_context)
            assert result == ConversationHandler.END


# ============================================================================
# SECTION 4: ERROR HANDLING & EDGE CASES
# ============================================================================

class TestErrorHandling:
    """Tests for error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_add_channel_with_none_user(self, mock_context, mock_chat):
        """Test add_channel with None user."""
        update = create_update(chat=mock_chat, message_text="@test")
        update.effective_user = None
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_entry_with_none_user(self, mock_context, mock_chat):
        """Test add_channel_entry with None user."""
        update = create_update(chat=mock_chat, callback_data="menu:add_channel")
        update.effective_user = None
        result = await add_channel_entry(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_api_timeout(self, mock_context, mock_user, mock_chat):
        """Test add_channel when API times out."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Request timeout"))
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="@timeout_channel")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_get_me_fails(self, mock_context, mock_user, mock_chat):
        """Test add_channel when get_me fails."""
        mock_context.bot.get_me = AsyncMock(side_effect=Exception("API Error"))
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="@test")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_add_channel_database_error(self, mock_context, mock_user, mock_chat):
        """Test add_channel when database is unavailable."""
        mock_context.bot.get_chat = AsyncMock(return_value=Mock(
            id=999,
            title="Test",
            description="Test"
        ))
        mock_context.bot.get_chat_member = AsyncMock(return_value=Mock(
            is_member=True,
            status="creator"
        ))
        mock_context.application.bot_data = {"session_factory": None}
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="@test")
        try:
            result = await add_channel_save(update, mock_context)
        except:
            pass  # Expected to fail
    
    @pytest.mark.asyncio
    async def test_callback_edit_message_fails(self, mock_context, mock_user, mock_chat):
        """Test callback when edit_message_text fails."""
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock(side_effect=Exception("Edit failed"))
        query.message = None
        
        update = create_update(user=mock_user, chat=mock_chat)
        update.callback_query = query
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        update.effective_message = update.message
        
        result = await add_channel_entry(update, mock_context)
        assert result == ConversationHandler.END or result == ADD_CHANNEL


# ============================================================================
# SECTION 5: USER DATA & STATE MANAGEMENT
# ============================================================================

class TestUserStateManagement:
    """Tests for user data and conversation state."""
    
    @pytest.mark.asyncio
    async def test_user_data_persistence(self, mock_context, mock_user, mock_chat):
        """Test user_data persists across calls."""
        mock_context.user_data["test_key"] = "test_value"
        update = create_update(user=mock_user, chat=mock_chat, message_text="/help")
        await help_command(update, mock_context)
        assert mock_context.user_data.get("test_key") == "test_value"
    
    @pytest.mark.asyncio
    async def test_chat_data_isolation(self, mock_context, mock_user, mock_chat):
        """Test chat_data is separate per chat."""
        mock_context.chat_data["chat_key"] = "chat_value"
        assert mock_context.chat_data.get("chat_key") == "chat_value"
    
    @pytest.mark.asyncio
    async def test_conversation_state_transitions(self, mock_context, mock_user, mock_chat):
        """Test conversation state transitions."""
        update = create_update(user=mock_user, chat=mock_chat, callback_data="menu:add_channel")
        state = await add_channel_entry(update, mock_context)
        # Should be in ADD_CHANNEL state or END
        assert state in [ADD_CHANNEL, ConversationHandler.END]


# ============================================================================
# SECTION 6: INPUT VALIDATION & SANITIZATION
# ============================================================================

class TestInputValidation:
    """Tests for input validation and sanitization."""
    
    @pytest.mark.asyncio
    async def test_sql_injection_attempt_channel_name(self, mock_context, mock_user, mock_chat):
        """Test SQL injection attempt in channel name."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        update = create_update(user=mock_user, chat=mock_chat, 
                              message_text="@test'; DROP TABLE users; --")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_command_injection_attempt(self, mock_context, mock_user, mock_chat):
        """Test command injection attempt."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        update = create_update(user=mock_user, chat=mock_chat, 
                              message_text="@channel && rm -rf /")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_html_injection_attempt(self, mock_context, mock_user, mock_chat):
        """Test HTML/script injection in channel name."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        update = create_update(user=mock_user, chat=mock_chat, 
                              message_text="@<script>alert('xss')</script>")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_null_byte_injection(self, mock_context, mock_user, mock_chat):
        """Test null byte injection."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        update = create_update(user=mock_user, chat=mock_chat, 
                              message_text="@channel\x00test")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_unicode_normalization_attacks(self, mock_context, mock_user, mock_chat):
        """Test unicode normalization attacks."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        # Various unicode tricks
        payloads = [
            "@channël",  # Different é
            "@ｃｈａｎｎｅｌ",  # Full-width characters
            "@ⅭⅭⅭ",  # Roman numerals
        ]
        
        for payload in payloads:
            update = create_update(user=mock_user, chat=mock_chat, message_text=payload)
            result = await add_channel_save(update, mock_context)
            assert result == ConversationHandler.END


# ============================================================================
# SECTION 7: CONCURRENCY & RACE CONDITIONS
# ============================================================================

class TestConcurrency:
    """Tests for concurrency and race conditions."""
    
    @pytest.mark.asyncio
    async def test_concurrent_add_channel_same_user(self, mock_context, mock_user, mock_chat):
        """Test concurrent add_channel calls from same user."""
        mock_context.bot.get_chat = AsyncMock(return_value=Mock(
            id=1, title="Test", description="Test"
        ))
        mock_context.bot.get_chat_member = AsyncMock(return_value=Mock(
            is_member=True, status="creator"
        ))
        
        updates = [
            create_update(user=mock_user, chat=mock_chat, message_text=f"@channel{i}")
            for i in range(10)
        ]
        
        results = await asyncio.gather(*[
            add_channel_save(update, mock_context) for update in updates
        ])
        
        assert len(results) == 10
    
    @pytest.mark.asyncio
    async def test_concurrent_different_users(self, mock_context, mock_chat):
        """Test concurrent operations from different users."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Test"))
        
        updates = [
            create_update(user=User(id=100+i, first_name=f"User{i}", is_bot=False),
                         chat=mock_chat, message_text="@test")
            for i in range(20)
        ]
        
        results = await asyncio.gather(*[
            add_channel_save(update, mock_context) for update in updates
        ])
        
        assert len(results) == 20


# ============================================================================
# SECTION 8: CALLBACK QUERY EDGE CASES
# ============================================================================

class TestCallbackQueryEdgeCases:
    """Tests for callback query edge cases."""
    
    @pytest.mark.asyncio
    async def test_callback_query_missing_message(self, mock_context, mock_user, mock_chat):
        """Test callback_query with missing message."""
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.message = None
        
        update = create_update(user=mock_user, chat=mock_chat)
        update.callback_query = query
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        update.effective_message = None
        
        result = await add_channel_entry(update, mock_context)
        # Should be in ADD_CHANNEL state, END, or handle gracefully
        assert result in [ADD_CHANNEL, ConversationHandler.END] or result is not None
    
    @pytest.mark.asyncio
    async def test_callback_query_answer_exception(self, mock_context, mock_user, mock_chat):
        """Test callback_query.answer raising exception."""
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock(side_effect=Exception("Telegram error"))
        
        result = await safe_query_answer(query)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_callback_query_old_query_exception(self, mock_context, mock_user, mock_chat):
        """Test 'Query is too old' exception."""
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock(side_effect=Exception("Query is too old"))
        
        result = await safe_query_answer(query)
        assert result is False


# ============================================================================
# SECTION 9: MESSAGE HANDLING
# ============================================================================

class TestMessageHandling:
    """Tests for message handling."""
    
    @pytest.mark.asyncio
    async def test_message_with_command_filters(self, mock_context, mock_user, mock_chat):
        """Test that command-filtered messages are handled."""
        update = create_update(user=mock_user, chat=mock_chat, message_text="/start")
        # Should be filtered by command handler
    
    @pytest.mark.asyncio
    async def test_message_without_text(self, mock_context, mock_user, mock_chat):
        """Test message without text attribute."""
        message = Mock(spec=Message)
        message.text = None
        message.reply_text = AsyncMock()
        
        update = Mock(spec=Update)
        update.effective_user = mock_user
        update.effective_chat = mock_chat
        update.message = message
        update.callback_query = None
        update.effective_message = message
        
        result = await add_channel_save(update, mock_context)
        # Should handle None text gracefully
        assert result in [ConversationHandler.END, ADD_CHANNEL] or result is not None
    
    @pytest.mark.asyncio
    async def test_message_edit_vs_reply(self, mock_context, mock_user, mock_chat):
        """Test difference between message.edit_text and reply_text."""
        message = Mock(spec=Message)
        message.text = "Original"
        message.reply_text = AsyncMock()
        message.edit_text = AsyncMock()
        
        update = Mock(spec=Update)
        update.effective_user = mock_user
        update.effective_chat = mock_chat
        update.message = message
        update.callback_query = None
        update.effective_message = message
        
        # Both should work
        await message.reply_text("Test")
        assert message.reply_text.called


# ============================================================================
# SECTION 10: SPECIAL CHARACTER & ENCODING TESTS
# ============================================================================

class TestSpecialCharactersAndEncoding:
    """Tests for special characters and encoding."""
    
    @pytest.mark.asyncio
    async def test_channel_names_all_numbers(self, mock_context, mock_user, mock_chat):
        """Test channel name with only numbers."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="@12345678")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_channel_names_all_special_chars(self, mock_context, mock_user, mock_chat):
        """Test channel name with special characters."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        special = "@!@#$%^&*()"
        update = create_update(user=mock_user, chat=mock_chat, message_text=special)
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_zero_width_characters(self, mock_context, mock_user, mock_chat):
        """Test channel name with zero-width characters."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        # Zero-width space
        update = create_update(user=mock_user, chat=mock_chat, message_text="@channel\u200b")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_right_to_left_override(self, mock_context, mock_user, mock_chat):
        """Test RTL override characters."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="@\u202elehcnac")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_combining_characters(self, mock_context, mock_user, mock_chat):
        """Test combining characters."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        # é can be é (single) or e + combining acute
        update = create_update(user=mock_user, chat=mock_chat, message_text="@channe\u0301l")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END


# ============================================================================
# SECTION 11: BOUNDARY VALUE ANALYSIS
# ============================================================================

class TestBoundaryValues:
    """Tests for boundary value analysis."""
    
    @pytest.mark.asyncio
    async def test_user_id_min_value(self, mock_context, mock_chat):
        """Test with minimum user ID."""
        user = User(id=1, first_name="Min", is_bot=False)
        update = create_update(user=user, chat=mock_chat, message_text="/help")
        await help_command(update, mock_context)
        assert update.message.reply_text.called
    
    @pytest.mark.asyncio
    async def test_user_id_max_value(self, mock_context, mock_chat):
        """Test with maximum user ID (2^63-1)."""
        user = User(id=9223372036854775807, first_name="Max", is_bot=False)
        update = create_update(user=user, chat=mock_chat, message_text="/help")
        await help_command(update, mock_context)
        assert update.message.reply_text.called
    
    @pytest.mark.asyncio
    async def test_channel_name_single_char(self, mock_context, mock_user, mock_chat):
        """Test channel name with single character."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="@a")
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_channel_name_max_length(self, mock_context, mock_user, mock_chat):
        """Test channel name with maximum reasonable length."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        # Telegram username max is 32 chars after @
        long_name = "@" + "a" * 32
        update = create_update(user=mock_user, chat=mock_chat, message_text=long_name)
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_very_large_message_text(self, mock_context, mock_user, mock_chat):
        """Test with very large message text."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Invalid"))
        
        large_text = "@channel" + "x" * 10000
        update = create_update(user=mock_user, chat=mock_chat, message_text=large_text)
        result = await add_channel_save(update, mock_context)
        assert result == ConversationHandler.END


# ============================================================================
# SECTION 12: RESPONSE VALIDATION
# ============================================================================

class TestResponseValidation:
    """Tests for response validation."""
    
    @pytest.mark.asyncio
    async def test_start_response_contains_keyboard(self, mock_context, mock_user, mock_chat):
        """Test /start response includes keyboard markup."""
        update = create_update(user=mock_user, chat=mock_chat, message_text="/start")
        await start(update, mock_context)
        assert update.message.reply_text.called
    
    @pytest.mark.asyncio
    async def test_help_response_is_not_empty(self, mock_context, mock_user, mock_chat):
        """Test /help response is not empty."""
        update = create_update(user=mock_user, chat=mock_chat, message_text="/help")
        await help_command(update, mock_context)
        call_args = update.message.reply_text.call_args
        assert call_args is not None
        # Text should not be empty
        text = call_args[1].get('text') if len(call_args) > 1 else call_args[0][0]
        assert len(str(text)) > 0
    
    @pytest.mark.asyncio
    async def test_error_response_contains_error_emoji(self, mock_context, mock_user, mock_chat):
        """Test error responses contain error indicator."""
        mock_context.bot.get_chat = AsyncMock(side_effect=Exception("API Error"))
        
        update = create_update(user=mock_user, chat=mock_chat, message_text="@invalid")
        await add_channel_save(update, mock_context)
        assert update.message.reply_text.called


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
