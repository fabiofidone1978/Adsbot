"""
Test E2E per Adsbot / InsideAds orientati a:
- DB (SQLite locale)
- business logic InsideAds (campagne, bilanci, transazioni)
- flusso "advertiser compra spazio ADV su canale"
- generazione notifiche (senza chiamare Telegram reale)

Regola di superamento:
- Esegui N iterazioni (default 20).
- Tutte devono chiudere senza errori / assert.
"""

import sys
import traceback
from pathlib import Path
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from adsbot.db import Base
from adsbot.models import User, Channel, UserBalance, Transaction, AdvertisementMetrics
from adsbot.inside_ads_services import (
    get_or_create_balance,
    add_transaction,
    get_recent_transactions,
    create_campaign_purchase,
    get_campaign_performance,
)
from adsbot.notifications import NotificationSender, NotificationType


# ========================================================
# 1. SETUP DB DI TEST (ISOLATO DA QUELLO DI PRODUZIONE)
# ========================================================

TEST_DB_PATH = Path(__file__).resolve().parent / "adsbot_e2e_test.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

engine = create_engine(TEST_DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)


def init_schema():
    """Drop & create schema per un run pulito."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


# ========================================================
# 2. FINTA NOTIFICA TELEGRAM (NO CHIAMATE REALI)
# ========================================================

class FakeBot:
    """Mock del Bot Telegram: registra solo messaggi invece di inviarli."""
    def __init__(self):
        self.sent_messages = []

    async def send_message(self, chat_id, text, parse_mode=None):
        # Nessuna rete: solo log in memoria
        self.sent_messages.append(
            {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        )
        return True


def build_notification_sender(fake_bot: FakeBot) -> NotificationSender:
    return NotificationSender(bot=fake_bot)


# ========================================================
# 3. SCENARIO E2E PRINCIPALE
# ========================================================

def run_single_e2e_scenario(iteration: int):
    """
    Scenario E2E:
    - crea advertiser e seller
    - crea channel del seller
    - accredita fondi all'advertiser
    - esegue create_campaign_purchase
    - controlla bilanci e transazioni
    - simula metriche e legge get_campaign_performance
    - genera notifiche "Earnings Received" e "Campaign Purchased"
    """

    print(f"\n=== E2E BUSINESS ITERAZIONE {iteration} ===")

    init_schema()
    session = SessionLocal()

    # -----------------------------
    # 1. CREA UTENTI BASE
    # -----------------------------
    advertiser = User(
        telegram_id=1001,
        username="advertiser_test",
        full_name="Advertiser Test",
        is_verified=True,
    )
    seller = User(
        telegram_id=2001,
        username="seller_test",
        full_name="Seller Test",
        is_verified=True,
    )
    session.add_all([advertiser, seller])
    session.commit()

    # -----------------------------
    # 2. CREA CANALE DEL SELLER
    # -----------------------------
    seller_channel = Channel(
        user_id=seller.id,
        handle="seller_channel_test",
        title="Canale Seller Test",
        description="Canale per test E2E",
        subscribers=5000,
        is_verified=True,
    )
    session.add(seller_channel)
    session.commit()

    # -----------------------------
    # 3. BILANCIO ADVERTISER: ACCREDITO INIZIALE
    # -----------------------------
    adv_balance = get_or_create_balance(session, advertiser)
    # Accredita 500 come deposito di test
    add_transaction(
        session,
        advertiser,
        transaction_type="deposit",
        amount=500.0,
        description="Test initial deposit",
        reference_id=None,
    )
    session.refresh(adv_balance)
    if adv_balance.balance < 500 - 1e-6:
        raise AssertionError("Bilancio advertiser non allineato dopo deposito iniziale")

    # -----------------------------
    # 4. ESEGUI CAMPAGNA: ADVERTISER COMPRA SPAZIO SUL CANALE SELLER
    # -----------------------------
    budget = 120.0
    result = create_campaign_purchase(
        session=session,
        buyer=advertiser,
        seller_channel=seller_channel,
        campaign_name="Campagna Test E2E",
        budget=budget,
        duration_days=7,
    )

    if result is None:
        raise AssertionError("create_campaign_purchase ha restituito None (fondi insufficienti?)")

    # Dopo l'acquisto:
    # - advertiser deve avere budget scalato
    # - seller deve avere una quota (80% del budget)
    adv_balance = get_or_create_balance(session, advertiser)
    seller_balance = get_or_create_balance(session, seller)

    expected_seller_earning = budget * 0.8

    if adv_balance.balance > 500.0 - 1e-6:
        raise AssertionError("Bilancio advertiser non scalato dopo acquisto campagna")

    if seller_balance.balance < expected_seller_earning - 1e-6:
        raise AssertionError("Bilancio seller non aggiornato con revenue da campagna")

    # -----------------------------
    # 5. CONTROLLA TRANSAZIONI
    # -----------------------------
    adv_tx = get_recent_transactions(session, advertiser, days=1)
    seller_tx = get_recent_transactions(session, seller, days=1)

    if not adv_tx or not seller_tx:
        raise AssertionError("Transazioni mancanti dopo acquisto campagna")

    # -----------------------------
    # 6. SIMULA METRICHE CAMPAGNA + PERFORMANCE
    # -----------------------------
    # Per semplicità: assegniamo una campagna esistente a cui appendere metriche.
    # Prendiamo l'ultima campagna creata.
    campaign = session.query(Transaction).filter_by(user_id=advertiser.id).order_by(Transaction.created_at.desc()).first()
    # NOTE: qui non abbiamo un ID campagna diretto da create_campaign_purchase (non lo restituisce),
    # quindi per questo test creiamo manualmente una campagna fittizia se necessario.
    from adsbot.models import Campaign

    test_campaign = Campaign(
        user_id=advertiser.id,
        channel_id=seller_channel.id,
        name="Campagna Metrics Test",
        description="Campagna per test performance",
        budget=budget,
        created_at=datetime.utcnow(),
    )
    session.add(test_campaign)
    session.commit()

    # Crea un po' di metriche
    m1 = AdvertisementMetrics(
        campaign_id=test_campaign.id,
        channel_id=seller_channel.id,
        date=datetime.utcnow().date(),
        followers=100,
        impressions=1000,
        clicks=150,
        subscriptions=30,
        revenue=200.0,
        cost=budget,
    )
    session.add(m1)
    session.commit()

    perf = get_campaign_performance(session, test_campaign.id)
    if perf.get("clicks", 0) <= 0 or perf.get("impressions", 0) <= 0:
        raise AssertionError("get_campaign_performance ha restituito metriche incoerenti")

    # -----------------------------
    # 7. NOTIFICHE (FAKE BOT)
    # -----------------------------
    fake_bot = FakeBot()
    notifier = build_notification_sender(fake_bot)

    # Notifica earnings ricevuti
    notifier.send_user_notification(
        user_id=seller.telegram_id,
        notification_type=NotificationType.EARNINGS_RECEIVED,
        data={
            "channel_handle": seller_channel.handle,
            "amount": expected_seller_earning,
        },
    )

    # Notifica campaign purchased
    notifier.send_user_notification(
        user_id=advertiser.telegram_id,
        notification_type=NotificationType.CAMPAIGN_PURCHASED,
        data={
            "campaign_name": "Campagna Test E2E",
            "channel_handle": seller_channel.handle,
        },
    )

    if len(fake_bot.sent_messages) < 2:
        raise AssertionError("Notifiche non inviate correttamente al FakeBot")

    print("      OK   - Scenario E2E business / DB / notifiche completato.")
    session.close()


# ========================================================
# ENTRYPOINT
# ========================================================

def main():
    print("=== ADSBOT E2E BUSINESS TESTS ===")
    success = 0
    total = 20

    for i in range(1, total + 1):
        try:
            run_single_e2e_scenario(i)
        except Exception as e:
            print(f"\n*** ERRORE E2E ITERAZIONE {i} ***")
            print(e)
            traceback.print_exc()
        else:
            success += 1

    print(f"\n=== RISULTATO FINALE E2E: {success}/{total} ===")
    if success == total:
        print(">>> E2E BUSINESS COMPLETAMENTE SUPERATO")
        sys.exit(0)
    else:
        print(">>> E2E BUSINESS NON COMPLETAMENTE SUPERATO")
        sys.exit(1)


if __name__ == "__main__":
    main()
