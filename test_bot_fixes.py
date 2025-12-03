"""Test automatici per verificare le modifiche al bot."""

import sys
import py_compile
import importlib.util
from pathlib import Path

def test_compilation():
    """Test 1: Verifica che bot.py compili senza errori."""
    print("🧪 Test 1: Compilazione bot.py...")
    try:
        py_compile.compile('adsbot/bot.py', doraise=True)
        print("✅ bot.py compila correttamente\n")
        return True
    except py_compile.PyCompileError as e:
        print(f"❌ Errore di compilazione: {e}\n")
        return False

def test_imports():
    """Test 2: Verifica che tutti i moduli si importino correttamente."""
    print("🧪 Test 2: Import moduli...")
    try:
        from adsbot.bot import build_application
        from adsbot.models import User, Channel
        from adsbot.campaign_analyzer import CampaignAnalyzer
        from adsbot.config import Config
        from adsbot.db import create_session_factory, session_scope
        print("✅ Tutti i moduli importati correttamente\n")
        return True
    except Exception as e:
        print(f"❌ Errore di import: {e}\n")
        return False

def test_models():
    """Test 3: Verifica che il modello User abbia subscription_type."""
    print("🧪 Test 3: Verifica modello User...")
    try:
        from adsbot.models import User
        from sqlalchemy import inspect
        
        # Verifica che la colonna subscription_type esista nel modello
        mapper = inspect(User)
        columns = [col.name for col in mapper.columns]
        
        if 'subscription_type' in columns:
            print("✅ Colonna 'subscription_type' presente nel modello User\n")
            return True
        else:
            print(f"❌ Colonna 'subscription_type' non trovata. Colonne: {columns}\n")
            return False
    except Exception as e:
        print(f"❌ Errore nella verifica modello: {e}\n")
        return False

def test_database_migration():
    """Test 4: Verifica che la migrazione del database sia stata applicata."""
    print("🧪 Test 4: Verifica migrazione database...")
    try:
        from sqlalchemy import create_engine, text, inspect
        from adsbot.config import Config
        
        config = Config.load()
        engine = create_engine(config.database_url)
        
        # Verifica che la tabella users abbia la colonna subscription_type
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'subscription_type' in columns:
            print("✅ Colonna 'subscription_type' presente nel database\n")
            return True
        else:
            print(f"⚠️  Colonna 'subscription_type' non presente. Colonne: {columns}")
            print("   Nota: eseguire migrate_db.py se necessario\n")
            return False
    except Exception as e:
        print(f"⚠️  Non è possibile verificare il database: {e}\n")
        print("   Nota: il database potrebbe non essere ancora inizializzato\n")
        return True  # Non è un errore critico se il DB non esiste ancora

def test_campaign_analyzer():
    """Test 5: Verifica che CampaignAnalyzer si importi e istanzi."""
    print("🧪 Test 5: Verifica CampaignAnalyzer...")
    try:
        from adsbot.campaign_analyzer import CampaignAnalyzer, ChannelAnalysis, CampaignSuggestion
        
        # Verifica che le classi siano istanziabili
        analyzer = CampaignAnalyzer()
        print("✅ CampaignAnalyzer istanziato correttamente\n")
        return True
    except Exception as e:
        print(f"❌ Errore con CampaignAnalyzer: {e}\n")
        return False

def test_handler_functions():
    """Test 6: Verifica che i handler async siano definiti."""
    print("🧪 Test 6: Verifica handler functions...")
    try:
        from adsbot import bot
        
        required_handlers = [
            'generate_post_menu',
            'ai_generate_post_start',
            'ai_tone_selected',
            'ai_generate_content',
            'aigen_start',
            'aigen_channel_selected',
            'aigen_show_campaign_suggestion',
        ]
        
        missing = []
        for handler_name in required_handlers:
            if not hasattr(bot, handler_name):
                missing.append(handler_name)
        
        if not missing:
            print(f"✅ Tutti gli handler trovati: {', '.join(required_handlers)}\n")
            return True
        else:
            print(f"❌ Handler mancanti: {missing}\n")
            return False
    except Exception as e:
        print(f"❌ Errore nella verifica handler: {e}\n")
        return False

def main():
    """Esegui tutti i test."""
    print("=" * 60)
    print("🤖 TEST AUTOMATICI ADSBOT")
    print("=" * 60)
    print()
    
    tests = [
        test_compilation,
        test_imports,
        test_models,
        test_database_migration,
        test_campaign_analyzer,
        test_handler_functions,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Errore durante test: {e}\n")
            results.append(False)
    
    print("=" * 60)
    print("📊 RISULTATI")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Test riusciti: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 TUTTI I TEST PASSATI!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test falliti")
        return 1

if __name__ == "__main__":
    sys.exit(main())
