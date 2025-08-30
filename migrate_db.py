#!/usr/bin/env python3
"""
Database migration script for BarterHub
Adds missing columns and tables
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment"""
    return os.environ.get('DATABASE_URL', 'postgresql://username:password@localhost/barterhub')

def migrate_database():
    """Run database migrations"""
    database_url = get_database_url()
    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            # Add profile_picture column to users table if it doesn't exist
            try:
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS profile_picture VARCHAR(255);
                """))
                logger.info("Added profile_picture column to users table")
            except Exception as e:
                logger.warning(f"Profile picture column might already exist: {e}")

            # Create wishlists table if it doesn't exist
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS wishlists (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, product_id)
                    );
                """))
                logger.info("Created wishlists table")
            except Exception as e:
                logger.warning(f"Wishlists table might already exist: {e}")

            # Add indexes for better performance
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_wishlists_user_id ON wishlists(user_id);
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_wishlists_product_id ON wishlists(product_id);
                """))
                logger.info("Added indexes for wishlists table")
            except Exception as e:
                logger.warning(f"Indexes might already exist: {e}")

            # Commit all changes
            conn.commit()
            logger.info("Database migration completed successfully")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate_database()