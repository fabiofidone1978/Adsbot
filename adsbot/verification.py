"""FASE 6: User verification, identity verification, and risk management system."""

import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from adsbot.models import User, UserRole, UserState, DisputeTicket, DisputeStatus, MarketplaceOrder, OrderState

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VerificationStatus(str, Enum):
    """User verification statuses."""
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


# ============================================================================
# Task 24: Identity Verification System
# ============================================================================

class IdentityVerification:
    """Handle user identity verification process."""
    
    @staticmethod
    def start_verification(session: Session, user_id: int, verification_data: Dict) -> Dict:
        """Start identity verification process.
        
        Args:
            session: Database session
            user_id: User ID to verify
            verification_data: Dictionary with:
                - full_name: str
                - date_of_birth: str (YYYY-MM-DD)
                - country: str
                - document_type: str (passport, id_card, license)
                - document_number: str
                - document_image_url: str (optional)
        
        Returns:
            Verification request status
        """
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User {user_id} not found")
                return {"error": "User not found"}
            
            # Validate input data
            required_fields = ["full_name", "date_of_birth", "country", "document_type", "document_number"]
            if not all(field in verification_data for field in required_fields):
                return {"error": "Missing required verification fields"}
            
            # Store verification request
            user.verification_data = {
                "full_name": verification_data["full_name"],
                "date_of_birth": verification_data["date_of_birth"],
                "country": verification_data["country"],
                "document_type": verification_data["document_type"],
                "document_number": verification_data["document_number"],
                "document_image_url": verification_data.get("document_image_url"),
                "status": VerificationStatus.PENDING,
                "requested_at": datetime.now().isoformat(),
            }
            
            user.state = UserState.UNDER_REVIEW
            session.commit()
            
            logger.info(f"Verification started for user {user_id}")
            
            return {
                "status": "pending",
                "user_id": user_id,
                "message": "Verification request submitted. Please wait for admin review.",
                "requested_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error starting verification: {e}")
            session.rollback()
            return {"error": str(e)}
    
    @staticmethod
    def verify_user(session: Session, user_id: int, admin_id: int, approved: bool, notes: str = "") -> Dict:
        """Admin approves or rejects user verification.
        
        Args:
            session: Database session
            user_id: User ID to verify
            admin_id: Admin user ID performing verification
            approved: True to approve, False to reject
            notes: Optional notes from admin
        
        Returns:
            Verification result
        """
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "User not found"}
            
            if approved:
                user.admin_verified_at = datetime.now()
                user.state = UserState.ACTIVE
                user.verification_data["status"] = VerificationStatus.VERIFIED
                result = "approved"
                message = "Your identity has been verified successfully!"
                
            else:
                user.verification_data["status"] = VerificationStatus.REJECTED
                user.state = UserState.UNVERIFIED
                result = "rejected"
                message = f"Verification rejected. Reason: {notes}"
            
            user.verification_data["verified_by"] = admin_id
            user.verification_data["verified_at"] = datetime.now().isoformat()
            user.verification_data["notes"] = notes
            
            session.commit()
            
            logger.info(f"User {user_id} verification {result} by admin {admin_id}")
            
            return {
                "status": result,
                "user_id": user_id,
                "message": message,
                "verified_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error verifying user: {e}")
            session.rollback()
            return {"error": str(e)}
    
    @staticmethod
    def check_verification_documents_validity(verification_data: Dict) -> bool:
        """Check if verification documents are within valid period.
        
        Args:
            verification_data: User verification data dictionary
            
        Returns:
            True if valid, False if expired
        """
        try:
            if not verification_data or not verification_data.get("verified_at"):
                return False
            
            verified_at = datetime.fromisoformat(verification_data["verified_at"])
            # Documents valid for 2 years
            if (datetime.now() - verified_at).days > 730:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking document validity: {e}")
            return False


# ============================================================================
# Task 25: Risk Scoring & Fraud Detection System
# ============================================================================

class RiskScorer:
    """Calculate user risk score based on behavior and account characteristics."""
    
    @staticmethod
    def calculate_risk_score(session: Session, user_id: int) -> Dict:
        """Calculate comprehensive risk score for user.
        
        Risk factors (0-100 scale):
        - New account (0-15 points)
        - No verification (0-20 points)
        - Disputed orders (0-20 points)
        - Account suspension history (0-15 points)
        - Negative ratings (0-20 points)
        - Unusual activity (0-10 points)
        
        Args:
            session: Database session
            user_id: User ID to score
            
        Returns:
            Risk assessment dictionary
        """
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "User not found"}
            
            score = 0
            factors = []
            
            # Factor 1: Account age
            account_age_days = (datetime.now() - user.created_at).days if user.created_at else 0
            if account_age_days < 7:
                score += 15
                factors.append({"factor": "new_account", "points": 15, "age_days": account_age_days})
            elif account_age_days < 30:
                score += 8
                factors.append({"factor": "recent_account", "points": 8, "age_days": account_age_days})
            
            # Factor 2: Verification status
            if user.admin_verified_at is None:
                score += 20
                factors.append({"factor": "unverified", "points": 20})
            else:
                # Check if verification is expired
                days_since_verified = (datetime.now() - user.admin_verified_at).days
                if days_since_verified > 730:  # 2 years
                    score += 10
                    factors.append({"factor": "verification_expired", "points": 10})
            
            # Factor 3: Disputed orders (relevant for both editors and advertisers)
            if user.role == UserRole.EDITOR:
                disputed_orders = session.query(DisputeTicket).filter(
                    DisputeTicket.editor_id == user_id,
                    DisputeTicket.status == DisputeStatus.open
                ).all()
            else:
                disputed_orders = session.query(DisputeTicket).filter(
                    DisputeTicket.advertiser_id == user_id,
                    DisputeTicket.status == DisputeStatus.open
                ).all()
            
            dispute_count = len(disputed_orders)
            if dispute_count > 0:
                score += min(dispute_count * 7, 20)  # Max 20 points for 3+ disputes
                factors.append({"factor": "disputed_orders", "points": min(dispute_count * 7, 20), "count": dispute_count})
            
            # Factor 4: Suspension history
            if user.is_suspended:
                score += 15
                factors.append({"factor": "currently_suspended", "points": 15})
            
            # Factor 5: Ratings (for editors)
            if user.role == UserRole.EDITOR and user.rating is not None:
                if user.rating < 2.0:
                    score += 15
                    factors.append({"factor": "low_rating", "points": 15, "rating": user.rating})
                elif user.rating < 3.0:
                    score += 8
                    factors.append({"factor": "below_average_rating", "points": 8, "rating": user.rating})
            
            # Factor 6: Unusual order activity
            if user.role == UserRole.ADVERTISER:
                orders_7d = session.query(MarketplaceOrder).filter(
                    MarketplaceOrder.advertiser_id == user_id,
                    MarketplaceOrder.created_at >= datetime.now() - timedelta(days=7)
                ).count()
                
                if orders_7d > 50:
                    score += 8
                    factors.append({"factor": "high_order_volume", "points": 8, "orders_7d": orders_7d})
            
            # Determine risk level
            if score < 20:
                risk_level = RiskLevel.LOW
            elif score < 40:
                risk_level = RiskLevel.MEDIUM
            elif score < 70:
                risk_level = RiskLevel.HIGH
            else:
                risk_level = RiskLevel.CRITICAL
            
            return {
                "user_id": user_id,
                "risk_score": score,
                "risk_level": risk_level,
                "factors": factors,
                "assessment_date": datetime.now().isoformat(),
                "recommendation": RiskScorer._get_recommendation(risk_level, score),
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _get_recommendation(risk_level: RiskLevel, score: int) -> str:
        """Get recommended action based on risk level.
        
        Args:
            risk_level: Risk level enum
            score: Risk score (0-100)
            
        Returns:
            Recommendation string
        """
        if risk_level == RiskLevel.CRITICAL:
            return "CRITICAL: Immediate action required. Consider suspension pending investigation."
        elif risk_level == RiskLevel.HIGH:
            return "HIGH: Increase monitoring. Require additional verification before new activities."
        elif risk_level == RiskLevel.MEDIUM:
            return "MEDIUM: Standard monitoring. Flag for manual review if score increases."
        else:
            return "LOW: Standard operations. Monitor for changes in risk factors."
    
    @staticmethod
    def flag_suspicious_activity(session: Session, user_id: int, activity_type: str, details: Dict) -> Dict:
        """Flag suspicious activity for a user.
        
        Activity types:
        - duplicate_account: Multiple accounts from same IP/email
        - rapid_orders: Unusually rapid order creation
        - unusual_geography: Orders from unexpected locations
        - payment_failure: Multiple failed payment attempts
        - high_chargeback_rate: Excessive chargebacks/refunds
        
        Args:
            session: Database session
            user_id: User ID
            activity_type: Type of suspicious activity
            details: Dictionary with activity details
            
        Returns:
            Flag status
        """
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "User not found"}
            
            # Initialize flags list if not present
            if not user.flags:
                user.flags = []
            
            flag = {
                "type": activity_type,
                "details": details,
                "flagged_at": datetime.now().isoformat(),
                "status": "open",
            }
            
            user.flags.append(flag)
            
            # If critical activity, consider automatic actions
            if activity_type == "rapid_orders":
                logger.warning(f"Suspicious activity flagged for user {user_id}: {activity_type}")
                # Could trigger temporary order limit or suspension
            
            session.commit()
            
            return {
                "status": "flagged",
                "user_id": user_id,
                "activity_type": activity_type,
                "flagged_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error flagging suspicious activity: {e}")
            session.rollback()
            return {"error": str(e)}


# ============================================================================
# Task 26: Dispute Resolution & Automation
# ============================================================================

class DisputeResolver:
    """Automated dispute resolution with fraud detection."""
    
    @staticmethod
    def analyze_dispute(session: Session, dispute_id: int) -> Dict:
        """Analyze dispute for fraud indicators and auto-resolution candidates.
        
        Returns analysis with:
        - Evidence quality score
        - Fraud likelihood
        - Recommendation
        
        Args:
            session: Database session
            dispute_id: Dispute ID
            
        Returns:
            Dispute analysis
        """
        try:
            dispute = session.query(DisputeTicket).filter(DisputeTicket.id == dispute_id).first()
            if not dispute:
                return {"error": "Dispute not found"}
            
            analysis = {
                "dispute_id": dispute_id,
                "editor_id": dispute.editor_id,
                "advertiser_id": dispute.advertiser_id,
                "order_id": dispute.order_id,
            }
            
            # Get related user data
            editor = session.query(User).filter(User.id == dispute.editor_id).first()
            advertiser = session.query(User).filter(User.id == dispute.advertiser_id).first()
            order = session.query(MarketplaceOrder).filter(MarketplaceOrder.id == dispute.order_id).first() if dispute.order_id else None
            
            # Calculate fraud score
            fraud_score = 0
            fraud_factors = []
            
            # Factor 1: Dispute history
            if editor:
                editor_disputes = session.query(DisputeTicket).filter(
                    DisputeTicket.editor_id == editor.id
                ).count()
                if editor_disputes > 3:
                    fraud_score += 15
                    fraud_factors.append("multiple_disputes_by_editor")
            
            if advertiser:
                advertiser_disputes = session.query(DisputeTicket).filter(
                    DisputeTicket.advertiser_id == advertiser.id
                ).count()
                if advertiser_disputes > 3:
                    fraud_score += 15
                    fraud_factors.append("multiple_disputes_by_advertiser")
            
            # Factor 2: User reputation
            if editor and editor.rating and editor.rating < 2.0:
                fraud_score += 10
                fraud_factors.append("low_editor_rating")
            
            if advertiser and advertiser.is_suspended:
                fraud_score += 15
                fraud_factors.append("advertiser_suspended")
            
            # Factor 3: Order characteristics
            if order:
                if order.state not in [OrderState.completed, OrderState.processing]:
                    fraud_score += 10
                    fraud_factors.append("unusual_order_state")
            
            # Factor 4: Reason text analysis (simple keyword matching)
            reason_lower = (dispute.reason or "").lower()
            if any(word in reason_lower for word in ["scam", "fraud", "fake", "stolen"]):
                fraud_score += 10
                fraud_factors.append("severe_allegation")
            
            # Determine recommendation
            if fraud_score > 40:
                recommendation = "DENY_EDITOR_CLAIM"  # Likely legitimate advertiser
                confidence = "high"
            elif fraud_score > 25:
                recommendation = "MANUAL_REVIEW"
                confidence = "medium"
            else:
                recommendation = "APPROVE_EDITOR_CLAIM"  # Likely genuine dispute
                confidence = "high"
            
            analysis["fraud_score"] = fraud_score
            analysis["fraud_factors"] = fraud_factors
            analysis["recommendation"] = recommendation
            analysis["confidence"] = confidence
            analysis["reason"] = dispute.reason
            analysis["evidence"] = dispute.evidence
            analysis["analysis_date"] = datetime.now().isoformat()
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing dispute: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def auto_resolve_dispute(session: Session, dispute_id: int, resolution: str) -> Dict:
        """Auto-resolve dispute based on analysis recommendation.
        
        Resolutions:
        - APPROVE_EDITOR_CLAIM: Refund editor, charge advertiser
        - DENY_EDITOR_CLAIM: Refund advertiser, pay editor normally
        - SPLIT_50_50: Split refund 50/50
        
        Args:
            session: Database session
            dispute_id: Dispute ID
            resolution: Resolution type
            
        Returns:
            Resolution status
        """
        try:
            dispute = session.query(DisputeTicket).filter(DisputeTicket.id == dispute_id).first()
            if not dispute:
                return {"error": "Dispute not found"}
            
            order = session.query(MarketplaceOrder).filter(MarketplaceOrder.id == dispute.order_id).first() if dispute.order_id else None
            if not order:
                return {"error": "Associated order not found"}
            
            editor = session.query(User).filter(User.id == dispute.editor_id).first()
            advertiser = session.query(User).filter(User.id == dispute.advertiser_id).first()
            
            dispute_amount = order.advertiser_cost or 0
            editor_earnings = order.editor_earnings or 0
            
            if resolution == "APPROVE_EDITOR_CLAIM":
                # Refund advertiser
                if advertiser:
                    advertiser.wallet_balance = (advertiser.wallet_balance or 0) + dispute_amount
                
                # Keep editor earnings as is
                dispute.status = DisputeStatus.resolved
                dispute.resolution = "EDITOR_APPROVED"
                
            elif resolution == "DENY_EDITOR_CLAIM":
                # Refund advertiser (chargeback)
                if advertiser:
                    advertiser.wallet_balance = (advertiser.wallet_balance or 0) + dispute_amount
                
                # Editor loses earnings
                if editor:
                    editor.wallet_balance = (editor.wallet_balance or 0) - editor_earnings
                
                dispute.status = DisputeStatus.resolved
                dispute.resolution = "EDITOR_DENIED"
                
            elif resolution == "SPLIT_50_50":
                # Split loss
                split_amount = dispute_amount / 2
                
                if advertiser:
                    advertiser.wallet_balance = (advertiser.wallet_balance or 0) + split_amount
                
                if editor:
                    editor.wallet_balance = (editor.wallet_balance or 0) - split_amount
                
                dispute.status = DisputeStatus.resolved
                dispute.resolution = "SPLIT_50_50"
            
            dispute.resolved_at = datetime.now()
            session.commit()
            
            logger.info(f"Dispute {dispute_id} auto-resolved: {resolution}")
            
            return {
                "status": "resolved",
                "dispute_id": dispute_id,
                "resolution": resolution,
                "resolved_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error resolving dispute: {e}")
            session.rollback()
            return {"error": str(e)}


# ============================================================================
# Account Security Functions
# ============================================================================

class AccountSecurity:
    """Manage user account security."""
    
    @staticmethod
    def generate_verification_token(user_id: int, token_type: str = "email") -> str:
        """Generate secure verification token.
        
        Args:
            user_id: User ID
            token_type: Type of token (email, phone, 2fa)
            
        Returns:
            Verification token
        """
        from secrets import token_urlsafe
        base_token = token_urlsafe(32)
        return base_token
    
    @staticmethod
    def check_ip_reputation(ip_address: str) -> Dict:
        """Check IP address reputation for fraud indicators.
        
        Args:
            ip_address: IP address to check
            
        Returns:
            IP reputation assessment
        """
        # In production, integrate with IP reputation API (MaxMind, AbuseIPDB, etc.)
        return {
            "ip": ip_address,
            "reputation": "unknown",
            "risk_level": "low",
            "is_vpn": False,
            "is_proxy": False,
        }
    
    @staticmethod
    def enable_2fa(session: Session, user_id: int, method: str = "totp") -> Dict:
        """Enable two-factor authentication for user.
        
        Args:
            session: Database session
            user_id: User ID
            method: 2FA method (totp, sms, email)
            
        Returns:
            2FA setup status
        """
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "User not found"}
            
            if not user.security_settings:
                user.security_settings = {}
            
            user.security_settings["2fa_enabled"] = True
            user.security_settings["2fa_method"] = method
            user.security_settings["2fa_enabled_at"] = datetime.now().isoformat()
            
            session.commit()
            
            return {
                "status": "enabled",
                "user_id": user_id,
                "method": method,
                "enabled_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error enabling 2FA: {e}")
            return {"error": str(e)}
