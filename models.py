import os
from datetime import datetime
from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Create a db instance that will be initialized later
db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='pembeli')  # penjual, pembeli, admin
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    kode_pos = db.Column(db.String(10))
    profile_picture = db.Column(db.String(255))  # Filename for profile picture
    is_active = db.Column(db.Boolean, default=True)
    is_banned = db.Column(db.Boolean, default=False)
    ban_reason = db.Column(db.Text)
    banned_at = db.Column(db.DateTime)
    banned_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    violation_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    products = db.relationship('Product', backref='owner', lazy='dynamic', foreign_keys='Product.user_id')
    sent_messages = db.relationship('ChatMessage', foreign_keys='ChatMessage.sender_id', backref='sender', lazy='dynamic')
    transactions_as_seller = db.relationship('Transaction', foreign_keys='Transaction.seller_id', backref='seller', lazy='dynamic')
    transactions_as_buyer = db.relationship('Transaction', foreign_keys='Transaction.buyer_id', backref='buyer', lazy='dynamic')
    reports_made = db.relationship('Report', foreign_keys='Report.reporter_id', backref='reporter', lazy='dynamic')
    reports_received = db.relationship('Report', foreign_keys='Report.reported_user_id', backref='reported_user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_seller(self):
        return self.role == 'penjual'

    def is_buyer(self):
        return self.role == 'pembeli'

    def ban_user(self, reason, banned_by_id):
        """Ban user with reason and who banned them"""
        self.is_banned = True
        self.ban_reason = reason
        self.banned_at = datetime.utcnow()
        self.banned_by = banned_by_id
        self.is_active = False

    def unban_user(self):
        """Unban user"""
        self.is_banned = False
        self.ban_reason = None
        self.banned_at = None
        self.banned_by = None
        self.is_active = True

    def add_violation(self):
        """Increment violation count"""
        self.violation_count += 1

    def add_to_wishlist(self, product_id):
        """Add product to user's wishlist"""
        from models import Wishlist
        existing = Wishlist.query.filter_by(user_id=self.id, product_id=product_id).first()
        if not existing:
            wishlist_item = Wishlist(user_id=self.id, product_id=product_id)
            db.session.add(wishlist_item)
            return True
        return False

    def remove_from_wishlist(self, product_id):
        """Remove product from user's wishlist"""
        from models import Wishlist
        wishlist_item = Wishlist.query.filter_by(user_id=self.id, product_id=product_id).first()
        if wishlist_item:
            db.session.delete(wishlist_item)
            return True
        return False

    def is_in_wishlist(self, product_id):
        """Check if product is in user's wishlist"""
        from models import Wishlist
        return Wishlist.query.filter_by(user_id=self.id, product_id=product_id).first() is not None

    def get_profile_picture(self):
        """Get profile picture URL or default avatar"""
        if self.profile_picture:
            return f'/static/uploads/profiles/{self.profile_picture}'
        else:
            return '/static/img/default-avatar.png'

    def set_profile_picture(self, filename):
        """Set profile picture filename"""
        # Delete old profile picture if exists
        if self.profile_picture:
            old_path = os.path.join(current_app.static_folder, 'uploads', 'profiles', self.profile_picture)
            if os.path.exists(old_path):
                os.remove(old_path)

        self.profile_picture = filename


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    products = db.relationship('Product', backref='category', lazy='dynamic')

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    condition = db.Column(db.String(20), nullable=False)  # New, Like New, Good, Fair, Poor
    desired_items = db.Column(db.Text, nullable=False)  # What user wants to trade for

    # Point calculation factors (1-10 scale)
    utility_score = db.Column(db.Integer, default=5)
    scarcity_score = db.Column(db.Integer, default=5)
    durability_score = db.Column(db.Integer, default=5)
    portability_score = db.Column(db.Integer, default=5)
    seasonal_score = db.Column(db.Integer, default=5)

    # Calculated points
    total_points = db.Column(db.Integer, default=0)

    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    images = db.relationship('ProductImage', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    offers_received = db.relationship('TransactionOffer', backref='product', lazy='dynamic')

    def calculate_points(self):
        """Calculate total points based on various factors"""
        # Base calculation
        base_score = (self.utility_score + self.scarcity_score + self.durability_score + 
                     self.portability_score + self.seasonal_score) / 5

        # Condition multiplier
        condition_multipliers = {
            'New': 1.0,
            'Like New': 0.9,
            'Good': 0.8,
            'Fair': 0.6,
            'Poor': 0.4
        }

        condition_multiplier = condition_multipliers.get(self.condition, 0.8)
        self.total_points = int(base_score * condition_multiplier * 10)  # Scale to reasonable range

        return self.total_points

    def get_main_image(self):
        """Get the main product image"""
        image = self.images.filter_by(is_main=True).first()
        if not image:
            image = self.images.first()
        return image.filename if image else 'default-product.jpg'

class ProductImage(db.Model):
    __tablename__ = 'product_images'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    is_main = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatRoom(db.Model):
    __tablename__ = 'chat_rooms'

    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, closed, negotiating
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user1 = db.relationship('User', foreign_keys=[user1_id])
    user2 = db.relationship('User', foreign_keys=[user2_id])
    product = db.relationship('Product')
    messages = db.relationship('ChatMessage', backref='room', lazy='dynamic', cascade='all, delete-orphan')

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_rooms.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')  # text, offer, system, image
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Enhanced fields for offer negotiations
    offered_products_json = db.Column(db.Text)  # JSON string of offered products
    requested_products_json = db.Column(db.Text)  # JSON string of requested products
    offer_status = db.Column(db.String(20), default='pending')  # pending, accepted, declined, countered

    # Relationships
    sender = db.relationship('User')

    def get_offered_products(self):
        """Parse offered products JSON"""
        if self.offered_products_json:
            try:
                import json
                return json.loads(self.offered_products_json)
            except:
                return []
        return []

    def get_requested_products(self):
        """Parse requested products JSON"""
        if self.requested_products_json:
            try:
                import json
                return json.loads(self.requested_products_json)
            except:
                return []
        return []

    def __repr__(self):
        return f'<ChatMessage {self.id}: {self.message[:50]}>'

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)

    status = db.Column(db.String(20), default='pending')  # pending, agreed, shipped, completed, cancelled, dispute

    # Shipping information
    seller_tracking_number = db.Column(db.String(100))
    buyer_tracking_number = db.Column(db.String(100))
    seller_shipped_at = db.Column(db.DateTime)
    buyer_shipped_at = db.Column(db.DateTime)
    seller_received_at = db.Column(db.DateTime)
    buyer_received_at = db.Column(db.DateTime)

    # Security confirmation codes
    seller_confirmation_code = db.Column(db.String(20))  # Code for seller's package
    buyer_confirmation_code = db.Column(db.String(20))   # Code for buyer's package

    # Points
    total_seller_points = db.Column(db.Integer, default=0)
    total_buyer_points = db.Column(db.Integer, default=0)

    # Alamat lengkap WAJIB untuk penjual dan pembeli
    seller_address = db.Column(db.Text)
    buyer_address = db.Column(db.Text)
    seller_phone = db.Column(db.String(20))
    buyer_phone = db.Column(db.String(20))

    # Kesepakatan melalui chat sebelum resi bisa muncul
    chat_agreement_seller = db.Column(db.Boolean, default=False)
    chat_agreement_buyer = db.Column(db.Boolean, default=False)
    agreement_timestamp = db.Column(db.DateTime)

    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = db.relationship('Product')
    offers = db.relationship('TransactionOffer', backref='transaction', lazy='dynamic', cascade='all, delete-orphan')

    def can_proceed_to_shipping(self):
        """Check if both parties agreed in chat and have complete addresses"""
        return (self.chat_agreement_seller and 
                self.chat_agreement_buyer and 
                self.seller_address and 
                self.buyer_address and 
                self.seller_phone and 
                self.buyer_phone)

    def set_chat_agreement(self, user_id):
        """Set chat agreement for seller or buyer"""
        if user_id == self.seller_id:
            self.chat_agreement_seller = True
        elif user_id == self.buyer_id:
            self.chat_agreement_buyer = True

        # If both agreed, set timestamp
        if self.chat_agreement_seller and self.chat_agreement_buyer:
            self.agreement_timestamp = datetime.utcnow()
            self.status = 'agreed'

    def generate_confirmation_codes(self):
        """Generate unique confirmation codes for both seller and buyer packages"""
        import secrets
        import string

        # Generate 8-character alphanumeric codes
        alphabet = string.ascii_uppercase + string.digits

        if not self.seller_confirmation_code:
            self.seller_confirmation_code = ''.join(secrets.choice(alphabet) for _ in range(8))

        if not self.buyer_confirmation_code:
            self.buyer_confirmation_code = ''.join(secrets.choice(alphabet) for _ in range(8))

class TransactionOffer(db.Model):
    __tablename__ = 'transaction_offers'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    offered_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    offered_by = db.relationship('User')

class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)  # If reporting about a product
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)  # If reporting about a transaction

    report_type = db.Column(db.String(50), nullable=False)  # 'prohibited_items', 'scam', 'fake_product', 'inappropriate_behavior', 'other'
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    evidence_urls = db.Column(db.Text)  # JSON string of evidence URLs/screenshots

    status = db.Column(db.String(20), default='pending')  # pending, investigating, resolved, dismissed
    admin_response = db.Column(db.Text)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolved_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = db.relationship('Product', backref='reports')
    transaction = db.relationship('Transaction', backref='reports')
    resolver = db.relationship('User', foreign_keys=[resolved_by], backref='resolved_reports')

class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reviewed_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)

    # Specific ratings
    communication_rating = db.Column(db.Integer, default=5)  # 1-5
    product_condition_rating = db.Column(db.Integer, default=5)  # 1-5
    shipping_speed_rating = db.Column(db.Integer, default=5)  # 1-5

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    transaction = db.relationship('Transaction', backref='reviews')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref='reviews_given')
    reviewed_user = db.relationship('User', foreign_keys=[reviewed_user_id], backref='reviews_received')

class Wishlist(db.Model):
    __tablename__ = 'wishlists'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='wishlist_items')
    product = db.relationship('Product', backref='wishlisted_by')

    # Unique constraint to prevent duplicate wishlist items
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='unique_user_product_wishlist'),)