import os
from app import create_app, db
from sqlalchemy import text
from app.models import User # Assuming User model is in app.models

def migrate_database():
    """Update database schema"""
    app = create_app() # Moved app creation inside the function to be self-contained

    with app.app_context():
        # Add any new columns that might be missing
        try:
            # Add violation_count to users if it doesn't exist
            if not hasattr(User, 'violation_count') or not db.engine.dialect.has_table(db.engine, 'users'):
                print("Adding violation_count column to users table...")
                # Using IF NOT EXISTS for broader compatibility, though some dialects might not support it directly in ALTER TABLE.
                # For robustness, one might query information_schema first.
                db.session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS violation_count INTEGER DEFAULT 0"))
                db.session.commit()
                print("Successfully added violation_count column!")
            else:
                print("violation_count column already exists or users table not found.")

            # Add status to chat_rooms if it doesn't exist
            # First, check if the table exists
            if db.engine.dialect.has_table(db.engine, 'chat_rooms'):
                # Check if the column exists
                result = db.session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'chat_rooms' AND column_name = 'status'
                """))
                if not result.fetchone():
                    print("Adding status column to chat_rooms table...")
                    db.session.execute(text("ALTER TABLE chat_rooms ADD COLUMN status VARCHAR(20) DEFAULT 'active'"))
                    db.session.commit()
                    print("Successfully added status column!")
                else:
                    print("status column already exists in chat_rooms table.")
            else:
                print("chat_rooms table not found, skipping status column addition.")


            # Check if is_read column exists
            if db.engine.dialect.has_table(db.engine, 'chat_messages'):
                result = db.session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'chat_messages' AND column_name = 'is_read'
                """))

                if not result.fetchone():
                    print("Adding is_read column to chat_messages table...")
                    db.session.execute(text("""
                        ALTER TABLE chat_messages 
                        ADD COLUMN is_read BOOLEAN DEFAULT FALSE
                    """))
                    db.session.commit()
                    print("Successfully added is_read column!")
                else:
                    print("is_read column already exists.")

                # Check if offered_products_json column exists
                result = db.session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'chat_messages' AND column_name = 'offered_products_json'
                """))

                if not result.fetchone():
                    print("Adding offered_products_json column to chat_messages table...")
                    db.session.execute(text("""
                        ALTER TABLE chat_messages 
                        ADD COLUMN offered_products_json TEXT
                    """))
                    db.session.commit()
                    print("Successfully added offered_products_json column!")
                else:
                    print("offered_products_json column already exists.")

                # Check if requested_products_json column exists
                result = db.session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'chat_messages' AND column_name = 'requested_products_json'
                """))

                if not result.fetchone():
                    print("Adding requested_products_json column to chat_messages table...")
                    db.session.execute(text("""
                        ALTER TABLE chat_messages 
                        ADD COLUMN requested_products_json TEXT
                    """))
                    db.session.commit()
                    print("Successfully added requested_products_json column!")
                else:
                    print("requested_products_json column already exists.")
            else:
                print("chat_messages table not found, skipping related column additions.")

        except Exception as e:
            print(f"Migration error: {e}")
            db.session.rollback()

if __name__ == "__main__":
    migrate_database()