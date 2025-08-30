
#!/usr/bin/env python3
"""
Script untuk membuat dummy data transaksi untuk testing sistem konfirmasi penerimaan
"""

from datetime import datetime, timedelta
from app import create_app
from models import db, User, Category, Product, ProductImage, Transaction, ChatRoom, ChatMessage
import secrets
import string

def create_dummy_data():
    app = create_app()
    with app.app_context():
        print("Creating dummy data for transaction testing...")
        
        # Create test users
        seller = User.query.filter_by(username='seller_test').first()
        if not seller:
            seller = User(
                username='seller_test',
                email='seller@test.com',
                full_name='John Penjual',
                role='penjual',
                phone='081234567890',
                address='Jl. Penjual No. 123, Jakarta Selatan',
                kode_pos='12345'
            )
            seller.set_password('password123')
            db.session.add(seller)
            print("✓ Created seller user: seller_test")
        
        buyer = User.query.filter_by(username='buyer_test').first()
        if not buyer:
            buyer = User(
                username='buyer_test',
                email='buyer@test.com',
                full_name='Jane Pembeli',
                role='pembeli',
                phone='081987654321',
                address='Jl. Pembeli No. 456, Jakarta Utara',
                kode_pos='54321'
            )
            buyer.set_password('password123')
            db.session.add(buyer)
            print("✓ Created buyer user: buyer_test")
        
        db.session.commit()
        
        # Get or create categories
        elektronik_cat = Category.query.filter_by(name='Elektronik').first()
        if not elektronik_cat:
            elektronik_cat = Category(name='Elektronik', description='Perangkat elektronik dan gadget')
            db.session.add(elektronik_cat)
            db.session.commit()
        
        # Create seller's product
        seller_product = Product.query.filter_by(title='iPhone 13 - Test Product').first()
        if not seller_product:
            seller_product = Product(
                user_id=seller.id,
                category_id=elektronik_cat.id,
                title='iPhone 13 - Test Product',
                description='iPhone 13 128GB kondisi sangat baik, fullset dengan box dan charger original. Digunakan hanya 6 bulan, tidak pernah jatuh atau rusak.',
                condition='Like New',
                desired_items='Laptop gaming, MacBook, atau smartphone Android flagship',
                utility_score=9,
                scarcity_score=7,
                durability_score=8,
                portability_score=10,
                seasonal_score=8
            )
            seller_product.calculate_points()
            db.session.add(seller_product)
            print("✓ Created seller product: iPhone 13")
        
        # Create buyer's product
        buyer_product = Product.query.filter_by(title='Samsung Galaxy S23 - Test Product').first()
        if not buyer_product:
            buyer_product = Product(
                user_id=buyer.id,
                category_id=elektronik_cat.id,
                title='Samsung Galaxy S23 - Test Product',
                description='Samsung Galaxy S23 256GB warna Phantom Black. Kondisi mulus, masih bergaransi resmi SEIN. Kelengkapan box, charger, earphone.',
                condition='New',
                desired_items='iPhone terbaru, iPad, atau laptop',
                utility_score=9,
                scarcity_score=6,
                durability_score=9,
                portability_score=10,
                seasonal_score=8
            )
            buyer_product.calculate_points()
            db.session.add(buyer_product)
            print("✓ Created buyer product: Samsung Galaxy S23")
        
        db.session.commit()
        
        # Create chat room
        chat_room = ChatRoom.query.filter_by(
            product_id=seller_product.id,
            user1_id=buyer.id,
            user2_id=seller.id
        ).first()
        
        if not chat_room:
            chat_room = ChatRoom(
                user1_id=buyer.id,
                user2_id=seller.id,
                product_id=seller_product.id,
                status='active'
            )
            db.session.add(chat_room)
            db.session.commit()
            print("✓ Created chat room")
        
        # Add chat messages
        existing_msgs = ChatMessage.query.filter_by(room_id=chat_room.id).count()
        if existing_msgs == 0:
            messages = [
                {
                    'sender_id': buyer.id,
                    'message': 'Halo, saya tertarik dengan iPhone 13 Anda. Apakah masih available?',
                    'created_at': datetime.utcnow() - timedelta(hours=2)
                },
                {
                    'sender_id': seller.id,
                    'message': 'Halo! Ya masih available. Saya lihat Anda punya Samsung Galaxy S23, kondisinya bagaimana?',
                    'created_at': datetime.utcnow() - timedelta(hours=1, minutes=50)
                },
                {
                    'sender_id': buyer.id,
                    'message': 'Kondisi masih sangat bagus, baru beli 3 bulan lalu. Masih bergaransi resmi. Mau tukar dengan iPhone 13 Anda?',
                    'created_at': datetime.utcnow() - timedelta(hours=1, minutes=45)
                },
                {
                    'sender_id': seller.id,
                    'message': 'Boleh! Tapi kita tambah ongkir ya, soalnya nilai iPhone saya sedikit lebih tinggi.',
                    'created_at': datetime.utcnow() - timedelta(hours=1, minutes=30)
                },
                {
                    'sender_id': buyer.id,
                    'message': 'Oke deal! Bagaimana proses selanjutnya?',
                    'created_at': datetime.utcnow() - timedelta(hours=1, minutes=15)
                },
                {
                    'sender_id': seller.id,
                    'message': 'Perfect! Saya setuju untuk melakukan barter. Mari kita lanjutkan ke tahap pengiriman.',
                    'created_at': datetime.utcnow() - timedelta(hours=1)
                }
            ]
            
            for msg_data in messages:
                msg = ChatMessage(
                    room_id=chat_room.id,
                    sender_id=msg_data['sender_id'],
                    message=msg_data['message'],
                    created_at=msg_data['created_at']
                )
                db.session.add(msg)
            
            print("✓ Created chat messages")
        
        # Create transaction
        existing_transaction = Transaction.query.filter_by(
            seller_id=seller.id,
            buyer_id=buyer.id,
            product_id=seller_product.id
        ).first()
        
        if not existing_transaction:
            transaction = Transaction(
                seller_id=seller.id,
                buyer_id=buyer.id,
                product_id=seller_product.id,
                status='shipped',  # Set to shipped for testing confirmation
                total_seller_points=seller_product.total_points,
                total_buyer_points=buyer_product.total_points,
                
                # Complete addresses for both parties
                seller_address=seller.address,
                buyer_address=buyer.address,
                seller_phone=seller.phone,
                buyer_phone=buyer.phone,
                
                # Chat agreements
                chat_agreement_seller=True,
                chat_agreement_buyer=True,
                agreement_timestamp=datetime.utcnow() - timedelta(minutes=30),
                
                # Shipping info
                seller_tracking_number='JNE123456789',
                buyer_tracking_number='JT987654321',
                seller_shipped_at=datetime.utcnow() - timedelta(days=1),
                buyer_shipped_at=datetime.utcnow() - timedelta(days=1),
                
                notes='Transaksi barter iPhone 13 dengan Samsung Galaxy S23. Kedua belah pihak sepakat dengan kondisi barang.'
            )
            
            # Generate confirmation codes
            transaction.generate_confirmation_codes()
            
            db.session.add(transaction)
            db.session.commit()
            
            print("✓ Created transaction with shipping status")
            print(f"  Transaction ID: {transaction.id}")
            print(f"  Seller confirmation code: {transaction.seller_confirmation_code}")
            print(f"  Buyer confirmation code: {transaction.buyer_confirmation_code}")
            
            # Add system message about transaction creation
            system_msg = ChatMessage(
                room_id=chat_room.id,
                sender_id=seller.id,
                message=f'✅ Transaksi #{transaction.id} telah dibuat dan kedua paket sudah dikirim! '
                       f'Gunakan kode konfirmasi untuk mengkonfirmasi penerimaan barang:\n'
                       f'• Kode untuk paket dari penjual: {transaction.seller_confirmation_code}\n'
                       f'• Kode untuk paket dari pembeli: {transaction.buyer_confirmation_code}',
                message_type='system',
                created_at=datetime.utcnow() - timedelta(minutes=25)
            )
            db.session.add(system_msg)
            db.session.commit()
            
        else:
            transaction = existing_transaction
            print("✓ Transaction already exists")
        
        print(f"\n🎉 Dummy data created successfully!")
        print(f"\nTest Users Created:")
        print(f"1. Seller: username='seller_test', password='password123'")
        print(f"   Name: {seller.full_name}")
        print(f"   Product: {seller_product.title}")
        print(f"\n2. Buyer: username='buyer_test', password='password123'")
        print(f"   Name: {buyer.full_name}")
        print(f"   Product: {buyer_product.title}")
        
        print(f"\nTransaction Details:")
        print(f"- ID: {transaction.id}")
        print(f"- Status: {transaction.status}")
        print(f"- Seller tracking: {transaction.seller_tracking_number}")
        print(f"- Buyer tracking: {transaction.buyer_tracking_number}")
        print(f"- Seller confirmation code: {transaction.seller_confirmation_code}")
        print(f"- Buyer confirmation code: {transaction.buyer_confirmation_code}")
        
        print(f"\nHow to test:")
        print(f"1. Login sebagai 'seller_test' dan pergi ke transaksi #{transaction.id}")
        print(f"2. Klik 'Konfirmasi Diterima' dan masukkan kode: {transaction.buyer_confirmation_code}")
        print(f"3. Login sebagai 'buyer_test' dan lakukan hal yang sama dengan kode: {transaction.seller_confirmation_code}")
        print(f"4. Setelah kedua pihak konfirmasi, status akan berubah menjadi 'completed'")

if __name__ == '__main__':
    create_dummy_data()
