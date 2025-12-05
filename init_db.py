#!/usr/bin/env python
"""Initialize the database with all models."""

import logging
from adsbot.config import Config
from adsbot.db import Base, create_session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Initializing database...")
    config = Config.load()
    
    # Create session factory (this calls Base.metadata.create_all)
    session_factory = create_session_factory(config)
    
    logger.info("✅ Database initialized successfully!")
    logger.info(f"Database URL: {config.database_url}")
