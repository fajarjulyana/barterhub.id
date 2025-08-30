import os
import uuid
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app

def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, subfolder='products'):
    """Save uploaded file and return filename"""
    if file and allowed_file(file.filename):
        # Generate unique filename
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        # Create directory if it doesn't exist
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(upload_path, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_path, unique_filename)
        file.save(file_path)
        
        # Resize image if it's too large
        try:
            with Image.open(file_path) as img:
                if img.width > 800 or img.height > 800:
                    img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                    img.save(file_path, optimize=True, quality=85)
        except Exception as e:
            print(f"Error resizing image: {e}")
        
        return unique_filename
    return None

def calculate_point_balance(seller_points, buyer_points):
    """Calculate if the point exchange is balanced"""
    difference = abs(seller_points - buyer_points)
    tolerance = max(seller_points, buyer_points) * 0.1  # 10% tolerance
    return difference <= tolerance

def get_transaction_status_text(status):
    """Get Indonesian translation for transaction status"""
    status_map = {
        'pending': 'Menunggu Persetujuan',
        'agreed': 'Disepakati',
        'shipped': 'Dalam Pengiriman',
        'completed': 'Selesai',
        'cancelled': 'Dibatalkan',
        'dispute': 'Sengketa'
    }
    return status_map.get(status, status)

def get_condition_text(condition):
    """Get Indonesian translation for product condition"""
    condition_map = {
        'New': 'Baru',
        'Like New': 'Seperti Baru',
        'Good': 'Baik',
        'Fair': 'Cukup',
        'Poor': 'Buruk'
    }
    return condition_map.get(condition, condition)
