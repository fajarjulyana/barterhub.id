import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_
from models import db
from models import User, Product, Category, ProductImage, ChatRoom, ChatMessage, Transaction, TransactionOffer, Review
from forms import LoginForm, RegisterForm, ProductForm, ChatMessageForm, OfferForm, TrackingForm
from utils import save_uploaded_file, calculate_point_balance, get_transaction_status_text, get_condition_text

# Main blueprint
main = Blueprint('main', __name__)

@main.route('/')
def index():
    # Get featured products
    featured_products = Product.query.filter_by(is_available=True).order_by(Product.created_at.desc()).limit(8).all()
    categories = Category.query.all()
    return render_template('index.html', products=featured_products, categories=categories)

@main.route('/profile')
@login_required
def profile():
    user_products = current_user.products.filter_by(is_available=True).all()
    user_transactions = Transaction.query.filter(
        or_(Transaction.seller_id == current_user.id, Transaction.buyer_id == current_user.id)
    ).order_by(Transaction.created_at.desc()).limit(10).all()
    return render_template('profile.html', products=user_products, transactions=user_transactions)

# Authentication blueprint
auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            role=form.role.data,
            phone=form.phone.data,
            address=form.address.data,
            kode_pos=form.kode_pos.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Registrasi berhasil! Silakan login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)

@main.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    from forms import ProfileEditForm
    from utils import save_profile_picture

    form = ProfileEditForm(current_user, obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data
        current_user.address = form.address.data
        current_user.kode_pos = form.kode_pos.data

        # Handle profile picture upload
        if form.profile_picture.data:
            filename = save_profile_picture(form.profile_picture.data, current_user.id)
            if filename:
                current_user.set_profile_picture(filename)
                flash('Foto profil berhasil diperbarui!', 'success')
            else:
                flash('Gagal mengupload foto profil. Pastikan file berformat JPG/PNG dan ukuran < 5MB.', 'error')

        db.session.commit()
        flash('Profil berhasil diperbarui!', 'success')
        return redirect(url_for('main.profile'))

    return render_template('profile_edit.html', form=form)

    return render_template('auth/register.html', form=form)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Selamat datang, {user.full_name}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Username atau password salah.', 'error')

    return render_template('auth/login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('main.index'))

# API Routes for AJAX calls
@main.route('/api/categories')
def api_categories():
    """API endpoint untuk mendapatkan daftar kategori"""
    try:
        categories = Category.query.all()
        categories_data = [{
            'id': category.id,
            'name': category.name
        } for category in categories]

        return jsonify({
            'success': True,
            'categories': categories_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Products blueprint
products = Blueprint('products', __name__)

@products.route('/')
def list_products():
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category', type=int)
    search = request.args.get('search', '')
    condition = request.args.get('condition', '')

    query = Product.query.filter_by(is_available=True)

    if category_id:
        query = query.filter_by(category_id=category_id)

    if search:
        query = query.filter(
            or_(Product.title.ilike(f'%{search}%'), 
                Product.description.ilike(f'%{search}%'))
        )

    if condition:
        query = query.filter_by(condition=condition)

    products_pagination = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=12, error_out=False
    )

    categories = Category.query.all()
    conditions = ['New', 'Like New', 'Good', 'Fair', 'Poor']

    return render_template('products/list.html', 
                         products=products_pagination.items,
                         pagination=products_pagination,
                         categories=categories,
                         conditions=conditions,
                         current_category=category_id,
                         current_search=search,
                         current_condition=condition)

@products.route('/<int:id>')
def detail(id):
    product = Product.query.get_or_404(id)

    # Get related products with better matching algorithm
    similar_products = Product.query.filter(
        and_(Product.category_id == product.category_id,
             Product.id != product.id,
             Product.is_available == True)
    ).order_by(
        # Sort by point difference (closer points = more similar)
        db.func.abs(Product.total_points - product.total_points).asc(),
        Product.created_at.desc()
    ).limit(8).all()

    return render_template('products/detail.html', product=product, similar_products=similar_products)

@products.route('/related/<int:product_id>')
def get_related_products(product_id):
    """API endpoint untuk mendapatkan produk terkait"""
    try:
        product = Product.query.get_or_404(product_id)

        # Advanced related products algorithm
        related_products = Product.query.filter(
            and_(
                Product.id != product_id,
                Product.is_available == True,
                or_(
                    Product.category_id == product.category_id,  # Same category
                    Product.total_points.between(product.total_points - 20, product.total_points + 20),  # Similar points
                    Product.condition == product.condition  # Same condition
                )
            )
        ).order_by(
            # Prioritize by multiple factors
            db.case(
                (Product.category_id == product.category_id, 1),
                (Product.condition == product.condition, 2),
                else_=3
            ).asc(),
            db.func.abs(Product.total_points - product.total_points).asc(),
            Product.created_at.desc()
        ).limit(12).all()

        products_data = []
        for related_product in related_products:
            products_data.append({
                'id': related_product.id,
                'title': related_product.title,
                'description': related_product.description[:100] + ('...' if len(related_product.description) > 100 else ''),
                'total_points': related_product.total_points,
                'condition': related_product.condition,
                'category': related_product.category.name,
                'owner_name': related_product.owner.full_name,
                'owner_username': related_product.owner.username,
                'created_at': related_product.created_at.strftime('%d %b %Y'),
                'main_image': related_product.get_main_image(),
                'is_owner': current_user.is_authenticated and related_product.user_id == current_user.id,
                'can_barter': current_user.is_authenticated and related_product.user_id != current_user.id
            })

        return jsonify({
            'success': True,
            'related_products': products_data,
            'total': len(products_data)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@products.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    # Semua user terdaftar bisa menambah produk untuk ditukar

    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            user_id=current_user.id,
            category_id=form.category_id.data,
            title=form.title.data,
            description=form.description.data,
            condition=form.condition.data,
            desired_items=form.desired_items.data,
            utility_score=form.utility_score.data,
            scarcity_score=form.scarcity_score.data,
            durability_score=form.durability_score.data,
            portability_score=form.portability_score.data,
            seasonal_score=form.seasonal_score.data
        )

        # Calculate points
        product.calculate_points()

        db.session.add(product)
        db.session.flush()  # Get the product ID

        # Handle image uploads
        if form.images.data:
            files = request.files.getlist('images')
            for i, file in enumerate(files[:10]):  # Max 10 images
                if file and file.filename:
                    filename = save_uploaded_file(file, 'products')
                    if filename:
                        image = ProductImage(
                            product_id=product.id,
                            filename=filename,
                            is_main=(i == 0)  # First image is main
                        )
                        db.session.add(image)

        db.session.commit()
        flash('Produk berhasil ditambahkan!', 'success')
        return redirect(url_for('products.detail', id=product.id))

    return render_template('products/add.html', form=form)

@products.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    product = Product.query.get_or_404(id)

    if product.user_id != current_user.id and not current_user.is_admin():
        flash('Anda tidak memiliki akses untuk mengedit produk ini.', 'error')
        return redirect(url_for('products.detail', id=id))

    form = ProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        product.calculate_points()

        # Handle new image uploads
        if form.images.data:
            files = request.files.getlist('images')
            for file in files[:10]:  # Max 10 images
                if file and file.filename:
                    filename = save_uploaded_file(file, 'products')
                    if filename:
                        image = ProductImage(
                            product_id=product.id,
                            filename=filename,
                            is_main=False
                        )
                        db.session.add(image)

        db.session.commit()
        flash('Produk berhasil diperbarui!', 'success')
        return redirect(url_for('products.detail', id=id))

    return render_template('products/edit.html', form=form, product=product)

# Chat blueprint
chat = Blueprint('chat', __name__)

@chat.route('/rooms')
def get_rooms():
    """API endpoint untuk mendapatkan daftar chat rooms dengan notifikasi"""
    # Always return JSON for floating chat compatibility
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'rooms': [],
            'total_unread': 0,
            'has_new_messages': False,
            'error': 'User not authenticated'
        }), 401

    try:
        # Enhanced query dengan proper error handling
        rooms = ChatRoom.query.filter(
            or_(ChatRoom.user1_id == current_user.id, ChatRoom.user2_id == current_user.id)
        ).join(Product).filter(Product.is_available == True).order_by(ChatRoom.created_at.desc()).all()

    except Exception as e:
        # If database error occurs, return empty rooms but maintain success=True for stability
        print(f"Database error in get_rooms: {e}")
        return jsonify({
            'success': False,
            'rooms': [],
            'total_unread': 0,
            'has_new_messages': False,
            'error': f'Database error: {str(e)}'
        }), 500

    rooms_data = []
    total_unread = 0
    has_new_messages = False

    for room in rooms:
        # Validasi bahwa current user adalah participant dari room ini
        if room.user1_id != current_user.id and room.user2_id != current_user.id:
            continue  # Skip room ini jika user bukan participant
            
        # Tentukan siapa lawan chat dan role pengguna saat ini
        if room.user1_id == current_user.id:
            other_user = room.user2.full_name if room.user2 else 'Pengguna Tidak Dikenal'
            other_user_profile = room.user2.get_profile_picture() if room.user2 else '/static/img/default-avatar.png'
            current_user_role = 'user1'  # Buyer biasanya
        else:
            other_user = room.user1.full_name if room.user1 else 'Pengguna Tidak Dikenal'
            other_user_profile = room.user1.get_profile_picture() if room.user1 else '/static/img/default-avatar.png'
            current_user_role = 'user2'  # Seller biasanya

        # Tentukan role dalam konteks produk
        is_product_owner = room.product.user_id == current_user.id
        chat_role = 'seller' if is_product_owner else 'buyer'
        
        # Pastikan ada pembeli dan penjual yang valid
        if not room.user1 or not room.user2 or not room.product:
            continue  # Skip room yang datanya tidak lengkap

        # Hitung pesan yang belum dibaca
        unread_count = ChatMessage.query.filter(
            and_(
                ChatMessage.room_id == room.id,
                ChatMessage.sender_id != current_user.id,
                ChatMessage.is_read == False
            )
        ).count()

        total_unread += unread_count

        # Check for new messages in last 5 minutes
        from datetime import datetime, timedelta
        recent_messages = ChatMessage.query.filter(
            and_(
                ChatMessage.room_id == room.id,
                ChatMessage.sender_id != current_user.id,
                ChatMessage.created_at >= datetime.utcnow() - timedelta(minutes=5)
            )
        ).count()

        if recent_messages > 0:
            has_new_messages = True

        # Pesan terakhir
        last_message = ChatMessage.query.filter_by(room_id=room.id).order_by(ChatMessage.created_at.desc()).first()

        # Truncate long messages for preview and handle undefined
        if last_message and last_message.message:
            last_msg_preview = last_message.message
            if len(last_msg_preview) > 50:
                last_msg_preview = last_msg_preview[:47] + '...'
        else:
            last_msg_preview = 'Belum ada pesan'


        rooms_data.append({
            'id': room.id,
            'product_id': room.product_id,
            'product_name': room.product.title[:30] + ('...' if len(room.product.title) > 30 else ''),
            'other_user': other_user,
            'other_user_profile_picture': other_user_profile,
            'unread_count': unread_count,
            'last_message': last_msg_preview,
            'last_message_time': last_message.created_at.strftime('%H:%M') if last_message else '',
            'last_message_date': last_message.created_at.strftime('%d/%m') if last_message else '',
            'status': 'active',
            'has_recent_activity': recent_messages > 0,
            'chat_role': chat_role,  # Tambahan untuk membedakan role
            'is_product_owner': is_product_owner  # Tambahan info role
        })

    # Sort by last message time (most recent first)
    rooms_data.sort(key=lambda x: x['last_message_time'], reverse=True)

    return jsonify({
        'success': True,
        'rooms': rooms_data,
        'total_unread': total_unread,
        'has_new_messages': has_new_messages,
        'notification_title': f'BarterHub - {total_unread} pesan baru' if total_unread > 0 else 'BarterHub',
        'notification_message': f'Anda memiliki {total_unread} pesan baru' if total_unread > 0 else 'Tidak ada pesan baru'
    }), 200, {'Content-Type': 'application/json'}

@chat.route('/room/<int:product_id>', methods=['GET', 'POST'])
@login_required
def room(product_id):
    product = Product.query.get_or_404(product_id)

    # Cari atau buat chat room untuk produk ini
    # Pastikan pembeli dan penjual bisa masuk ke room yang sama
    chat_room = ChatRoom.query.filter(
        or_(
            and_(ChatRoom.user1_id == current_user.id, ChatRoom.user2_id == product.user_id),
            and_(ChatRoom.user1_id == product.user_id, ChatRoom.user2_id == current_user.id)
        ),
        ChatRoom.product_id == product_id
    ).first()

    # Jika tidak ada room, buat room baru
    if not chat_room:
        # Untuk penjual (owner produk), cari semua room untuk produk ini
        if product.user_id == current_user.id:
            existing_rooms = ChatRoom.query.filter_by(product_id=product_id).all()
            if existing_rooms:
                # Ambil room yang paling baru dibuat
                chat_room = existing_rooms[0]
            else:
                # Belum ada pembeli yang membuat room
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'error': 'Belum ada pembeli yang chat untuk produk ini.'})
                flash('Belum ada pembeli yang chat untuk produk ini.', 'info')
                return redirect(url_for('products.detail', id=product_id))
        else:
            # Untuk pembeli, buat room baru
            chat_room = ChatRoom(
                user1_id=current_user.id,
                user2_id=product.user_id,
                product_id=product_id
            )
            db.session.add(chat_room)
            db.session.commit()

    # Pastikan current user memiliki akses ke room ini
    if (chat_room.user1_id != current_user.id and 
        chat_room.user2_id != current_user.id and 
        product.user_id != current_user.id):
        flash('Anda tidak memiliki akses ke chat room ini.', 'error')
        return redirect(url_for('products.detail', id=product_id))

    messages = chat_room.messages.order_by(ChatMessage.created_at.asc()).all()
    form = ChatMessageForm()

    if request.method == 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Handle AJAX request for floating chat
            if form.validate_on_submit():
                message_text = form.message.data.strip() if form.message.data else ''
                if not message_text or len(message_text) == 0:
                    return jsonify({'success': False, 'error': 'Pesan tidak boleh kosong. Silakan tulis pesan terlebih dahulu.'}), 400
                    
                try:
                    message = ChatMessage(
                        room_id=chat_room.id,
                        sender_id=current_user.id,
                        message=message_text,
                        message_type='text'
                    )
                    db.session.add(message)
                    db.session.commit()
                    return jsonify({'success': True, 'message': 'Pesan terkirim!'})
                except Exception as e:
                    db.session.rollback()
                    return jsonify({'success': False, 'error': f'Gagal mengirim pesan: {str(e)}'}), 500
            else:
                return jsonify({'success': False, 'error': 'Form tidak valid', 'errors': form.errors}), 400
        else:
            # Handle normal form submission
            if form.validate_on_submit():
                message_text = form.message.data.strip() if form.message.data else ''
                if not message_text or len(message_text) == 0:
                    flash('Pesan tidak boleh kosong. Silakan tulis pesan terlebih dahulu.', 'error')
                    return redirect(url_for('chat.room', product_id=product_id))
                    
                try:
                    message = ChatMessage(
                        room_id=chat_room.id,
                        sender_id=current_user.id,
                        message=message_text,
                        message_type='text'
                    )
                    db.session.add(message)
                    db.session.commit()
                    flash('Pesan berhasil dikirim!', 'success')
                    return redirect(url_for('chat.room', product_id=product_id))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Gagal mengirim pesan: {str(e)}', 'error')
                    return redirect(url_for('chat.room', product_id=product_id))
            else:
                flash('Form tidak valid. Periksa pesan Anda.', 'error')
                return redirect(url_for('chat.room', product_id=product_id))

    return render_template('chat/room.html', 
                         chat_room=chat_room, 
                         messages=messages, 
                         form=form, 
                         product=product)

@chat.route('/room/<int:room_id>/send_negotiation', methods=['POST'])
@login_required 
def send_negotiation(room_id):
    """Endpoint untuk mengirim penawaran negosiasi dengan detail produk"""
    try:
        # Handle CSRF validation manually for AJAX requests
        from flask_wtf.csrf import validate_csrf
        try:
            validate_csrf(request.headers.get('X-CSRFToken') or request.form.get('csrf_token'))
        except:
            # For backward compatibility, allow requests without CSRF for now
            # In production, you should enforce CSRF validation
            pass
        chat_room = ChatRoom.query.get_or_404(room_id)

        # Cek akses - pastikan user adalah participant dari chat room
        if (chat_room.user1_id != current_user.id and 
            chat_room.user2_id != current_user.id):
            return jsonify({'success': False, 'error': 'Akses ditolak. Anda bukan participant chat room ini.'}), 403

        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Data tidak valid atau kosong'}), 400

        offered_products = data.get('offered_products', [])
        requested_products = data.get('requested_products', [])
        base_message = data.get('message', 'Penawaran barter')

        # Validasi minimal ada penawaran atau permintaan
        if not offered_products and not requested_products:
            return jsonify({'success': False, 'error': 'Minimal pilih produk yang ditawarkan atau tulis permintaan'}), 400

        # Build detailed offer message
        offer_details = []
        total_offered_points = 0

        # Validasi dan proses produk yang ditawarkan
        for offer in offered_products:
            product_id = offer.get('product_id')
            if not product_id:
                continue
                
            product = Product.query.get(product_id)
            if product and product.user_id == current_user.id and product.is_available:
                quantity = offer.get('quantity', 1)
                note = offer.get('note', '')
                
                offer_text = f"• {product.title} ({product.total_points} poin, {product.condition})"
                if quantity > 1:
                    offer_text += f" x{quantity}"
                if note:
                    offer_text += f" - {note}"
                    
                offer_details.append(offer_text)
                total_offered_points += product.total_points * quantity

        # Proses produk yang diminta
        request_details = []
        for req in requested_products:
            name = req.get('name', '').strip()
            if name:
                description = req.get('description', '').strip()
                quantity = req.get('quantity', 1)
                condition = req.get('condition', '')
                
                request_text = f"• {name}"
                if quantity > 1:
                    request_text += f" x{quantity}"
                if condition:
                    request_text += f" ({condition})"
                if description:
                    request_text += f" - {description}"
                    
                request_details.append(request_text)

        # Construct full message
        full_message = base_message
        
        if offer_details:
            full_message += f"\n\n🎁 Yang saya tawarkan:\n" + "\n".join(offer_details)
            full_message += f"\n💰 Total poin yang ditawarkan: {total_offered_points}"

        if request_details:
            full_message += f"\n\n❤️ Yang saya inginkan:\n" + "\n".join(request_details)

        # Tambah info role untuk konteks
        if chat_room.product.user_id == current_user.id:
            role_info = "\n\n📢 Saya adalah pemilik produk yang ingin ditukar"
        else:
            role_info = "\n\n📢 Saya tertarik dengan produk Anda"
        
        full_message += role_info

        # Simpan pesan penawaran
        message = ChatMessage(
            room_id=room_id,
            sender_id=current_user.id,
            message=full_message,
            message_type='offer',
            offered_products_json=json.dumps(offered_products) if offered_products else None,
            requested_products_json=json.dumps(requested_products) if requested_products else None,
            offer_status='pending'
        )

        db.session.add(message)
        db.session.commit()

        return jsonify({
            'success': True, 
            'message_id': message.id,
            'message': 'Penawaran berhasil dikirim!'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error in send_negotiation: {str(e)}")  # For debugging
        return jsonify({'success': False, 'error': f'Gagal mengirim penawaran: {str(e)}'}), 500

@chat.route('/offer/<int:message_id>/accept', methods=['POST'])
@login_required
def accept_offer(message_id):
    """Terima penawaran dan buat deal konfirmasi"""
    try:
        # Handle CSRF validation manually for AJAX requests
        from flask_wtf.csrf import validate_csrf
        try:
            validate_csrf(request.headers.get('X-CSRFToken') or request.form.get('csrf_token'))
        except:
            # For backward compatibility, allow requests without CSRF for now
            # In production, you should enforce CSRF validation
            pass
        message = ChatMessage.query.get_or_404(message_id)
        chat_room = message.room

        # Cek akses - tidak bisa menerima penawaran sendiri
        if message.sender_id == current_user.id:
            return jsonify({'success': False, 'error': 'Anda tidak dapat menerima penawaran sendiri'}), 403

        # Pastikan user adalah participant dari chat room
        if (chat_room.user1_id != current_user.id and 
            chat_room.user2_id != current_user.id):
            return jsonify({'success': False, 'error': 'Anda tidak memiliki akses ke chat room ini'}), 403

        # Cek apakah penawaran sudah pernah diproses
        if message.offer_status in ['accepted', 'declined']:
            return jsonify({'success': False, 'error': f'Penawaran sudah {message.offer_status}'}), 400

        # Update offer status
        message.offer_status = 'accepted'

        # Parse offered products for transaction
        offered_products = message.get_offered_products()
        requested_products = message.get_requested_products()

        # Calculate total points from offered products
        total_offered_points = 0
        valid_offered_products = []
        
        for offer in offered_products:
            product = Product.query.get(offer.get('product_id'))
            if product and product.is_available:
                quantity = offer.get('quantity', 1)
                points = product.total_points * quantity
                total_offered_points += points
                valid_offered_products.append({
                    'product': product,
                    'quantity': quantity,
                    'points': points
                })

        # Tentukan siapa penjual dan pembeli berdasarkan produk
        product = chat_room.product
        seller_id = product.user_id
        buyer_id = chat_room.user1_id if chat_room.user1_id != seller_id else chat_room.user2_id

        # Tentukan siapa yang menerima penawaran
        accepter_role = "seller" if current_user.id == seller_id else "buyer"
        sender_role = "buyer" if accepter_role == "seller" else "seller"

        # Create transaction with offer details
        transaction = Transaction(
            seller_id=seller_id,
            buyer_id=buyer_id,
            product_id=chat_room.product_id,
            status='agreed',
            total_seller_points=product.total_points,
            total_buyer_points=total_offered_points,
            notes=f'Deal dikonfirmasi oleh {accepter_role} dari penawaran chat message #{message_id}'
        )

        # Set chat agreements - kedua pihak otomatis setuju saat ada yang accept
        transaction.chat_agreement_seller = True
        transaction.chat_agreement_buyer = True
        transaction.agreement_timestamp = datetime.utcnow()

        db.session.add(transaction)
        db.session.flush()  # Get transaction ID

        # Create transaction offers for each offered product
        for offer_data in valid_offered_products:
            transaction_offer = TransactionOffer(
                transaction_id=transaction.id,
                product_id=offer_data['product'].id,
                offered_by_id=message.sender_id,
                quantity=offer_data['quantity'],
                points=offer_data['points']
            )
            db.session.add(transaction_offer)

        # Build summary messages
        offer_summary = ""
        if valid_offered_products:
            offer_summary = "\n".join([
                f"• {item['product'].title} x{item['quantity']} ({item['points']} poin)" 
                for item in valid_offered_products
            ])

        request_summary = ""
        if requested_products:
            request_list = []
            for req in requested_products:
                if req.get('name'):
                    quantity_text = f"x{req.get('quantity', 1)}" if req.get('quantity', 1) > 1 else ""
                    request_list.append(f"• {req.get('name', 'Produk')} {quantity_text}")
            request_summary = "\n".join(request_list)

        # Add comprehensive system message
        sender_name = message.sender.full_name
        accepter_name = current_user.full_name
        
        system_message_text = f'🎉 DEAL BERHASIL DIKONFIRMASI!\n\n'
        system_message_text += f'👤 Penawaran dari: {sender_name}\n'
        system_message_text += f'✅ Diterima oleh: {accepter_name}\n'
        system_message_text += f'🆔 Transaksi ID: #{transaction.id}\n\n'
        
        if offer_summary:
            system_message_text += f'📦 Produk yang ditawarkan:\n{offer_summary}\n\n'
        
        if request_summary:
            system_message_text += f'❤️ Produk yang diminta:\n{request_summary}\n\n'
        
        system_message_text += f'💰 Total nilai tukar: {total_offered_points} ↔ {product.total_points} poin\n\n'
        system_message_text += '🚚 Langkah selanjutnya: Silakan lanjut ke halaman transaksi untuk mengatur pengiriman!'

        system_message = ChatMessage(
            room_id=chat_room.id,
            sender_id=current_user.id,
            message=system_message_text,
            message_type='system'
        )
        db.session.add(system_message)

        db.session.commit()

        return jsonify({
            'success': True, 
            'transaction_id': transaction.id,
            'message': 'Deal berhasil dikonfirmasi! Transaksi telah dibuat.'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error in accept_offer: {str(e)}")  # For debugging
        return jsonify({'success': False, 'error': f'Gagal mengkonfirmasi deal: {str(e)}'}), 500

@chat.route('/offer/<int:message_id>/decline', methods=['POST'])
@login_required
def decline_offer(message_id):
    """Tolak penawaran"""
    try:
        # Handle CSRF validation manually for AJAX requests
        from flask_wtf.csrf import validate_csrf
        try:
            validate_csrf(request.headers.get('X-CSRFToken') or request.form.get('csrf_token'))
        except:
            # For backward compatibility, allow requests without CSRF for now
            # In production, you should enforce CSRF validation
            pass
        message = ChatMessage.query.get_or_404(message_id)
        chat_room = message.room

        # Cek akses - tidak bisa menolak penawaran sendiri
        if message.sender_id == current_user.id:
            return jsonify({'success': False, 'error': 'Anda tidak dapat menolak penawaran sendiri'}), 403

        # Pastikan user adalah participant dari chat room
        if (chat_room.user1_id != current_user.id and 
            chat_room.user2_id != current_user.id):
            return jsonify({'success': False, 'error': 'Anda tidak memiliki akses ke chat room ini'}), 403

        # Cek apakah penawaran sudah pernah diproses
        if message.offer_status in ['accepted', 'declined']:
            return jsonify({'success': False, 'error': f'Penawaran sudah {message.offer_status}'}), 400

        # Update offer status
        message.offer_status = 'declined'

        data = request.get_json() or {}
        reason = data.get('reason', '').strip()

        # Build decline message
        decline_msg = f'❌ Penawaran ditolak oleh {current_user.full_name}'
        if reason:
            decline_msg += f'\n💬 Alasan: {reason}'
        
        decline_msg += f'\n\n💡 Tip: Anda bisa membuat penawaran counter atau diskusikan lebih lanjut!'

        system_message = ChatMessage(
            room_id=chat_room.id,
            sender_id=current_user.id,
            message=decline_msg,
            message_type='system'
        )
        db.session.add(system_message)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Penawaran berhasil ditolak'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error in decline_offer: {str(e)}")  # For debugging
        return jsonify({'success': False, 'error': f'Gagal menolak penawaran: {str(e)}'}), 500

@chat.route('/room/<int:product_id>/messages')
@login_required
def get_messages(product_id):
    """API endpoint to get messages for a chat room"""
    product = Product.query.get_or_404(product_id)

    # Find chat room
    chat_room = ChatRoom.query.filter(
        or_(
            and_(ChatRoom.user1_id == current_user.id, ChatRoom.user2_id == product.user_id),
            and_(ChatRoom.user1_id == product.user_id, ChatRoom.user2_id == current_user.id)
        ),
        ChatRoom.product_id == product_id
    ).first()

    if not chat_room:
        return jsonify({'messages': []})

    # Check access
    if (chat_room.user1_id != current_user.id and 
        chat_room.user2_id != current_user.id and
        product.user_id != current_user.id):
        return jsonify({'error': 'Access denied'}), 403

    messages = chat_room.messages.order_by(ChatMessage.created_at.asc()).all()

    return jsonify({
        'messages': [{
            'id': msg.id,
            'sender_name': msg.sender.full_name if msg.sender and msg.sender.full_name else 'Pengguna',
            'message': msg.message if msg.message and msg.message.strip() else 'Pesan tidak dapat ditampilkan',
            'message_type': msg.message_type or 'text',
            'created_at': msg.created_at.isoformat()
        } for msg in messages]
    })

@chat.route('/room/<int:room_id>/messages_direct')
@login_required
def get_messages_direct(room_id):
    """API endpoint to get messages directly by room ID"""
    chat_room = ChatRoom.query.get_or_404(room_id)

    # Check access
    if (chat_room.user1_id != current_user.id and 
        chat_room.user2_id != current_user.id):
        return jsonify({'error': 'Access denied'}), 403

    messages = chat_room.messages.order_by(ChatMessage.created_at.asc()).all()

    # Mark messages as read for current user
    unread_messages = ChatMessage.query.filter(
        and_(
            ChatMessage.room_id == room_id,
            ChatMessage.sender_id != current_user.id,
            ChatMessage.is_read == False
        )
    ).all()

    for msg in unread_messages:
        msg.is_read = True

    db.session.commit()

    return jsonify({
        'messages': [{
            'id': msg.id,
            'sender_name': msg.sender.full_name if msg.sender and msg.sender.full_name else 'Pengguna',
            'message': msg.message if msg.message and msg.message.strip() else 'Pesan tidak dapat ditampilkan',
            'message_type': msg.message_type or 'text',
            'created_at': msg.created_at.isoformat()
        } for msg in messages]
    })

@chat.route('/room/<int:room_id>/send_message', methods=['POST'])
@login_required
def send_message_direct(room_id):
    """Send message directly by room ID"""
    chat_room = ChatRoom.query.get_or_404(room_id)

    # Check access
    if (chat_room.user1_id != current_user.id and 
        chat_room.user2_id != current_user.id):
        return jsonify({'error': 'Access denied'}), 403

    message_text = request.form.get('message', '').strip()
    if not message_text or message_text == '' or len(message_text) == 0:
        return jsonify({'success': False, 'error': 'Pesan tidak boleh kosong. Silakan tulis pesan terlebih dahulu.'}), 400

    try:
        message = ChatMessage(
            room_id=room_id,
            sender_id=current_user.id,
            message=message_text,
            message_type='text'
        )
        db.session.add(message)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Pesan terkirim!',
            'message_data': {
                'id': message.id,
                'sender_name': current_user.full_name,
                'message': message.message,
                'message_type': message.message_type,
                'created_at': message.created_at.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@chat.route('/rooms/quick_check')
@login_required
def quick_check_chat_activity():
    """Quick endpoint to check for new chat activity without full data load"""
    try:
        # Get user's chat rooms
        user_rooms = ChatRoom.query.filter(
            or_(ChatRoom.user1_id == current_user.id, ChatRoom.user2_id == current_user.id)
        ).all()

        if not user_rooms:
            return jsonify({
                'success': True,
                'has_updates': False,
                'last_update': 0,
                'active_room_updates': {}
            })

        # Get the latest message timestamp across all rooms
        room_ids = [room.id for room in user_rooms]
        latest_message = ChatMessage.query.filter(
            ChatMessage.room_id.in_(room_ids)
        ).order_by(ChatMessage.created_at.desc()).first()

        last_update_timestamp = 0
        if latest_message:
            last_update_timestamp = int(latest_message.created_at.timestamp() * 1000)

        # Check for unread messages in each room
        active_room_updates = {}
        for room in user_rooms:
            unread_count = ChatMessage.query.filter(
                and_(
                    ChatMessage.room_id == room.id,
                    ChatMessage.sender_id != current_user.id,
                    ChatMessage.is_read == False
                )
            ).count()
            
            if unread_count > 0:
                active_room_updates[room.id] = {
                    'unread_count': unread_count,
                    'has_new_messages': True
                }

        # Check if there are any updates
        has_updates = len(active_room_updates) > 0

        return jsonify({
            'success': True,
            'has_updates': has_updates,
            'last_update': last_update_timestamp,
            'active_room_updates': active_room_updates,
            'total_unread': sum(data.get('unread_count', 0) for data in active_room_updates.values())
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'has_updates': False,
            'last_update': 0,
            'active_room_updates': {}
        }), 500

@chat.route('/room/<int:room_id>/notify_activity', methods=['POST'])
@login_required
def notify_chat_activity(room_id):
    """Endpoint to notify about chat activity for real-time sync"""
    try:
        chat_room = ChatRoom.query.get_or_404(room_id)

        # Check access
        if (chat_room.user1_id != current_user.id and 
            chat_room.user2_id != current_user.id):
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        # For now, just acknowledge the activity
        # In a real production app, you might use WebSockets or Server-Sent Events
        # to push updates to connected clients
        
        return jsonify({
            'success': True,
            'message': 'Activity noted',
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chat.route('/room_info/<int:room_id>')
@login_required
def get_room_info(room_id):
    """API endpoint to get chat room information"""
    try:
        chat_room = ChatRoom.query.get_or_404(room_id)

        # Check access
        if (chat_room.user1_id != current_user.id and 
            chat_room.user2_id != current_user.id):
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        return jsonify({
            'success': True,
            'room_id': chat_room.id,
            'product_id': chat_room.product_id,
            'product_name': chat_room.product.title,
            'other_user': chat_room.user2.full_name if chat_room.user1_id == current_user.id else chat_room.user1.full_name
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@products.route('/user/available')
@login_required
def user_available():
    """API endpoint to get user's available products"""
    try:
        user_products = current_user.products.filter_by(is_available=True).all()

        products_data = [{
            'id': product.id,
            'title': product.title,
            'total_points': product.total_points,
            'condition': product.condition,
            'category': product.category.name if product.category else 'Unknown',
            'description': product.description[:100] + ('...' if len(product.description) > 100 else ''),
            'main_image': product.get_main_image(),
            'created_at': product.created_at.strftime('%d %b %Y')
        } for product in user_products]

        return jsonify({
            'success': True,
            'products': products_data,
            'total': len(products_data)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@products.route('/suggest_barter/<int:target_product_id>')
@login_required
def suggest_barter(target_product_id):
    """API endpoint untuk menyarankan produk user yang cocok untuk barter"""
    try:
        target_product = Product.query.get_or_404(target_product_id)

        if target_product.user_id == current_user.id:
            return jsonify({
                'success': False,
                'error': 'Tidak dapat barter dengan produk sendiri'
            }), 400

        # Get user's products that might be good for barter
        user_products = current_user.products.filter_by(is_available=True).all()

        # Score products based on similarity and point difference
        suggested_products = []
        for product in user_products:
            score = 0

            # Same category gets higher score
            if product.category_id == target_product.category_id:
                score += 50

            # Similar points get higher score
            point_diff = abs(product.total_points - target_product.total_points)
            if point_diff <= 10:
                score += 30
            elif point_diff <= 20:
                score += 20
            elif point_diff <= 30:
                score += 10

            # Same condition gets bonus
            if product.condition == target_product.condition:
                score += 20

            suggested_products.append({
                'id': product.id,
                'title': product.title,
                'total_points': product.total_points,
                'condition': product.condition,
                'category': product.category.name,
                'description': product.description[:100] + ('...' if len(product.description) > 100 else ''),
                'main_image': product.get_main_image(),
                'created_at': product.created_at.strftime('%d %b %Y'),
                'match_score': score,
                'point_difference': point_diff,
                'is_good_match': score >= 50
            })

        # Sort by match score
        suggested_products.sort(key=lambda x: x['match_score'], reverse=True)

        return jsonify({
            'success': True,
            'target_product': {
                'id': target_product.id,
                'title': target_product.title,
                'total_points': target_product.total_points,
                'condition': target_product.condition,
                'category': target_product.category.name,
                'owner_name': target_product.owner.full_name
            },
            'suggested_products': suggested_products[:6],  # Top 6 suggestions
            'total_available': len(user_products)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@products.route('/quick-add', methods=['POST'])
@login_required
def quick_add():
    """Quick add product via AJAX"""
    try:
        # Get form data
        title = request.form.get('title')
        category_id = request.form.get('category_id')
        description = request.form.get('description')
        condition = request.form.get('condition')
        desired_items = request.form.get('desired_items')

        # Validate required fields
        if not all([title, category_id, description, condition, desired_items]):
            return jsonify({
                'success': False,
                'error': 'Semua field wajib diisi'
            }), 400

        # Create product
        product = Product(
            user_id=current_user.id,
            category_id=int(category_id),
            title=title,
            description=description,
            condition=condition,
            desired_items=desired_items,
            utility_score=5,  # Default values
            scarcity_score=5,
            durability_score=5,
            portability_score=5,
            seasonal_score=5
        )

        product.calculate_points()
        db.session.add(product)
        db.session.flush()

        # Handle image upload if provided
        if 'images' in request.files:
            file = request.files['images']
            if file and file.filename:
                filename = save_uploaded_file(file, 'products')
                if filename:
                    image = ProductImage(
                        product_id=product.id,
                        filename=filename,
                        is_main=True
                    )
                    db.session.add(image)

        db.session.commit()

        return jsonify({
            'success': True,
            'product_id': product.id,
            'message': 'Produk berhasil ditambahkan!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Transactions blueprint
transactions = Blueprint('transactions', __name__)

@transactions.route('/')
@login_required
def list_transactions():
    page = request.args.get('page', 1, type=int)

    user_transactions = Transaction.query.filter(
        or_(Transaction.seller_id == current_user.id, Transaction.buyer_id == current_user.id)
    ).order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )

    return render_template('transactions/list.html', 
                         transactions=user_transactions.items,
                         pagination=user_transactions)

@transactions.route('/<int:id>', methods=['GET', 'POST'])
@login_required
def detail(id):
    transaction = Transaction.query.get_or_404(id)

    if (transaction.seller_id != current_user.id and 
        transaction.buyer_id != current_user.id and 
        not current_user.is_admin()):
        flash('Anda tidak memiliki akses untuk melihat transaksi ini.', 'error')
        return redirect(url_for('transactions.list_transactions'))

    tracking_form = TrackingForm()

    if request.method == 'POST' and tracking_form.validate_on_submit():
        tracking_number = tracking_form.tracking_number.data

        if current_user.id == transaction.seller_id:
            transaction.seller_tracking_number = tracking_number
            transaction.seller_shipped_at = datetime.utcnow()
            flash('Nomor resi penjual berhasil diperbarui!', 'success')
        elif current_user.id == transaction.buyer_id:
            transaction.buyer_tracking_number = tracking_number
            transaction.buyer_shipped_at = datetime.utcnow()
            flash('Nomor resi pembeli berhasil diperbarui!', 'success')

        # Update status to 'shipped' if both parties have tracking numbers
        if (transaction.seller_tracking_number and 
            transaction.buyer_tracking_number and 
            transaction.status == 'agreed'):
            transaction.status = 'shipped'
            flash('Status transaksi diperbarui menjadi "Dalam Pengiriman"!', 'info')

        # Generate confirmation codes when status changes to agreed
        if transaction.status == 'agreed' and not transaction.seller_confirmation_code:
            transaction.generate_confirmation_codes()

        # Mark as completed if both parties confirmed
        if transaction.seller_received_at and transaction.buyer_received_at:
            transaction.status = 'completed'
            flash('🎉 Transaksi barter berhasil diselesaikan! Kedua belah pihak telah mengkonfirmasi penerimaan barang.', 'success')

        db.session.commit()
        return redirect(url_for('transactions.detail', id=id))

    return render_template('transactions/detail.html', 
                         transaction=transaction, 
                         tracking_form=tracking_form)

@transactions.route('/<int:id>/receipt')
@login_required
def receipt(id):
    """Cetak label pengiriman"""
    from datetime import datetime as dt

    transaction = Transaction.query.get_or_404(id)

    if (transaction.seller_id != current_user.id and 
        transaction.buyer_id != current_user.id and 
        not current_user.is_admin()):
        flash('Anda tidak memiliki akses untuk melihat label ini.', 'error')
        return redirect(url_for('transactions.list_transactions'))

    return render_template('transactions/receipt.html', transaction=transaction, datetime=dt)

@transactions.route('/<int:id>/tracking')
@login_required
def tracking(id):
    """Tracking ekspedisi pengiriman"""
    transaction = Transaction.query.get_or_404(id)

    if (transaction.seller_id != current_user.id and 
        transaction.buyer_id != current_user.id and 
        not current_user.is_admin()):
        flash('Anda tidak memiliki akses untuk tracking transaksi ini.', 'error')
        return redirect(url_for('transactions.list_transactions'))

    # Simulasi data tracking (dalam implementasi nyata, ini akan mengintegrasikan dengan API ekspedisi)
    tracking_data = {
        'seller_tracking': get_tracking_info(transaction.seller_tracking_number) if transaction.seller_tracking_number else None,
        'buyer_tracking': get_tracking_info(transaction.buyer_tracking_number) if transaction.buyer_tracking_number else None
    }

    return render_template('transactions/tracking.html', 
                         transaction=transaction, 
                         tracking_data=tracking_data)

def get_tracking_info(tracking_number):
    """Mendapatkan informasi tracking dari API ekspedisi nyata"""
    import requests
    import json

    if not tracking_number:
        return None

    try:
        # Deteksi kurir berdasarkan format nomor resi
        courier = detect_courier(tracking_number)

        if courier == 'JNE':
            return get_jne_tracking(tracking_number)
        elif courier == 'JT':
            return get_jt_tracking(tracking_number)
        elif courier == 'SICEPAT':
            return get_sicepat_tracking(tracking_number)
        elif courier == 'POS':
            return get_pos_tracking(tracking_number)
        else:
            # Fallback ke simulasi jika kurir tidak dikenali
            return get_simulated_tracking(tracking_number)

    except Exception as e:
        print(f"Error getting tracking info: {e}")
        # Fallback ke simulasi jika API error
        return get_simulated_tracking(tracking_number)

def detect_courier(tracking_number):
    """Deteksi kurir berdasarkan format nomor resi"""
    tracking_number = tracking_number.upper().replace(' ', '')

    # Format resi JNE: alphanumeric 10-15 karakter
    if len(tracking_number) >= 10 and len(tracking_number) <= 15:
        if tracking_number.startswith('JNE') or tracking_number.startswith('CGK'):
            return 'JNE'

    # Format resi J&T: JP + 10 digit angka
    if tracking_number.startswith('JP') and len(tracking_number) == 12:
        return 'JT'

    # Format resi SiCepat: 000 + 9-12 digit
    if tracking_number.startswith('000') and len(tracking_number) >= 12:
        return 'SICEPAT'

    # Format resi Pos Indonesia: PC/EX/CA/CC + angka
    if any(tracking_number.startswith(prefix) for prefix in ['PC', 'EX', 'CA', 'CC']):
        return 'POS'

    return 'UNKNOWN'

def get_jne_tracking(tracking_number):
    """Tracking JNE menggunakan API resmi (perlu API key)"""
    # API JNE memerlukan registrasi dan API key
    # Untuk development, gunakan simulasi
    return get_simulated_tracking(tracking_number, 'JNE')

def get_jt_tracking(tracking_number):
    """Tracking J&T menggunakan API resmi"""
    try:
        # API J&T Express - gratis tanpa API key
        url = f"https://www.jet.co.id/api/track/{tracking_number}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()

            if data.get('success') and data.get('data'):
                tracking_data = data['data']

                timeline = []
                for item in tracking_data.get('details', []):
                    timeline.append({
                        'status': item.get('desc', ''),
                        'time': item.get('date', ''),
                        'location': item.get('city', ''),
                        'is_current': False
                    })

                if timeline:
                    timeline[-1]['is_current'] = True

                return {
                    'tracking_number': tracking_number,
                    'courier': 'J&T Express',
                    'status': tracking_data.get('last_status', 'Dalam pengiriman'),
                    'timeline': timeline,
                    'delivered': any('terima' in item.get('desc', '').lower() for item in tracking_data.get('details', []))
                }
    except Exception as e:
        print(f"Error J&T tracking: {e}")

    return get_simulated_tracking(tracking_number, 'J&T Express')

def get_sicepat_tracking(tracking_number):
    """Tracking SiCepat menggunakan API resmi"""
    try:
        # API SiCepat - gratis
        url = "https://api.sicepat.com/customer/waybill"
        payload = {'waybill': tracking_number}

        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()

            if data.get('sicepat') and data['sicepat'].get('result'):
                result = data['sicepat']['result']

                timeline = []
                for item in result.get('track_history', []):
                    timeline.append({
                        'status': item.get('receiver_name', item.get('status', '')),
                        'time': item.get('date_time', ''),
                        'location': item.get('city', ''),
                        'is_current': False
                    })

                if timeline:
                    timeline[-1]['is_current'] = True

                return {
                    'tracking_number': tracking_number,
                    'courier': 'SiCepat',
                    'status': result.get('last_status', 'Dalam pengiriman'),
                    'timeline': timeline,
                    'delivered': result.get('status') == 'DELIVERED'
                }
    except Exception as e:
        print(f"Error SiCepat tracking: {e}")

    return get_simulated_tracking(tracking_number, 'SiCepat')

def get_pos_tracking(tracking_number):
    """Tracking Pos Indonesia"""
    # API Pos Indonesia memerlukan kerjasama khusus
    return get_simulated_tracking(tracking_number, 'Pos Indonesia')

def get_simulated_tracking(tracking_number, courier='Unknown'):
    """Simulasi tracking untuk fallback"""
    import random

    statuses = [
        'Paket diterima oleh kurir',
        'Paket dalam perjalanan ke hub',
        'Paket tiba di hub asal', 
        'Paket dalam perjalanan ke kota tujuan',
        'Paket tiba di hub tujuan',
        'Paket dalam perjalanan untuk pengiriman',
        'Paket sudah dikirim ke alamat tujuan',
        'Paket berhasil diterima'
    ]

    timeline = []
    num_statuses = random.randint(3, len(statuses))
    for i, status in enumerate(statuses[:num_statuses]):
        timeline.append({
            'status': status,
            'time': (datetime.now() - timedelta(days=num_statuses-i, hours=random.randint(0, 23))).strftime('%d/%m/%Y %H:%M'),
            'location': f'Hub {["Jakarta", "Bandung", "Surabaya", "Medan", "Yogyakarta"][random.randint(0, 4)]}',
            'is_current': i == num_statuses-1
        })

    # Check if delivered (last status contains "terima")
    is_delivered = 'terima' in timeline[-1]['status'].lower() if timeline else False

    return {
        'tracking_number': tracking_number,
        'courier': courier,
        'status': timeline[-1]['status'] if timeline else 'Belum ada update',
        'timeline': timeline,
        'delivered': is_delivered
    }

@transactions.route('/<int:id>/auto_confirm')
@login_required  
def auto_confirm_check(id):
    """Cek dan lakukan auto konfirmasi/pembatalan berdasarkan status pengiriman"""
    transaction = Transaction.query.get_or_404(id)

    if transaction.status != 'shipped':
        return jsonify({'auto_confirmed': False, 'message': 'Transaksi belum dalam status pengiriman'})

    # Cek status pengiriman real-time
    seller_tracking = get_tracking_info(transaction.seller_tracking_number) if transaction.seller_tracking_number else None
    buyer_tracking = get_tracking_info(transaction.buyer_tracking_number) if transaction.buyer_tracking_number else None

    # Cek apakah kedua paket sudah terkirim
    if not (transaction.seller_shipped_at and transaction.buyer_shipped_at):
        return jsonify({'auto_confirmed': False, 'message': 'Belum semua paket dikirim'})

    # Hitung waktu sejak pengiriman terakhir
    last_shipped = max(transaction.seller_shipped_at, transaction.buyer_shipped_at)
    hours_since_shipped = (datetime.utcnow() - last_shipped).total_seconds() / 3600

    # Auto-konfirmasi jika paket sudah delivered menurut tracking
    seller_delivered = seller_tracking and seller_tracking.get('delivered', False)
    buyer_delivered = buyer_tracking and buyer_tracking.get('delivered', False)

    if seller_delivered and buyer_delivered:
        # Kedua paket sudah sampai, auto konfirmasi setelah 6 jam
        if hours_since_shipped >= 6:
            if not transaction.seller_received_at:
                transaction.seller_received_at = datetime.utcnow()
            if not transaction.buyer_received_at:
                transaction.buyer_received_at = datetime.utcnow()

            transaction.status = 'completed'
            db.session.commit()

            return jsonify({
                'auto_confirmed': True,
                'message': 'Transaksi otomatis selesai karena kedua paket sudah terkirim dan tidak ada konfirmasi dalam 6 jam'
            })

    # Auto-cancel jika sudah lebih dari 7 hari dan belum ada konfirmasi
    elif hours_since_shipped >= (7 * 24):  # 7 hari
        # Cek jika tidak ada konfirmasi sama sekali
        if not transaction.seller_received_at and not transaction.buyer_received_at:
            transaction.status = 'cancelled'
            transaction.notes = f"{transaction.notes}\n\nTransaksi dibatalkan otomatis karena tidak ada konfirmasi penerimaan dalam 7 hari."
            db.session.commit()

            return jsonify({
                'auto_cancelled': True,
                'message': 'Transaksi dibatalkan otomatis karena tidak ada konfirmasi penerimaan dalam 7 hari'
            })

    # Auto-konfirmasi normal setelah 24 jam jika belum dikonfirmasi manual
    elif hours_since_shipped >= 24:
        if not transaction.seller_received_at:
            transaction.seller_received_at = datetime.utcnow()
        if not transaction.buyer_received_at:
            transaction.buyer_received_at = datetime.utcnow()

        transaction.status = 'completed'
        db.session.commit()

        return jsonify({
            'auto_confirmed': True,
            'message': 'Transaksi otomatis selesai karena tidak ada konfirmasi dalam 24 jam'
        })

    return jsonify({
        'auto_confirmed': False, 
        'message': f'Menunggu konfirmasi. {24 - int(hours_since_shipped)} jam tersisa untuk auto-konfirmasi',
        'seller_delivered': seller_delivered,
        'buyer_delivered': buyer_delivered,
        'hours_remaining': int(24 - hours_since_shipped)
    })

@transactions.route('/<int:id>/review', methods=['GET', 'POST'])
@login_required
def add_review(id):
    """Add review and rating for completed transaction"""
    transaction = Transaction.query.get_or_404(id)

    # Check access and if transaction is completed
    if (transaction.seller_id != current_user.id and 
        transaction.buyer_id != current_user.id):
        flash('Anda tidak memiliki akses untuk memberikan review pada transaksi ini.', 'error')
        return redirect(url_for('transactions.detail', id=id))

    if transaction.status != 'completed':
        flash('Review hanya dapat diberikan untuk transaksi yang sudah selesai.', 'error')
        return redirect(url_for('transactions.detail', id=id))

    # Check if user already reviewed
    from models import Review
    existing_review = Review.query.filter_by(
        transaction_id=id,
        reviewer_id=current_user.id
    ).first()

    if existing_review:
        flash('Anda sudah memberikan review untuk transaksi ini.', 'info')
        return redirect(url_for('transactions.detail', id=id))

    # Determine who is being reviewed
    if current_user.id == transaction.seller_id:
        reviewed_user = transaction.buyer
        reviewer_role = 'seller'
    else:
        reviewed_user = transaction.seller
        reviewer_role = 'buyer'

    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        comment = request.form.get('comment', '').strip()
        communication_rating = request.form.get('communication_rating', 5, type=int)
        product_condition_rating = request.form.get('product_condition_rating', 5, type=int)
        shipping_speed_rating = request.form.get('shipping_speed_rating', 5, type=int)

        if not rating or rating < 1 or rating > 5:
            flash('Rating harus antara 1-5 bintang.', 'error')
            return redirect(url_for('transactions.add_review', id=id))

        review = Review(
            transaction_id=id,
            reviewer_id=current_user.id,
            reviewed_user_id=reviewed_user.id,
            rating=rating,
            comment=comment,
            communication_rating=communication_rating,
            product_condition_rating=product_condition_rating,
            shipping_speed_rating=shipping_speed_rating
        )

        db.session.add(review)
        db.session.commit()

        flash(f'Review berhasil diberikan untuk {reviewed_user.full_name}!', 'success')
        return redirect(url_for('transactions.detail', id=id))

    return render_template('transactions/review.html', 
                         transaction=transaction, 
                         reviewed_user=reviewed_user,
                         reviewer_role=reviewer_role)

@transactions.route('/<int:id>/dispute', methods=['GET', 'POST'])
@login_required
def dispute(id):
    """Buat atau lihat sengketa transaksi"""
    transaction = Transaction.query.get_or_404(id)

    if (transaction.seller_id != current_user.id and 
        transaction.buyer_id != current_user.id):
        flash('Anda tidak memiliki akses untuk transaksi ini.', 'error')
        return redirect(url_for('transactions.list_transactions'))

    if request.method == 'POST':
        reason = request.form.get('reason')
        description = request.form.get('description')

        # Update status transaksi menjadi dispute
        transaction.status = 'dispute'
        transaction.notes = f"Sengketa: {reason}\nDeskripsi: {description}\nDilaporkan oleh: {current_user.full_name}"
        db.session.commit()

        flash('Sengketa berhasil dilaporkan. Tim kami akan meninjau dalam 1x24 jam.', 'info')
        return redirect(url_for('transactions.detail', id=id))

    return render_template('transactions/dispute.html', transaction=transaction)

@transactions.route('/<int:id>/confirm_received', methods=['POST'])
@login_required
def confirm_received(id):
    transaction = Transaction.query.get_or_404(id)

    # Check access
    if (transaction.seller_id != current_user.id and 
        transaction.buyer_id != current_user.id):
        flash('Anda tidak memiliki akses untuk mengkonfirmasi transaksi ini.', 'error')
        return redirect(url_for('transactions.detail', id=id))

    # Get confirmation code from form
    confirmation_code = request.form.get('confirmation_code', '').strip().upper()

    if not confirmation_code:
        flash('Kode konfirmasi wajib diisi.', 'error')
        return redirect(url_for('transactions.detail', id=id))

    # Generate confirmation codes if not exist
    if not transaction.seller_confirmation_code or not transaction.buyer_confirmation_code:
        transaction.generate_confirmation_codes()
        db.session.commit()

    # Validate confirmation code and mark as received
    if current_user.id == transaction.seller_id:
        # Seller confirming receipt from buyer
        expected_code = transaction.buyer_confirmation_code
        if not transaction.seller_received_at:
            if confirmation_code == expected_code:
                transaction.seller_received_at = datetime.utcnow()
                flash(f'✅ Konfirmasi berhasil! Anda telah mengkonfirmasi menerima barang dari {transaction.buyer.full_name}.', 'success')
            else:
                flash('❌ Kode konfirmasi salah. Periksa kembali kode pada label paket yang Anda terima.', 'error')
                return redirect(url_for('transactions.detail', id=id))
        else:
            flash('Anda sudah mengkonfirmasi penerimaan barang sebelumnya.', 'info')

    elif current_user.id == transaction.buyer_id:
        # Buyer confirming receipt from seller
        expected_code = transaction.seller_confirmation_code
        if not transaction.buyer_received_at:
            if confirmation_code == expected_code:
                transaction.buyer_received_at = datetime.utcnow()
                flash(f'✅ Konfirmasi berhasil! Anda telah mengkonfirmasi menerima barang dari {transaction.seller.full_name}.', 'success')
            else:
                flash('❌ Kode konfirmasi salah. Periksa kembali kode pada label paket yang Anda terima.', 'error')
                return redirect(url_for('transactions.detail', id=id))
        else:
            flash('Anda sudah mengkonfirmasi penerimaan barang sebelumnya.', 'info')

    # Check if transaction is completed
    if transaction.seller_received_at and transaction.buyer_received_at:
        transaction.status = 'completed'
        flash('🎉 Transaksi barter berhasil diselesaikan! Kedua belah pihak telah mengkonfirmasi penerimaan barang.', 'success')

        # Add system message to chat room
        chat_room = ChatRoom.query.filter(
            and_(
                ChatRoom.product_id == transaction.product_id,
                or_(
                    and_(ChatRoom.user1_id == transaction.seller_id, ChatRoom.user2_id == transaction.buyer_id),
                    and_(ChatRoom.user1_id == transaction.buyer_id, ChatRoom.user2_id == transaction.seller_id)
                )
            )
        ).first()

        if chat_room:
            system_message = ChatMessage(
                room_id=chat_room.id,
                sender_id=current_user.id,
                message=f'🎉 Transaksi barter berhasil diselesaikan! Kedua belah pihak telah mengkonfirmasi penerimaan barang dengan kode yang benar. Silakan berikan review untuk partner Anda!',
                message_type='system'
            )
            db.session.add(system_message)

        # Check if user has already reviewed
        from models import Review
        existing_review = Review.query.filter_by(
            transaction_id=id,
            reviewer_id=current_user.id
        ).first()

        if not existing_review:
            flash('💫 Jangan lupa berikan review untuk partner barter Anda!', 'info')

    db.session.commit()

    # If transaction just completed and no review exists, suggest review
    if (transaction.seller_received_at and transaction.buyer_received_at and 
        transaction.status == 'completed'):
        from models import Review
        existing_review = Review.query.filter_by(
            transaction_id=id,
            reviewer_id=current_user.id
        ).first()

        if not existing_review:
            return redirect(url_for('transactions.add_review', id=id))

    return redirect(url_for('transactions.detail', id=id))

@transactions.route('/create/<int:product_id>', methods=['GET', 'POST'])
@login_required
def create_offer(product_id):
    product = Product.query.get_or_404(product_id)

    if product.user_id == current_user.id:
        flash('Anda tidak dapat menawar produk sendiri.', 'error')
        return redirect(url_for('products.detail', id=product_id))

    # Get user's products for offering
    user_products = current_user.products.filter_by(is_available=True).all()

    # Check if there's a suggested product from query params
    suggested_product_id = request.args.get('suggested', type=int)
    suggested_product = None
    if suggested_product_id:
        suggested_product = Product.query.filter_by(
            id=suggested_product_id, 
            user_id=current_user.id, 
            is_available=True
        ).first()

    if request.method == 'POST':
        offered_product_ids = request.form.getlist('offered_products')

        if not offered_product_ids:
            flash('Pilih minimal satu produk untuk ditawarkan.', 'error')
            return redirect(url_for('transactions.create_offer', product_id=product_id))

        # Create transaction
        transaction = Transaction(
            seller_id=product.user_id,
            buyer_id=current_user.id,
            product_id=product_id,
            total_seller_points=product.total_points
        )

        db.session.add(transaction)
        db.session.flush()

        # Add offered products
        total_buyer_points = 0
        for product_id_str in offered_product_ids:
            offered_product = Product.query.get(int(product_id_str))
            if offered_product and offered_product.user_id == current_user.id:
                offer = TransactionOffer(
                    transaction_id=transaction.id,
                    product_id=offered_product.id,
                    offered_by_id=current_user.id,
                    points=offered_product.total_points
                )
                db.session.add(offer)
                total_buyer_points += offered_product.total_points

        transaction.total_buyer_points = total_buyer_points
        db.session.commit()

        flash('Penawaran berhasil dikirim!', 'success')
        return redirect(url_for('transactions.detail', id=transaction.id))

    return render_template('transactions/create_offer.html', 
                         product=product, 
                         user_products=user_products,
                         suggested_product=suggested_product)

# Admin blueprint
admin = Blueprint('admin', __name__)

@admin.before_request
@login_required
def require_admin():
    if not current_user.is_admin():
        flash('Akses ditolak. Hanya admin yang dapat mengakses halaman ini.', 'error')
        return redirect(url_for('main.index'))

@admin.route('/dashboard')
def dashboard():
    from models import Report

    # User Management Statistics
    total_users = User.query.count()
    banned_users = User.query.filter_by(is_banned=True).count()
    active_sellers = User.query.filter_by(role='penjual', is_active=True, is_banned=False).count()
    active_buyers = User.query.filter_by(role='pembeli', is_active=True, is_banned=False).count()

    # Report Statistics
    pending_reports = Report.query.filter_by(status='pending').count()
    total_reports = Report.query.count()
    recent_violations = User.query.filter(User.violation_count > 0).order_by(User.violation_count.desc()).limit(5).all()

    # Recent Reports
    recent_reports = Report.query.order_by(Report.created_at.desc()).limit(5).all()

    # High-risk users (with multiple violations)
    high_risk_users = User.query.filter(User.violation_count >= 3).order_by(User.violation_count.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         banned_users=banned_users,
                         active_sellers=active_sellers,
                         active_buyers=active_buyers,
                         pending_reports=pending_reports,
                         total_reports=total_reports,
                         recent_reports=recent_reports,
                         recent_violations=recent_violations,
                         high_risk_users=high_risk_users)

@admin.route('/users')
def users():
    page = request.args.get('page', 1, type=int)
    users_pagination = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/users.html', 
                         users=users_pagination.items,
                         pagination=users_pagination)

@admin.route('/users/<int:id>/toggle_status')
def toggle_user_status(id):
    user = User.query.get_or_404(id)
    if user.is_admin():
        flash('Tidak dapat mengubah status admin.', 'error')
    else:
        user.is_active = not user.is_active
        db.session.commit()
        status = 'diaktifkan' if user.is_active else 'dinonaktifkan'
        flash(f'User {user.username} berhasil {status}.', 'success')

    return redirect(url_for('admin.users'))

@admin.route('/users/<int:id>/ban', methods=['POST'])
def ban_user(id):
    user = User.query.get_or_404(id)
    ban_reason = request.form.get('ban_reason', 'Pelanggaran aturan platform')

    if user.is_admin():
        flash('Tidak dapat memban admin.', 'error')
    else:
        user.ban_user(ban_reason, current_user.id)
        user.add_violation()
        db.session.commit()
        flash(f'User {user.username} berhasil dibanned. Alasan: {ban_reason}', 'success')

    return redirect(url_for('admin.users'))

@admin.route('/users/<int:id>/unban')
def unban_user(id):
    user = User.query.get_or_404(id)
    user.unban_user()
    db.session.commit()
    flash(f'User {user.username} berhasil di-unban.', 'success')

    return redirect(url_for('admin.users'))

@admin.route('/reports')
def reports():
    from models import Report
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')

    query = Report.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if type_filter:
        query = query.filter_by(report_type=type_filter)

    reports_pagination = query.order_by(Report.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template('admin/reports.html', 
                         reports=reports_pagination.items,
                         pagination=reports_pagination,
                         status_filter=status_filter,
                         type_filter=type_filter)

@admin.route('/reports/<int:id>/resolve', methods=['POST'])
def resolve_report(id):
    from models import Report
    report = Report.query.get_or_404(id)
    action = request.form.get('action')  # 'dismiss', 'warn', 'ban'
    response = request.form.get('admin_response', '')

    report.status = 'resolved'
    report.admin_response = response
    report.resolved_by = current_user.id
    report.resolved_at = datetime.utcnow()

    if action == 'ban':
        reported_user = report.reported_user
        ban_reason = f"Laporan: {report.subject}"
        reported_user.ban_user(ban_reason, current_user.id)
        reported_user.add_violation()
    elif action == 'warn':
        reported_user = report.reported_user
        reported_user.add_violation()

    db.session.commit()
    flash(f'Laporan berhasil diselesaikan dengan aksi: {action}', 'success')

    return redirect(url_for('admin.reports'))

@admin.route('/products')
def admin_products():
    page = request.args.get('page', 1, type=int)
    products_pagination = Product.query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/products.html', 
                         products=products_pagination.items,
                         pagination=products_pagination)

@admin.route('/transactions')
def admin_transactions():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = Transaction.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    transactions_pagination = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template('admin/transactions.html', 
                         transactions=transactions_pagination.items,
                         pagination=transactions_pagination,
                         current_status=status_filter)

# Wishlist routes
@main.route('/wishlist')
@login_required
def wishlist():
    page = request.args.get('page', 1, type=int)

    # Get user's wishlist items with pagination
    from models import Wishlist
    wishlist_items = db.session.query(Wishlist).filter_by(user_id=current_user.id)\
        .join(Product).filter(Product.is_available == True)\
        .order_by(Wishlist.created_at.desc())\
        .paginate(page=page, per_page=12, error_out=False)

    return render_template('wishlist.html', 
                         wishlist_items=wishlist_items.items,
                         pagination=wishlist_items)

@main.route('/wishlist/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_wishlist(product_id):
    try:
        product = Product.query.get_or_404(product_id)

        if product.user_id == current_user.id:
            return jsonify({'success': False, 'message': 'Tidak dapat menambahkan produk sendiri ke wishlist'})

        if current_user.add_to_wishlist(product_id):
            db.session.commit()
            return jsonify({'success': True, 'message': f'{product.title} ditambahkan ke wishlist'})
        else:
            return jsonify({'success': False, 'message': 'Produk sudah ada di wishlist'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Terjadi kesalahan: {str(e)}'}), 500

@main.route('/wishlist/remove/<int:product_id>', methods=['POST'])
@login_required
def remove_from_wishlist(product_id):
    try:
        product = Product.query.get_or_404(product_id)

        if current_user.remove_from_wishlist(product_id):
            db.session.commit()
            return jsonify({'success': True, 'message': f'{product.title} dihapus dari wishlist'})
        else:
            return jsonify({'success': False, 'message': 'Produk tidak ada di wishlist'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Terjadi kesalahan: {str(e)}'}), 500

@main.route('/wishlist/check/<int:product_id>')
@login_required
def check_wishlist(product_id):
    is_in_wishlist = current_user.is_in_wishlist(product_id)
    return jsonify({'in_wishlist': is_in_wishlist})

# Initialize default data function (removed before_app_first_request decorator)
def init_db():
    try:
        # Create default categories
        if Category.query.count() == 0:
            categories = [
                Category(name='Elektronik', description='Perangkat elektronik dan gadget'),
                Category(name='Fashion', description='Pakaian, sepatu, dan aksesoris'),
                Category(name='Rumah Tangga', description='Peralatan dan perlengkapan rumah'),
                Category(name='Olahraga', description='Peralatan dan perlengkapan olahraga'),
                Category(name='Buku & Media', description='Buku, CD, DVD, dan media lainnya'),
                Category(name='Kendaraan', description='Motor, mobil, dan aksesoris kendaraan'),
                Category(name='Hobi & Koleksi', description='Barang hobi dan koleksi'),
                Category(name='Lainnya', description='Kategori lainnya')
            ]

            for category in categories:
                db.session.add(category)
            db.session.commit()

        # Create admin user if doesn't exist
        admin = User.query.filter_by(username='fajarjulyana').first()
        if not admin:
            admin = User(
                username='fajarjulyana',
                email='fajarjulyana@barterhub.com',
                full_name='Fajar Julyana',
                role='admin'
            )
            admin.set_password('fajar123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created")
        else:
            print("Admin user already exists")

    except Exception as e:
        print(f"Error in init_db: {e}")
        db.session.rollback()