from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from datetime import datetime
import requests
import secrets
import logging
from decimal import Decimal

from config import Config
import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['DEBUG'] = Config.DEBUG

# ==================== HELPER FUNCTIONS ====================

def convert_to_serializable(obj):
    """Convert Decimal and datetime objects to JSON serializable format"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    return obj

def send_telegram_message(chat_id, message):
    """Send message via Telegram bot"""
    try:
        url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=data)
        return response.json()
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return None

def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = session.get('session_token')
        if not session_token:
            return jsonify({'error': 'Authentication required'}), 401

        user_session = db.get_session(session_token)
        if not user_session:
            session.clear()
            return jsonify({'error': 'Session expired'}), 401

        # Add user_id to request context
        request.user_id = user_session['user_id']
        return f(*args, **kwargs)
    return decorated_function

def business_required(f):
    """Decorator to require Business subscription"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = session.get('session_token')
        if not session_token:
            return jsonify({'error': 'Authentication required'}), 401

        user_session = db.get_session(session_token)
        if not user_session:
            session.clear()
            return jsonify({'error': 'Session expired'}), 401

        # Get user and check subscription
        user = db.get_user(user_session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Check if user has Business subscription
        subscription = user.get('subscription', 'free').lower()
        if subscription != 'business':
            return jsonify({
                'error': 'Business tarifi kerak',
                'redirect': 'https://balansai-app.onrender.com',
                'message': 'Bu funksiya faqat Business tarifi uchun mavjud'
            }), 403

        # Add user_id and user to request context
        request.user_id = user_session['user_id']
        request.user = user
        return f(*args, **kwargs)
    return decorated_function

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/login')
def login_page():
    """Login page"""
    return render_template('login.html')

@app.route('/api/auth/request-code', methods=['POST'])
def request_verification_code():
    """Request OTP code for phone number"""
    try:
        data = request.get_json()
        phone_number = data.get('phone')

        if not phone_number:
            return jsonify({'error': 'Telefon raqam kiritilmadi'}), 400

        # Normalize phone number (remove spaces, dashes, etc.)
        phone_number = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

        # Check if user exists with this phone number
        user = db.get_user_by_phone(phone_number)
        if not user:
            return jsonify({'error': 'Bu telefon raqam bazada topilmadi'}), 404

        # Generate OTP code
        otp_code = db.create_phone_verification(phone_number)
        if not otp_code:
            return jsonify({'error': 'Kod yaratishda xatolik yuz berdi'}), 500

        # Get user's Telegram ID to send OTP
        telegram_user_id = user.get('user_id')  # Assuming user_id is Telegram ID

        # Send OTP via Telegram
        message = f"🔐 <b>Balans AI kirish kodi:</b>\n\n<code>{otp_code}</code>\n\nKod {Config.OTP_EXPIRY_MINUTES} daqiqa amal qiladi."
        result = send_telegram_message(telegram_user_id, message)

        if result and result.get('ok'):
            return jsonify({
                'success': True,
                'message': 'Kod Telegram botga yuborildi',
                'expires_in': Config.OTP_EXPIRY_MINUTES * 60  # in seconds
            }), 200
        else:
            return jsonify({'error': 'Telegram botga kod yuborishda xatolik'}), 500

    except Exception as e:
        logger.error(f"Error in request_verification_code: {e}")
        return jsonify({'error': 'Serverda xatolik yuz berdi'}), 500

@app.route('/api/auth/verify-code', methods=['POST'])
def verify_code():
    """Verify OTP code and create session"""
    try:
        data = request.get_json()
        phone_number = data.get('phone')
        otp_code = data.get('code')

        if not phone_number or not otp_code:
            return jsonify({'error': 'Telefon raqam va kod kiritilishi shart'}), 400

        # Normalize phone number
        phone_number = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

        # Verify OTP code
        is_valid = db.verify_phone_code(phone_number, otp_code)

        if not is_valid:
            db.increment_verification_attempts(phone_number)
            return jsonify({'error': 'Kod noto\'g\'ri yoki muddati o\'tgan'}), 400

        # Get user
        user = db.get_user_by_phone(phone_number)
        if not user:
            return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404

        # Create session
        session_token = secrets.token_urlsafe(32)
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent')

        success = db.create_web_session(
            user['user_id'],
            session_token,
            ip_address,
            user_agent
        )

        if not success:
            return jsonify({'error': 'Sessiya yaratishda xatolik'}), 500

        # Set session cookie
        session['session_token'] = session_token
        session['user_id'] = user['user_id']

        return jsonify({
            'success': True,
            'message': 'Muvaffaqiyatli kirdingiz',
            'user': convert_to_serializable(user)
        }), 200

    except Exception as e:
        logger.error(f"Error in verify_code: {e}")
        return jsonify({'error': 'Serverda xatolik yuz berdi'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    """Logout user"""
    try:
        session_token = session.get('session_token')
        if session_token:
            db.delete_session(session_token)
        session.clear()
        return jsonify({'success': True, 'message': 'Tizimdan chiqdingiz'}), 200
    except Exception as e:
        logger.error(f"Error in logout: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current authenticated user"""
    try:
        user = db.get_user(request.user_id)
        if user:
            return jsonify(convert_to_serializable(user)), 200
        return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

# ==================== MAIN APP ROUTES ====================

@app.route('/')
def index():
    """Main application page"""
    session_token = session.get('session_token')
    if not session_token or not db.get_session(session_token):
        return redirect(url_for('login_page'))

    # Check if user has Business subscription
    user_session = db.get_session(session_token)
    if user_session:
        user = db.get_user(user_session['user_id'])
        if user:
            subscription = user.get('subscription', 'free').lower()
            if subscription != 'business':
                # Redirect non-business users to the mobile app
                return redirect('https://balansai-app.onrender.com')

    return render_template('index.html')

# ==================== USER ROUTES ====================

@app.route('/api/user', methods=['GET'])
@login_required
def get_user_info():
    """Get user information"""
    try:
        user = db.get_user(request.user_id)
        if user:
            return jsonify(convert_to_serializable(user)), 200
        return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404
    except Exception as e:
        logger.error(f"Error in get_user_info: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/user/<int:user_id>/update', methods=['POST'])
@login_required
def update_user_info(user_id):
    """Update user information"""
    try:
        if request.user_id != user_id:
            return jsonify({'error': 'Ruxsat berilmagan'}), 403

        data = request.get_json()
        success = db.update_user(user_id, **data)

        if success:
            return jsonify({'success': True, 'message': 'Ma\'lumotlar yangilandi'}), 200
        return jsonify({'error': 'Yangilashda xatolik'}), 500
    except Exception as e:
        logger.error(f"Error in update_user_info: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

# ==================== TRANSACTION ROUTES ====================

@app.route('/api/transactions', methods=['GET'])
@login_required
def get_transactions():
    """Get user transactions"""
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        transaction_type = request.args.get('type')

        transactions = db.get_transactions(request.user_id, limit, offset, transaction_type)
        return jsonify(convert_to_serializable(transactions)), 200
    except Exception as e:
        logger.error(f"Error in get_transactions: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/transactions', methods=['POST'])
@login_required
def add_transaction():
    """Add new transaction"""
    try:
        data = request.get_json()
        transaction_type = data.get('type')
        amount = data.get('amount')
        currency = data.get('currency', 'UZS')
        category = data.get('category')
        description = data.get('description')

        if not transaction_type or not amount:
            return jsonify({'error': 'Type va amount majburiy'}), 400

        transaction_id = db.add_transaction(
            request.user_id,
            transaction_type,
            amount,
            currency,
            category,
            description
        )

        if transaction_id:
            return jsonify({
                'success': True,
                'transaction_id': transaction_id,
                'message': 'Tranzaksiya qo\'shildi'
            }), 201
        return jsonify({'error': 'Tranzaksiya qo\'shishda xatolik'}), 500
    except Exception as e:
        logger.error(f"Error in add_transaction: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/balance', methods=['GET'])
@login_required
def get_balance():
    """Get user balance"""
    try:
        balance = db.get_balance(request.user_id)
        return jsonify({'balance': balance}), 200
    except Exception as e:
        logger.error(f"Error in get_balance: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/statistics', methods=['GET'])
@login_required
def get_statistics():
    """Get user statistics"""
    try:
        period = request.args.get('period', 'month')
        stats = db.get_statistics(request.user_id, period)
        return jsonify(convert_to_serializable(stats)), 200
    except Exception as e:
        logger.error(f"Error in get_statistics: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

# ==================== DEBT ROUTES ====================

@app.route('/api/debts', methods=['GET'])
@login_required
def get_debts():
    """Get user debts"""
    try:
        debt_type = request.args.get('type')
        debts = db.get_debts(request.user_id, debt_type)
        return jsonify(convert_to_serializable(debts)), 200
    except Exception as e:
        logger.error(f"Error in get_debts: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/debts', methods=['POST'])
@login_required
def add_debt():
    """Add new debt"""
    try:
        data = request.get_json()
        debt_type = data.get('type')
        amount = data.get('amount')
        person_name = data.get('person_name')
        currency = data.get('currency', 'UZS')
        description = data.get('description')
        due_date = data.get('due_date')

        if not debt_type or not amount or not person_name:
            return jsonify({'error': 'Type, amount va person_name majburiy'}), 400

        debt_id = db.add_debt(
            request.user_id,
            debt_type,
            amount,
            person_name,
            currency,
            description,
            due_date
        )

        if debt_id:
            return jsonify({
                'success': True,
                'debt_id': debt_id,
                'message': 'Qarz qo\'shildi'
            }), 201
        return jsonify({'error': 'Qarz qo\'shishda xatolik'}), 500
    except Exception as e:
        logger.error(f"Error in add_debt: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

# ==================== REMINDER ROUTES ====================

@app.route('/api/reminders', methods=['GET'])
@login_required
def get_reminders():
    """Get user reminders"""
    try:
        reminders = db.get_reminders(request.user_id)
        return jsonify(convert_to_serializable(reminders)), 200
    except Exception as e:
        logger.error(f"Error in get_reminders: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/reminders', methods=['POST'])
@login_required
def add_reminder():
    """Add new reminder"""
    try:
        data = request.get_json()
        title = data.get('title')
        amount = data.get('amount')
        currency = data.get('currency', 'UZS')
        reminder_date = data.get('reminder_date')
        repeat_interval = data.get('repeat_interval')

        if not title:
            return jsonify({'error': 'Title majburiy'}), 400

        reminder_id = db.add_reminder(
            request.user_id,
            title,
            amount,
            currency,
            reminder_date,
            repeat_interval
        )

        if reminder_id:
            return jsonify({
                'success': True,
                'reminder_id': reminder_id,
                'message': 'Eslatma qo\'shildi'
            }), 201
        return jsonify({'error': 'Eslatma qo\'shishda xatolik'}), 500
    except Exception as e:
        logger.error(f"Error in add_reminder: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

# ==================== CONTACT ROUTES ====================

@app.route('/api/contacts', methods=['GET'])
@login_required
def get_contacts():
    """Get user contacts"""
    try:
        contact_type = request.args.get('type')
        contacts = db.get_contacts(request.user_id, contact_type)
        return jsonify(convert_to_serializable(contacts)), 200
    except Exception as e:
        logger.error(f"Error in get_contacts: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/contacts', methods=['POST'])
@login_required
def add_contact():
    """Add new contact"""
    try:
        data = request.get_json()
        name = data.get('name')
        phone = data.get('phone')
        contact_type = data.get('type', 'person')
        notes = data.get('notes')

        if not name:
            return jsonify({'error': 'Name majburiy'}), 400

        contact_id = db.add_contact(
            request.user_id,
            name,
            phone,
            contact_type,
            notes
        )

        if contact_id:
            return jsonify({
                'success': True,
                'contact_id': contact_id,
                'message': 'Kontakt qo\'shildi'
            }), 201
        return jsonify({'error': 'Kontakt qo\'shishda xatolik'}), 500
    except Exception as e:
        logger.error(f"Error in add_contact: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

# ==================== LIMIT ROUTES ====================

@app.route('/api/limit', methods=['GET'])
@login_required
def get_monthly_limit():
    """Get monthly spending limit"""
    try:
        limit = db.get_monthly_limit(request.user_id)
        return jsonify({'limit': limit}), 200
    except Exception as e:
        logger.error(f"Error in get_monthly_limit: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/limit', methods=['POST'])
@login_required
def set_monthly_limit():
    """Set monthly spending limit"""
    try:
        data = request.get_json()
        limit_amount = data.get('limit')

        if limit_amount is None:
            return jsonify({'error': 'Limit kiritilishi shart'}), 400

        success = db.set_monthly_limit(request.user_id, limit_amount)

        if success:
            return jsonify({'success': True, 'message': 'Limit o\'rnatildi'}), 200
        return jsonify({'error': 'Limit o\'rnatishda xatolik'}), 500
    except Exception as e:
        logger.error(f"Error in set_monthly_limit: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

# ==================== WAREHOUSE ROUTES ====================

@app.route('/api/warehouse/products', methods=['GET'])
@login_required
def get_warehouse_products():
    """Get warehouse products"""
    try:
        products = db.get_warehouse_products(request.user_id)
        return jsonify(convert_to_serializable(products)), 200
    except Exception as e:
        logger.error(f"Error in get_warehouse_products: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/warehouse/products', methods=['POST'])
@login_required
def add_warehouse_product():
    """Add warehouse product"""
    try:
        data = request.get_json()
        name = data.get('name')
        quantity = data.get('quantity', 0)
        unit = data.get('unit', 'dona')
        price = data.get('price', 0)
        category = data.get('category')

        if not name:
            return jsonify({'error': 'Mahsulot nomi majburiy'}), 400

        product_id = db.add_warehouse_product(request.user_id, name, quantity, unit, price, category)

        if product_id:
            return jsonify({
                'success': True,
                'product_id': product_id,
                'message': 'Mahsulot qo\'shildi'
            }), 201
        return jsonify({'error': 'Mahsulot qo\'shishda xatolik'}), 500
    except Exception as e:
        logger.error(f"Error in add_warehouse_product: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/warehouse/products/<int:product_id>', methods=['PUT'])
@login_required
def update_warehouse_product(product_id):
    """Update warehouse product"""
    try:
        data = request.get_json()
        success = db.update_warehouse_product(request.user_id, product_id, **data)

        if success:
            return jsonify({'success': True, 'message': 'Mahsulot yangilandi'}), 200
        return jsonify({'error': 'Yangilashda xatolik'}), 500
    except Exception as e:
        logger.error(f"Error in update_warehouse_product: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

# ==================== EMPLOYEE ROUTES ====================

@app.route('/api/employees', methods=['GET'])
@login_required
def get_employees():
    """Get employees"""
    try:
        employees = db.get_employees(request.user_id)
        return jsonify(convert_to_serializable(employees)), 200
    except Exception as e:
        logger.error(f"Error in get_employees: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/employees', methods=['POST'])
@login_required
def add_employee():
    """Add employee"""
    try:
        data = request.get_json()
        name = data.get('name')
        position = data.get('position')
        phone = data.get('phone')
        salary = data.get('salary', 0)

        if not name:
            return jsonify({'error': 'Ism majburiy'}), 400

        employee_id = db.add_employee(request.user_id, name, position, phone, salary)

        if employee_id:
            return jsonify({
                'success': True,
                'employee_id': employee_id,
                'message': 'Xodim qo\'shildi'
            }), 201
        return jsonify({'error': 'Xodim qo\'shishda xatolik'}), 500
    except Exception as e:
        logger.error(f"Error in add_employee: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/employees/<int:employee_id>', methods=['PUT'])
@login_required
def update_employee(employee_id):
    """Update employee"""
    try:
        data = request.get_json()
        success = db.update_employee(request.user_id, employee_id, **data)

        if success:
            return jsonify({'success': True, 'message': 'Xodim yangilandi'}), 200
        return jsonify({'error': 'Yangilashda xatolik'}), 500
    except Exception as e:
        logger.error(f"Error in update_employee: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

# ==================== TASK ROUTES ====================

@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    """Get tasks"""
    try:
        status = request.args.get('status')
        tasks = db.get_tasks(request.user_id, status)
        return jsonify(convert_to_serializable(tasks)), 200
    except Exception as e:
        logger.error(f"Error in get_tasks: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/tasks', methods=['POST'])
@login_required
def add_task():
    """Add task"""
    try:
        data = request.get_json()
        title = data.get('title')
        description = data.get('description')
        due_date = data.get('due_date')
        priority = data.get('priority', 'medium')
        assigned_to = data.get('assigned_to')

        if not title:
            return jsonify({'error': 'Sarlavha majburiy'}), 400

        task_id = db.add_task(request.user_id, title, description, due_date, priority, assigned_to)

        if task_id:
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': 'Vazifa qo\'shildi'
            }), 201
        return jsonify({'error': 'Vazifa qo\'shishda xatolik'}), 500
    except Exception as e:
        logger.error(f"Error in add_task: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    """Update task"""
    try:
        data = request.get_json()
        success = db.update_task(request.user_id, task_id, **data)

        if success:
            return jsonify({'success': True, 'message': 'Vazifa yangilandi'}), 200
        return jsonify({'error': 'Yangilashda xatolik'}), 500
    except Exception as e:
        logger.error(f"Error in update_task: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

# ==================== REPORTS ROUTES ====================

@app.route('/api/reports/summary', methods=['GET'])
@login_required
def get_report_summary():
    """Get comprehensive report summary"""
    try:
        period = request.args.get('period', 'month')
        summary = db.get_report_summary(request.user_id, period)
        return jsonify(convert_to_serializable(summary)), 200
    except Exception as e:
        logger.error(f"Error in get_report_summary: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/reports/analytics', methods=['GET'])
@login_required
def get_analytics():
    """Get detailed analytics"""
    try:
        period = request.args.get('period', 'month')
        analytics = db.get_analytics(request.user_id, period)
        return jsonify(convert_to_serializable(analytics)), 200
    except Exception as e:
        logger.error(f"Error in get_analytics: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

@app.route('/api/reports/categories', methods=['GET'])
@login_required
def get_category_breakdown():
    """Get spending by category"""
    try:
        period = request.args.get('period', 'month')
        categories = db.get_category_breakdown(request.user_id, period)
        return jsonify(convert_to_serializable(categories)), 200
    except Exception as e:
        logger.error(f"Error in get_category_breakdown: {e}")
        return jsonify({'error': 'Xatolik yuz berdi'}), 500

# ==================== CONFIG ROUTE ====================

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get app configuration"""
    return jsonify({
        'bot_username': Config.TELEGRAM_BOT_USERNAME,
        'trial_periods': Config.TRIAL_PERIODS
    }), 200

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Sahifa topilmadi'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Serverda xatolik yuz berdi'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)
