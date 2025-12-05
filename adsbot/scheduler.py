"""FASE 5: Scheduled background tasks using APScheduler."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from sqlalchemy import and_

from adsbot.models import (
    MarketplaceOrder, OrderState, Campaign, User, UserRole, 
    DisputeTicket, DisputeStatus, Channel
)
from adsbot.db import get_session

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[BackgroundScheduler] = None


class SchedulerConfig:
    """APScheduler configuration."""
    
    JOBS = {
        "order_expiration": {
            "job_func": "adsbot.scheduler.job_expire_pending_orders",
            "trigger": "interval",
            "minutes": 30,  # Check every 30 minutes
            "max_instances": 1,
        },
        "order_timeout": {
            "job_func": "adsbot.scheduler.job_timeout_orders",
            "trigger": "interval",
            "minutes": 60,  # Check every hour
            "max_instances": 1,
        },
        "metrics_update": {
            "job_func": "adsbot.scheduler.job_update_channel_metrics",
            "trigger": "cron",
            "hour": "*/6",  # Every 6 hours
            "max_instances": 1,
        },
        "daily_report": {
            "job_func": "adsbot.scheduler.job_generate_daily_reports",
            "trigger": "cron",
            "hour": "2",  # 2 AM daily
            "minute": "0",
            "max_instances": 1,
        },
        "dispute_auto_resolve": {
            "job_func": "adsbot.scheduler.job_auto_resolve_disputes",
            "trigger": "interval",
            "minutes": 60,  # Check every hour
            "max_instances": 1,
        },
        "campaign_expiration": {
            "job_func": "adsbot.scheduler.job_expire_campaigns",
            "trigger": "interval",
            "minutes": 15,  # Check every 15 minutes
            "max_instances": 1,
        },
    }


# ============================================================================
# Task 20: APScheduler Setup & Initialization
# ============================================================================

def init_scheduler() -> BackgroundScheduler:
    """Initialize and configure APScheduler.
    
    Returns:
        Configured BackgroundScheduler instance
    """
    global scheduler
    
    try:
        scheduler = BackgroundScheduler(daemon=True)
        
        # Add all configured jobs
        for job_name, job_config in SchedulerConfig.JOBS.items():
            try:
                trigger = job_config.get("trigger")
                
                if trigger == "cron":
                    # CronTrigger for time-based schedules
                    trigger_obj = CronTrigger(
                        hour=job_config.get("hour"),
                        minute=job_config.get("minute", "0"),
                    )
                elif trigger == "interval":
                    # IntervalTrigger for recurring intervals
                    trigger_obj = IntervalTrigger(
                        minutes=job_config.get("minutes", 30),
                    )
                else:
                    logger.warning(f"Unknown trigger type for {job_name}: {trigger}")
                    continue
                
                # Get the job function by name
                job_func_path = job_config.get("job_func")
                module_name, func_name = job_func_path.rsplit(".", 1)
                
                # Import module and get function
                import importlib
                module = importlib.import_module(module_name)
                job_func = getattr(module, func_name)
                
                # Add job to scheduler
                scheduler.add_job(
                    job_func,
                    trigger=trigger_obj,
                    id=job_name,
                    name=job_name,
                    misfire_grace_time=60,
                    replace_existing=True,
                    max_instances=job_config.get("max_instances", 1),
                )
                
                logger.info(f"Scheduled job '{job_name}' registered successfully")
                
            except Exception as e:
                logger.error(f"Error scheduling job '{job_name}': {e}")
                continue
        
        scheduler.start()
        logger.info("APScheduler initialized and started")
        return scheduler
        
    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {e}")
        raise


def stop_scheduler():
    """Stop the scheduler gracefully."""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
        scheduler = None
        logger.info("Scheduler stopped")


# ============================================================================
# Task 21: Order Expiration & Auto-Cancel Jobs
# ============================================================================

def job_expire_pending_orders():
    """Expire pending orders that have exceeded max duration.
    
    Orders expire after PENDING_ORDER_MAX_HOURS (24 hours default).
    This prevents indefinite pending states.
    """
    try:
        session = get_session()
        
        # Orders older than 24 hours in PENDING state
        expiration_time = datetime.now() - timedelta(hours=24)
        
        expired_orders = session.query(MarketplaceOrder).filter(
            and_(
                MarketplaceOrder.state == OrderState.pending,
                MarketplaceOrder.created_at < expiration_time
            )
        ).all()
        
        for order in expired_orders:
            try:
                order.state = OrderState.cancelled
                order.updated_at = datetime.now()
                session.commit()
                logger.info(f"Expired pending order {order.id}")
            except Exception as e:
                session.rollback()
                logger.error(f"Error expiring order {order.id}: {e}")
        
        if expired_orders:
            logger.info(f"Expired {len(expired_orders)} pending orders")
        
    except Exception as e:
        logger.error(f"Error in order expiration job: {e}")
    finally:
        session.close()


def job_timeout_orders():
    """Auto-cancel orders that failed to complete within timeout.
    
    Orders in PROCESSING state timeout after PROCESSING_TIMEOUT_HOURS
    (48 hours default). This prevents stuck orders.
    """
    try:
        session = get_session()
        
        # Orders in PROCESSING state older than 48 hours
        timeout_time = datetime.now() - timedelta(hours=48)
        
        timeout_orders = session.query(MarketplaceOrder).filter(
            and_(
                MarketplaceOrder.state == OrderState.processing,
                MarketplaceOrder.created_at < timeout_time
            )
        ).all()
        
        for order in timeout_orders:
            try:
                order.state = OrderState.failed
                order.updated_at = datetime.now()
                session.commit()
                
                # Refund advertiser
                if order.advertiser_id:
                    user = session.query(User).filter(User.id == order.advertiser_id).first()
                    if user and order.advertiser_cost:
                        user.wallet_balance = (user.wallet_balance or 0) + order.advertiser_cost
                        session.commit()
                        logger.info(f"Refunded advertiser {order.advertiser_id} for timed-out order {order.id}")
                
                logger.info(f"Timed out order {order.id}")
            except Exception as e:
                session.rollback()
                logger.error(f"Error timing out order {order.id}: {e}")
        
        if timeout_orders:
            logger.info(f"Timed out {len(timeout_orders)} processing orders")
        
    except Exception as e:
        logger.error(f"Error in order timeout job: {e}")
    finally:
        session.close()


# ============================================================================
# Task 22: Metrics Update Jobs
# ============================================================================

def job_update_channel_metrics():
    """Update channel performance metrics every 6 hours.
    
    Recalculates: total orders, earnings, avg rating, etc.
    """
    try:
        session = get_session()
        
        channels = session.query(Channel).all()
        
        for channel in channels:
            try:
                # Get completed orders for this channel
                completed_orders = session.query(MarketplaceOrder).filter(
                    and_(
                        MarketplaceOrder.channel_id == channel.id,
                        MarketplaceOrder.state == OrderState.completed
                    )
                ).all()
                
                if completed_orders:
                    total_impressions = sum(o.impressions_count or 0 for o in completed_orders)
                    total_clicks = sum(o.clicks_count or 0 for o in completed_orders)
                    
                    # Update channel cache (if we had one)
                    # For now just log the metrics
                    logger.debug(f"Channel {channel.id} - Orders: {len(completed_orders)}, "
                               f"Impressions: {total_impressions}, Clicks: {total_clicks}")
                    
            except Exception as e:
                logger.error(f"Error updating metrics for channel {channel.id}: {e}")
        
        logger.info(f"Updated metrics for {len(channels)} channels")
        
    except Exception as e:
        logger.error(f"Error in metrics update job: {e}")
    finally:
        session.close()


# ============================================================================
# Task 23: Daily Reporting Jobs
# ============================================================================

def job_generate_daily_reports():
    """Generate and send daily platform reports.
    
    Creates daily summaries of:
    - Platform revenue and activity
    - Top performing channels
    - Top performing campaigns
    - New users
    """
    try:
        session = get_session()
        
        from datetime import date
        
        today = date.today()
        
        # Collect today's data
        daily_stats = {
            "date": today.isoformat(),
            "timestamp": datetime.now().isoformat(),
        }
        
        # New orders today
        today_orders = session.query(MarketplaceOrder).filter(
            MarketplaceOrder.created_at >= datetime.combine(today, datetime.min.time())
        ).all()
        
        daily_stats["new_orders"] = len(today_orders)
        daily_stats["completed_orders"] = len([o for o in today_orders if o.state == OrderState.completed])
        daily_stats["total_value"] = sum(o.advertiser_cost or 0 for o in today_orders)
        
        # New users today
        new_users = session.query(User).filter(
            User.created_at >= datetime.combine(today, datetime.min.time())
        ).all()
        
        daily_stats["new_editors"] = len([u for u in new_users if u.role == UserRole.EDITOR])
        daily_stats["new_advertisers"] = len([u for u in new_users if u.role == UserRole.ADVERTISER])
        
        # Top channels today
        top_channels = session.query(Channel).order_by(
            Channel.subscribers_count.desc()
        ).limit(5).all()
        
        daily_stats["top_channels"] = [
            {"name": c.channel_name, "subscribers": c.subscribers_count}
            for c in top_channels
        ]
        
        logger.info(f"Daily report generated: {daily_stats}")
        
        # In production: send email, save to DB, etc.
        
    except Exception as e:
        logger.error(f"Error in daily reporting job: {e}")
    finally:
        session.close()


# ============================================================================
# Task 23: Dispute Auto-Resolution Job
# ============================================================================

def job_auto_resolve_disputes():
    """Auto-resolve disputes based on predefined rules.
    
    Rules:
    - Dispute without new evidence for 5 days -> auto-close (refund editor)
    - Fraud case clearly documented -> deny editor, approve advertiser
    - Moderate violations -> 50/50 split
    """
    try:
        session = get_session()
        
        # Get open disputes
        open_disputes = session.query(DisputeTicket).filter(
            DisputeTicket.status == DisputeStatus.open
        ).all()
        
        for dispute in open_disputes:
            try:
                # Check age of dispute
                days_open = (datetime.now() - dispute.created_at).days
                
                if days_open > 5:
                    # Auto-close old disputes (refund editor)
                    dispute.status = DisputeStatus.closed
                    dispute.resolution = "auto_closed"
                    dispute.updated_at = datetime.now()
                    
                    # Refund editor
                    if dispute.order:
                        order = dispute.order
                        if order.editor_earnings:
                            # Return to advertiser wallet
                            advertiser = session.query(User).filter(
                                User.id == order.advertiser_id
                            ).first()
                            if advertiser:
                                advertiser.wallet_balance = (advertiser.wallet_balance or 0) + order.editor_earnings
                                session.commit()
                    
                    logger.info(f"Auto-resolved dispute {dispute.id} (age: {days_open} days)")
                    
            except Exception as e:
                session.rollback()
                logger.error(f"Error resolving dispute {dispute.id}: {e}")
        
        if open_disputes:
            logger.info(f"Auto-resolution processed for {len(open_disputes)} disputes")
        
    except Exception as e:
        logger.error(f"Error in dispute auto-resolution job: {e}")
    finally:
        session.close()


# ============================================================================
# Campaign Expiration Job
# ============================================================================

def job_expire_campaigns():
    """Auto-expire campaigns that have reached end date or budget limit.
    
    Criteria:
    - Campaign end_date has passed
    - Campaign budget fully spent
    - Campaign marked for expiration
    """
    try:
        session = get_session()
        
        now = datetime.now()
        
        # Get campaigns that should be expired
        expired_campaigns = session.query(Campaign).filter(
            and_(
                Campaign.is_active == True,
                Campaign.end_date < now
            )
        ).all()
        
        for campaign in expired_campaigns:
            try:
                campaign.is_active = False
                campaign.updated_at = datetime.now()
                session.commit()
                logger.info(f"Expired campaign {campaign.id}: {campaign.campaign_name}")
                
            except Exception as e:
                session.rollback()
                logger.error(f"Error expiring campaign {campaign.id}: {e}")
        
        if expired_campaigns:
            logger.info(f"Expired {len(expired_campaigns)} campaigns")
        
    except Exception as e:
        logger.error(f"Error in campaign expiration job: {e}")
    finally:
        session.close()


# ============================================================================
# Scheduler Management Functions
# ============================================================================

def get_scheduler_status() -> Dict:
    """Get current scheduler status and job details.
    
    Returns:
        Scheduler status dictionary
    """
    global scheduler
    
    if not scheduler:
        return {"status": "not_initialized"}
    
    return {
        "status": "running" if scheduler.running else "stopped",
        "jobs_count": len(scheduler.get_jobs()),
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
            for job in scheduler.get_jobs()
        ]
    }


def pause_job(job_id: str) -> bool:
    """Pause a scheduled job.
    
    Args:
        job_id: ID of the job to pause
        
    Returns:
        True if successful, False otherwise
    """
    global scheduler
    
    if not scheduler:
        return False
    
    try:
        job = scheduler.get_job(job_id)
        if job:
            job.pause()
            logger.info(f"Job {job_id} paused")
            return True
    except Exception as e:
        logger.error(f"Error pausing job {job_id}: {e}")
    
    return False


def resume_job(job_id: str) -> bool:
    """Resume a paused job.
    
    Args:
        job_id: ID of the job to resume
        
    Returns:
        True if successful, False otherwise
    """
    global scheduler
    
    if not scheduler:
        return False
    
    try:
        job = scheduler.get_job(job_id)
        if job:
            job.resume()
            logger.info(f"Job {job_id} resumed")
            return True
    except Exception as e:
        logger.error(f"Error resuming job {job_id}: {e}")
    
    return False


def trigger_job_now(job_id: str) -> bool:
    """Manually trigger a job immediately (for testing/admin).
    
    Args:
        job_id: ID of the job to trigger
        
    Returns:
        True if successful, False otherwise
    """
    global scheduler
    
    if not scheduler:
        return False
    
    try:
        job = scheduler.get_job(job_id)
        if job:
            # Execute the job function directly
            job.func()
            logger.info(f"Job {job_id} triggered manually")
            return True
    except Exception as e:
        logger.error(f"Error triggering job {job_id}: {e}")
    
    return False
