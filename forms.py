from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField, SelectField, IntegerField, PasswordField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, ValidationError
from models import User, Category

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Masuk')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Nama Lengkap', validators=[DataRequired(), Length(min=2, max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Konfirmasi Password', validators=[
        DataRequired(), EqualTo('password', message='Password harus sama')])
    role = SelectField('Role', choices=[('penjual', 'Penjual'), ('pembeli', 'Pembeli')], validators=[DataRequired()])
    phone = StringField('Nomor Telepon', validators=[DataRequired(), Length(min=10, max=20)])
    address = TextAreaField('Alamat Lengkap (untuk pengiriman)', validators=[DataRequired(), Length(min=10, max=500)])
    kode_pos = StringField('Kode Pos', validators=[Length(max=10)], render_kw={'placeholder': 'Contoh: 40123 (opsional, bisa diisi nanti di agen)'})
    submit = SubmitField('Daftar')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username sudah digunakan. Pilih username lain.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email sudah terdaftar. Gunakan email lain.')

class ProductForm(FlaskForm):
    title = StringField('Judul Produk', validators=[DataRequired(), Length(min=5, max=200)])
    description = TextAreaField('Deskripsi', validators=[DataRequired(), Length(min=10)])
    category_id = SelectField('Kategori', coerce=int, validators=[DataRequired()])
    condition = SelectField('Kondisi', choices=[
        ('New', 'Baru'),
        ('Like New', 'Seperti Baru'),
        ('Good', 'Baik'),
        ('Fair', 'Cukup'),
        ('Poor', 'Buruk')
    ], validators=[DataRequired()])

    # Point calculation factors
    utility_score = IntegerField('Nilai Kegunaan (1-10)', validators=[DataRequired(), NumberRange(min=1, max=10)], default=5)
    scarcity_score = IntegerField('Nilai Kelangkaan (1-10)', validators=[DataRequired(), NumberRange(min=1, max=10)], default=5)
    durability_score = IntegerField('Nilai Daya Tahan (1-10)', validators=[DataRequired(), NumberRange(min=1, max=10)], default=5)
    portability_score = IntegerField('Nilai Portabilitas (1-10)', validators=[DataRequired(), NumberRange(min=1, max=10)], default=5)
    seasonal_score = IntegerField('Nilai Musiman (1-10)', validators=[DataRequired(), NumberRange(min=1, max=10)], default=5)

    # What user wants to trade for
    desired_items = TextAreaField('Apa yang Anda inginkan sebagai gantinya?', 
                                  validators=[DataRequired(), Length(min=5, max=500)],
                                  render_kw={'placeholder': 'Contoh: Smartphone Android, Laptop gaming, Sepeda motor, dll. Jelaskan secara detail barang apa yang Anda cari untuk ditukar dengan produk ini.'})

    images = FileField('Gambar Produk (Maksimal 5)', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Hanya file gambar yang diperbolehkan!')
    ])

    submit = SubmitField('Simpan Produk')

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(c.id, c.name) for c in Category.query.all()]

class ChatMessageForm(FlaskForm):
    message = TextAreaField('Pesan', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('Kirim')

class OfferForm(FlaskForm):
    product_ids = HiddenField('Product IDs')
    message = TextAreaField('Pesan Penawaran', validators=[Length(max=500)])
    submit = SubmitField('Kirim Penawaran')

class TrackingForm(FlaskForm):
    tracking_number = StringField('Nomor Resi', validators=[DataRequired(), Length(min=5, max=50)])
    submit = SubmitField('Simpan Resi')

class ConfirmationForm(FlaskForm):
    confirmation_code = StringField('Kode Konfirmasi', 
                                   validators=[DataRequired(), Length(min=8, max=8)],
                                   render_kw={'placeholder': 'Masukkan kode 8 karakter'})
    submit = SubmitField('Konfirmasi Penerimaan')

class QuickProductForm(FlaskForm):
    """Form for buyers to quickly add products during chat negotiations"""
    title = StringField('Nama Produk', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Deskripsi Singkat', validators=[DataRequired(), Length(min=5, max=300)])
    category_id = SelectField('Kategori', coerce=int, validators=[DataRequired()])
    condition = SelectField('Kondisi', choices=[
        ('New', 'Baru'),
        ('Like New', 'Seperti Baru'), 
        ('Good', 'Baik'),
        ('Fair', 'Cukup')
    ], validators=[DataRequired()])
    desired_items = TextAreaField('Ingin ditukar dengan apa?', 
                                  validators=[DataRequired(), Length(min=5, max=200)],
                                  render_kw={'placeholder': 'Sebutkan barang yang Anda cari'})
    images = FileField('Foto Produk', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Hanya file gambar!')
    ])
    submit = SubmitField('Tambah Produk Cepat')

    def __init__(self, *args, **kwargs):
        super(QuickProductForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(c.id, c.name) for c in Category.query.all()]



class ProfileEditForm(FlaskForm):
    full_name = StringField('Nama Lengkap', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Nomor Telepon', validators=[DataRequired(), Length(min=10, max=20)])
    address = TextAreaField('Alamat Lengkap', validators=[DataRequired(), Length(min=10, max=500)])
    kode_pos = StringField('Kode Pos', validators=[Length(max=10)], render_kw={'placeholder': 'Contoh: 40123 (opsional)'})
    submit = SubmitField('Perbarui Profil')

    def __init__(self, current_user, *args, **kwargs):
        super(ProfileEditForm, self).__init__(*args, **kwargs)
        self.current_user = current_user

    def validate_email(self, email):
        if email.data != self.current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email sudah terdaftar. Gunakan email lain.')