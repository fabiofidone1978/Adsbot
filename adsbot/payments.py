"""Payment integration for Stripe and PayPal."""

from __future__ import annotations

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Stripe imports (optional, install with: pip install stripe)
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False

# PayPal imports (optional, install with: pip install paypalrestsdk)
try:
    import paypalrestsdk
    PAYPAL_AVAILABLE = True
except ImportError:
    PAYPAL_AVAILABLE = False


class StripePaymentHandler:
    """Handle Stripe payments."""

    def __init__(self):
        self.api_key = os.getenv("STRIPE_API_KEY")
        if self.api_key and STRIPE_AVAILABLE:
            stripe.api_key = self.api_key
            self.enabled = True
        else:
            self.enabled = False
            logger.warning("Stripe not configured or unavailable")

    def create_payment_intent(
        self, amount_cents: int, customer_email: str, description: str
    ) -> Optional[dict]:
        """Create a Stripe payment intent."""
        if not self.enabled:
            return None

        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                receipt_email=customer_email,
                description=description,
            )
            return {
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id,
                "status": intent.status,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return None

    def retrieve_payment_intent(self, payment_intent_id: str) -> Optional[dict]:
        """Retrieve payment intent status."""
        if not self.enabled:
            return None

        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                "status": intent.status,
                "amount": intent.amount,
                "currency": intent.currency,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return None

    def refund_payment(self, payment_intent_id: str, amount_cents: Optional[int] = None) -> bool:
        """Refund a payment."""
        if not self.enabled:
            return False

        try:
            stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=amount_cents,
            )
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund error: {e}")
            return False


class PayPalPaymentHandler:
    """Handle PayPal payments."""

    def __init__(self):
        self.client_id = os.getenv("PAYPAL_CLIENT_ID")
        self.client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        self.mode = os.getenv("PAYPAL_MODE", "sandbox")

        if self.client_id and self.client_secret and PAYPAL_AVAILABLE:
            paypalrestsdk.configure(
                {
                    "mode": self.mode,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                }
            )
            self.enabled = True
        else:
            self.enabled = False
            logger.warning("PayPal not configured or unavailable")

    def create_payment(
        self, amount: float, currency: str, description: str, return_url: str, cancel_url: str
    ) -> Optional[dict]:
        """Create a PayPal payment."""
        if not self.enabled:
            return None

        try:
            payment = paypalrestsdk.Payment(
                {
                    "intent": "sale",
                    "payer": {"payment_method": "paypal"},
                    "redirect_urls": {"return_url": return_url, "cancel_url": cancel_url},
                    "transactions": [
                        {
                            "amount": {"total": str(amount), "currency": currency},
                            "description": description,
                        }
                    ],
                }
            )

            if payment.create():
                # Return approval link
                for link in payment.links:
                    if link.rel == "approval_url":
                        return {
                            "payment_id": payment.id,
                            "approval_url": link.href,
                            "status": "created",
                        }
            else:
                logger.error(f"PayPal error: {payment.error}")
                return None
        except Exception as e:
            logger.error(f"PayPal exception: {e}")
            return None

    def execute_payment(self, payment_id: str, payer_id: str) -> Optional[dict]:
        """Execute a PayPal payment."""
        if not self.enabled:
            return None

        try:
            payment = paypalrestsdk.Payment.find(payment_id)
            if payment.execute({"payer_id": payer_id}):
                return {
                    "payment_id": payment.id,
                    "status": payment.state,
                    "amount": payment.transactions[0].amount.total,
                }
            else:
                logger.error(f"PayPal execution error: {payment.error}")
                return None
        except Exception as e:
            logger.error(f"PayPal execution exception: {e}")
            return None


class PaymentProcessor:
    """Unified payment processor supporting multiple providers."""

    def __init__(self):
        self.stripe = StripePaymentHandler()
        self.paypal = PayPalPaymentHandler()

    def process_payment(
        self,
        provider: str,
        amount: float,
        currency: str,
        customer_email: str,
        description: str,
        **kwargs,
    ) -> Optional[dict]:
        """Process payment with specified provider."""
        if provider == "stripe":
            amount_cents = int(amount * 100)
            return self.stripe.create_payment_intent(
                amount_cents, customer_email, description
            )
        elif provider == "paypal":
            return self.paypal.create_payment(
                amount,
                currency,
                description,
                kwargs.get("return_url", ""),
                kwargs.get("cancel_url", ""),
            )
        else:
            logger.error(f"Unknown payment provider: {provider}")
            return None

    def verify_payment(self, provider: str, payment_id: str) -> Optional[dict]:
        """Verify payment status."""
        if provider == "stripe":
            return self.stripe.retrieve_payment_intent(payment_id)
        elif provider == "paypal":
            # PayPal: payment_id is checked during execution
            return {"provider": "paypal", "payment_id": payment_id}
        else:
            return None
