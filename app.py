from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import threading
from bot import run_bot

app = Flask(__name__)
app.config['SECRET_KEY'] = 'zylve-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bot_token = db.Column(db.String(250))
    chat_id = db.Column(db.String(100))
    router_ip = db.Column(db.String(100))
    router_port = db.Column(db.Integer)
    router_user = db.Column(db.String(100))
    router_pass = db.Column(db.String(150))
    router_identity = db.Column(db.String(100))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET', 'POST'])
@login_required
def dashboard():
    config = Config.query.first()
    if not config:
        config = Config(id=1, router_port=8728, router_identity="MIKROTIK")
        db.session.add(config)
        db.session.commit()

    if request.method == 'POST':
        config.bot_token = request.form.get('bot_token')
        config.chat_id = request.form.get('chat_id')
        config.router_ip = request.form.get('router_ip')
        config.router_port = int(request.form.get('router_port', 8728))
        config.router_user = request.form.get('router_user')
        config.router_identity = request.form.get('router_identity')
        
        new_pass = request.form.get('router_pass')
        if new_pass:
            config.router_pass = new_pass
            
        db.session.commit()
        flash('Konfigurasi berhasil disimpan!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('index.html', config=config)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Login gagal. Periksa username dan password.', 'danger')
    return render_template('index.html', login_page=True)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if User.query.first():
        flash('Registrasi ditutup. Akun admin sudah ada.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Akun berhasil dibuat! Silakan login.', 'success')
        return redirect(url_for('login'))
    return render_template('index.html', register_page=True)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
