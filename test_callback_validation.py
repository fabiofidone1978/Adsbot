#!/usr/bin/env python3
"""
Callback Validation Test - Verifica che tutti i callback Telegram-only siano validi
e che i bottoni rimossi non causino errori
"""

import re
from typing import Set, Dict, List

# Patterns di callback validi per Telegram ADV marketplace
VALID_CALLBACK_PATTERNS = [
    r"^menu:",                    # Menu principale
    r"^insideads:",              # InsideAds marketplace
    r"^aigen:",                   # AI Generation
    r"^ai:",                      # AI tone/content
    r"^marketplace:",             # Marketplace operations
    r"^campaign:",                # Campaign management
    r"^offer:",                   # Offer management
    r"^purchase:",                # Purchase operations
    r"^admin:",                   # Admin operations
    r"^upgrade:",                 # Upgrade operations
    r"^goal:",                    # Goal management
    r"^noop$",                    # No operation
]

# Callback specifici rimossi che NON devono apparire
REMOVED_CALLBACKS = {
    "menu:obiettivi",
    "menu:objectives", 
    "menu:template",
    "menu:broadcast",
}

# Regex per estrarre tutti i callback_data dal codice
CALLBACK_REGEX = r'callback_data=["\']([^"\']+)["\']'

def read_bot_file() -> str:
    """Leggi il file bot.py"""
    try:
        with open("adsbot/bot.py", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("❌ File adsbot/bot.py non trovato")
        return ""

def extract_callbacks(content: str) -> Set[str]:
    """Estrai tutti i callback_data dal file"""
    matches = re.findall(CALLBACK_REGEX, content)
    return set(matches)

def validate_callback_format(callback: str) -> bool:
    """Verifica che il callback segua i pattern validi"""
    for pattern in VALID_CALLBACK_PATTERNS:
        if re.match(pattern, callback):
            return True
    return False

def check_removed_callbacks(callbacks: Set[str]) -> List[str]:
    """Verifica che i callback rimossi non siano presenti"""
    found_removed = []
    for removed in REMOVED_CALLBACKS:
        if removed in callbacks:
            found_removed.append(removed)
    return found_removed

def test_callback_consistency() -> bool:
    """Test principale di validazione callback"""
    print("=" * 60)
    print("🧪 CALLBACK VALIDATION TEST - Telegram ADV Marketplace")
    print("=" * 60)
    
    # 1. Leggi il file
    print("\n1️⃣  Leggo bot.py...")
    content = read_bot_file()
    if not content:
        return False
    print("   ✅ File letto correttamente")
    
    # 2. Estrai callback
    print("\n2️⃣  Estraggo tutti i callback_data...")
    callbacks = extract_callbacks(content)
    print(f"   ✅ Trovati {len(callbacks)} callback distinti")
    
    # 3. Valida format
    print("\n3️⃣  Valido i format dei callback...")
    invalid_callbacks = []
    for cb in callbacks:
        if not validate_callback_format(cb):
            invalid_callbacks.append(cb)
    
    if invalid_callbacks:
        print(f"   ❌ Callback non validi trovati: {invalid_callbacks}")
        return False
    print(f"   ✅ Tutti i {len(callbacks)} callback hanno format valido")
    
    # 4. Verifica bottoni rimossi
    print("\n4️⃣  Verifico che bottoni rimossi non siano presenti...")
    removed_found = check_removed_callbacks(callbacks)
    
    if removed_found:
        print(f"   ❌ Callback rimossi trovati: {removed_found}")
        return False
    print(f"   ✅ Nessun callback rimosso trovato")
    
    # 5. Stampa summary
    print("\n5️⃣  SUMMARY - Callback presenti:")
    print("   " + "-" * 56)
    
    callback_categories = {}
    for cb in sorted(callbacks):
        prefix = cb.split(":")[0]
        if prefix not in callback_categories:
            callback_categories[prefix] = []
        callback_categories[prefix].append(cb)
    
    for prefix in sorted(callback_categories.keys()):
        print(f"   📍 {prefix.upper()}: {len(callback_categories[prefix])} callback")
        for cb in sorted(callback_categories[prefix])[:3]:
            print(f"      • {cb}")
        if len(callback_categories[prefix]) > 3:
            print(f"      ... e {len(callback_categories[prefix]) - 3} altri")
    
    print("\n" + "=" * 60)
    print("✅ TUTTI I TEST PASSATI - Marketplace refactoring OK")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_callback_consistency()
    exit(0 if success else 1)
