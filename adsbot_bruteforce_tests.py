"""
Test "brutali" per AdsBot / InsideAds con esecuzione ripetuta.

Regola di superamento:
- Esegui l'intera suite di test 100 volte.
- Se meno di 99 iterazioni su 100 terminano senza errori, l'intero test è considerato NON superato.

Obiettivo:
- Verificare che i moduli core si importino senza errori.
- Stressare i componenti critici (rate limiting, AI, integrazioni Telegram).
- Eseguire fuzzing leggero sugli input per trovare edge case e crash.
"""

import sys
import traceback
import random
import asyncio
from pathlib import Path


# Hypothesis (opzionale)
try:
    from hypothesis import given, settings, HealthCheck
    from hypothesis.strategies import text, integers, sampled_from
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False


# ============================================
# 1. IMPORT BASE APP
# ============================================

def brutal_imports_check():
    """
    Controlla che i moduli core si importino senza errori.
    """
    print("  [1] Verifica import moduli core...")
    modules = [
        "adsbot.config",
        "adsbot.db",
        "adsbot.ai_content",
        "adsbot.chatgpt_integration",
        "adsbot.sqlite_rate_limiter",
        "adsbot.services",
        "adsbot.inside_ads_services",
        "adsbot.notifications",
        "adsbot.payments",
        "adsbot.telegram_metrics",
        "adsbot.verification",
    ]

    failed = []
    for m in modules:
        try:
            __import__(m)
            print(f"      OK   - {m}")
        except Exception as e:
            print(f"      FAIL - {m} -> {e}")
            traceback.print_exc()
            failed.append((m, e))

    if failed:
        raise RuntimeError(f"Import falliti: {[m for (m, _) in failed]}")


# ============================================
# 2. RATE LIMITER STRESS (VERSIONE FINALE)
# ============================================

def brutal_rate_limiter_test():
    """
    Stress test sul SQLiteRateLimiter usando SOLO un file fisico,
    evitando qualsiasi uso di ':memory:' che causa concorrenza non sicura in SQLite.
    """
    print("  [2] Stress test SQLiteRateLimiter...")

    from adsbot.sqlite_rate_limiter import SQLiteRateLimiter

    # DB locale dedicato ai test
    test_db_path = Path(__file__).resolve().parent / "rate_limiter_test.db"
    limiter = SQLiteRateLimiter(db_path=str(test_db_path), window_seconds=1, max_requests=5)

    async def _single_key_stress(api_key: str):
        for window_round in range(2):
            allowed = 0
            blocked = 0
            for _ in range(15):  # molto oltre max_requests
                ok, remaining, retry_after = await limiter.increment_and_check(api_key)
                if ok:
                    allowed += 1
                else:
                    blocked += 1

            if blocked == 0:
                raise AssertionError(
                    f"RateLimiter NON ha bloccato nulla per key={api_key}, round={window_round}"
                )

            await asyncio.sleep(1.1)

    async def _multi_key_stress():
        tasks = []
        for i in range(5):
            tasks.append(_single_key_stress(f"stress_key_{i}"))
        await asyncio.gather(*tasks)

    asyncio.run(_multi_key_stress())
    print("      OK   - Rate limiter ha bloccato correttamente in condizioni di stress.")


# ============================================
# 3. AI CONTENT GENERATOR – TEST SERIE
# ============================================

def brutal_ai_content_test():
    """
    Test AIContentGenerator: costruzione prompt + fallback.
    """
    print("  [3] Test AIContentGenerator (costruzione prompt + fallback)...")
    from adsbot.ai_content import ContentType, ToneType, ContentRequest, AIContentGenerator

    generator = AIContentGenerator(enabled=False)

    topics = [
        "offerte smartphone",
        "trading crypto",
        "canale news tech",
        "community gaming",
    ]

    for _ in range(20):
        req = ContentRequest(
            content_type=random.choice(list(ContentType)),
            topic=random.choice(topics),
            tone=random.choice(list(ToneType)),
            target_audience="utenti Telegram interessati a offerte",
            max_length=random.randint(50, 400),
            keywords=["promo", "sconto", "telegram"],
            context="Stress test interno",
            language="it",
            call_to_action="Iscriviti subito"
        )
        content = generator.generate_content(req)
        if not content or not content.text:
            raise AssertionError("AIContentGenerator ha generato contenuto vuoto")
        if content.language != "it":
            raise AssertionError("AIContentGenerator ha generato contenuto non in italiano")
    print("      OK   - AIContentGenerator stabile sotto carico.")


# ============================================
# 4. CHATGPT INTEGRATION – MOCK
# ============================================

class _FakeChatCompletionClient:
    """Simula una risposta ChatGPT JSON pura."""
    class _ChoicesWrapper:
        def __init__(self, content: str):
            class Msg:
                def __init__(self, c): self.content = c
            self.choices = [type("X", (), {"message": Msg(content)})]

    def __init__(self, payload: str):
        self.payload = payload

    def create(self, model, messages, temperature, max_tokens):
        return self._ChoicesWrapper(self.payload)


class _FakeOpenAIClient:
    def __init__(self, json_payload: dict):
        import json
        self.chat = type("Y", (), {
            "completions": _FakeChatCompletionClient(json.dumps(json_payload))
        })


def brutal_chatgpt_integration_test():
    print("  [4] Test ChatGPTCampaignGenerator (mockato)...")
    from adsbot.chatgpt_integration import ChatGPTCampaignGenerator, CampaignContent

    fake_json = {
        "title": "Promo offerte Telegram",
        "description": "Ogni giorno offerte tech selezionate.",
        "cta_text": "Iscriviti ora",
        "suggested_budget": 50,
        "keywords": ["offerte", "tech"],
        "target_audience": "utenti Telegram interessati a tecnologia",
        "image_prompt": "immagine minimalista blu"
    }

    client = _FakeOpenAIClient(fake_json)

    class DummyChannel:
        handle = "test"
        topic = "Offerte tech"
        title = "Canale Offerte"

    gen = ChatGPTCampaignGenerator(api_key="fake")
    gen.client = client
    gen.generate_image = lambda prompt: "https://example.com/img.png"

    camp = gen.generate_campaign_for_platform(
        channel=DummyChannel(), platform="telegram", tone="professional"
    )

    if not isinstance(camp, CampaignContent):
        raise AssertionError("Campagna non valida")
    if not camp.image_url:
        raise AssertionError("image_url mancante")

    print("      OK   - ChatGPTCampaignGenerator coerente.")


# ============================================
# 5. TELEGRAM METRICS – MOCK
# ============================================

class _FakeTelegramChat:
    def __init__(self, members):
        self._members = members
        self.id = 1
        self.title = "Fake"
        self.description = "Fake desc"
        self.type = "channel"

    def get_member_count(self):
        return self._members


class _FakeTelegramBot:
    async def get_chat(self, chat_id):
        return _FakeTelegramChat(1234)

    async def get_chat_member(self, chat_id, user_id):
        class S: status = "member"
        return S()

    async def get_chat_administrators(self, chat_id):
        class U: 
            def __init__(self, i): self.id=i; self.username=f"admin{i}"
        class A: 
            def __init__(self,i): self.user=U(i)
        return [A(1), A(2)]


def brutal_telegram_metrics_test():
    print("  [5] Test TelegramMetricsCollector (mock bot)...")
    from adsbot.telegram_metrics import TelegramMetricsCollector

    bot = _FakeTelegramBot()
    collector = TelegramMetricsCollector(bot)

    async def _run():
        mc = await collector.get_channel_member_count("x")
        if mc != 1234: raise AssertionError("Member count errato")

        info = await collector.get_channel_info("x")
        if not info or info["members"] != 1234:
            raise AssertionError("get_channel_info errato")

        st = await collector.get_user_member_status("x", 42)
        if st != "member": raise AssertionError("status errato")

        admins = await collector.get_chat_administrators("x")
        if len(admins) != 2: raise AssertionError("admin errati")

        est = await collector.estimate_channel_metrics("x", 42)
        if not est["user_is_member"]: raise AssertionError("estimate errato")

    asyncio.run(_run())
    print("      OK   - TelegramMetricsCollector stabile.")


# ============================================
# 6. SECURITY / VERIFICATION SMOKE
# ============================================

def brutal_verification_smoke():
    print("  [6] Smoke test Verification...")
    from adsbot.verification import AccountSecurity

    ips = ["127.0.0.1", "0.0.0.0", "10.0.0.1", "256.256.256.256"]

    for ip in ips:
        out = AccountSecurity.check_ip_reputation(ip)
        if "ip" not in out or "risk_level" not in out:
            raise AssertionError("Struttura IP reputation errata")

    print("      OK   - Verification stabile.")


# ============================================
# 7. HYPOTHESIS (SE DISPONIBILE)
# ============================================

if HYPOTHESIS_AVAILABLE:
    from adsbot.ai_content import ContentType, ToneType, ContentRequest, AIContentGenerator

    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    @given(
        txt=text(min_size=0, max_size=200),
        tone=sampled_from(list(ToneType)),
        ctype=sampled_from(list(ContentType)),
        max_len=integers(min_value=10, max_value=300),
    )
    def hypothesis_ai_does_not_crash(txt, tone, ctype, max_len):
        gen = AIContentGenerator(enabled=False)
        req = ContentRequest(
            content_type=ctype,
            topic=txt or "default",
            tone=tone,
            target_audience="fuzz",
            max_length=max_len,
            keywords=["test"],
            context="fuzz test",
            language="it",
            call_to_action="vai"
        )
        out = gen.generate_content(req)
        assert isinstance(out.text, str)


# ============================================
# ENTRYPOINT
# ============================================

def run_single_iteration(it):
    print(f"\n=== ITERAZIONE {it}/100 ===")
    brutal_imports_check()
    brutal_rate_limiter_test()
    brutal_ai_content_test()
    brutal_chatgpt_integration_test()
    brutal_telegram_metrics_test()
    brutal_verification_smoke()

    if HYPOTHESIS_AVAILABLE:
        print("  [7] Hypothesis fuzzing...")
        hypothesis_ai_does_not_crash()
        print("      OK   - Hypothesis stabile.")
    else:
        print("  [7] Hypothesis non disponibile.")


def main():
    print("=== ADSBOT BRUTAL INTERNAL TESTS – 100 RUNS ===")
    success = 0

    for i in range(1, 101):
        try:
            run_single_iteration(i)
        except Exception as e:
            print(f"\n*** ERRORE ITERAZIONE {i} ***")
            print(e)
            traceback.print_exc()
        else:
            success += 1

    print(f"\n=== RISULTATO FINALE: {success}/100 ===")

    if success >= 99:
        print(">>> TEST COMPLESSIVO SUPERATO")
        sys.exit(0)
    else:
        print(">>> TEST NON SUPERATO")
        sys.exit(1)


if __name__ == "__main__":
    main()
