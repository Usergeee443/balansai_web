import mysql.connector
from dbutils.pooled_db import PooledDB
from datetime import datetime, timedelta
import threading
import logging
from decimal import Decimal
import random
import string
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global connection pool
pool = None
pool_lock = threading.Lock()

# Cache for currency rates
currency_cache = {}
cache_timestamp = None
CACHE_DURATION = 300  # 5 minutes

def get_db_connection():
    """Get database connection from pool"""
    global pool
    if pool is None:
        with pool_lock:
            if pool is None:
                pool = PooledDB(
                    creator=mysql.connector,
                    maxconnections=20,
                    mincached=2,
                    maxcached=10,
                    host=Config.DB_HOST,
                    user=Config.DB_USER,
                    password=Config.DB_PASSWORD,
                    database=Config.DB_NAME,
                    port=Config.DB_PORT,
                    charset='utf8mb4',
                    autocommit=True
                )
    return pool.connection()

def init_database():
    """Initialize database and create tables if they don't exist"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create phone_verifications table for web login
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS phone_verifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                phone_number VARCHAR(20) NOT NULL,
                otp_code VARCHAR(10) NOT NULL,
                attempts INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_verified BOOLEAN DEFAULT FALSE,
                INDEX idx_phone (phone_number),
                INDEX idx_expires (expires_at)
            )
        """)

        # Create web_sessions table for session management
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS web_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45),
                user_agent TEXT,
                INDEX idx_token (session_token),
                INDEX idx_user (user_id),
                INDEX idx_expires (expires_at)
            )
        """)

        # Create warehouse_products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS warehouse_products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                name VARCHAR(255) NOT NULL,
                quantity DECIMAL(10,2) DEFAULT 0,
                unit VARCHAR(50) DEFAULT 'dona',
                price DECIMAL(15,2) DEFAULT 0,
                category VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user (user_id)
            )
        """)

        # Create employees table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                name VARCHAR(255) NOT NULL,
                position VARCHAR(100),
                phone VARCHAR(20),
                salary DECIMAL(15,2) DEFAULT 0,
                status ENUM('active', 'inactive') DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user (user_id),
                INDEX idx_status (status)
            )
        """)

        # Create tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                due_date DATE,
                priority ENUM('low', 'medium', 'high') DEFAULT 'medium',
                status ENUM('pending', 'in_progress', 'completed', 'cancelled') DEFAULT 'pending',
                assigned_to INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user (user_id),
                INDEX idx_status (status),
                INDEX idx_assigned (assigned_to)
            )
        """)

        # Add password column to users table if it doesn't exist
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NULL")
            logger.info("Added password_hash column to users table")
        except mysql.connector.Error as e:
            if e.errno == 1060:  # Duplicate column name
                logger.info("password_hash column already exists")
            else:
                logger.error(f"Error adding password_hash column: {e}")

        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

# ==================== PHONE VERIFICATION FUNCTIONS ====================

def create_phone_verification(phone_number):
    """Create OTP code for phone verification"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Generate random OTP code
        otp_code = ''.join(random.choices(string.digits, k=Config.OTP_LENGTH))
        expires_at = datetime.now() + timedelta(minutes=Config.OTP_EXPIRY_MINUTES)

        # Delete old verifications for this phone
        cursor.execute(
            "DELETE FROM phone_verifications WHERE phone_number = %s AND is_verified = FALSE",
            (phone_number,)
        )

        # Insert new verification
        cursor.execute("""
            INSERT INTO phone_verifications (phone_number, otp_code, expires_at)
            VALUES (%s, %s, %s)
        """, (phone_number, otp_code, expires_at))

        conn.commit()
        cursor.close()
        conn.close()

        return otp_code
    except Exception as e:
        logger.error(f"Error creating phone verification: {e}")
        return None

def verify_phone_code(phone_number, otp_code):
    """Verify OTP code for phone number"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get latest verification
        cursor.execute("""
            SELECT * FROM phone_verifications
            WHERE phone_number = %s AND otp_code = %s AND is_verified = FALSE
            ORDER BY created_at DESC LIMIT 1
        """, (phone_number, otp_code))

        verification = cursor.fetchone()

        if not verification:
            cursor.close()
            conn.close()
            return False

        # Check if expired
        if datetime.now() > verification['expires_at']:
            cursor.close()
            conn.close()
            return False

        # Mark as verified
        cursor.execute("""
            UPDATE phone_verifications
            SET is_verified = TRUE
            WHERE id = %s
        """, (verification['id'],))

        conn.commit()
        cursor.close()
        conn.close()

        return True
    except Exception as e:
        logger.error(f"Error verifying phone code: {e}")
        return False

def increment_verification_attempts(phone_number):
    """Increment failed verification attempts"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE phone_verifications
            SET attempts = attempts + 1
            WHERE phone_number = %s AND is_verified = FALSE
        """, (phone_number,))

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error incrementing attempts: {e}")

# ==================== SESSION MANAGEMENT ====================

def create_web_session(user_id, session_token, ip_address=None, user_agent=None):
    """Create web session for authenticated user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        expires_at = datetime.now() + timedelta(days=30)  # 30 days session

        cursor.execute("""
            INSERT INTO web_sessions (user_id, session_token, expires_at, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, session_token, expires_at, ip_address, user_agent))

        conn.commit()
        cursor.close()
        conn.close()

        return True
    except Exception as e:
        logger.error(f"Error creating web session: {e}")
        return False

def get_session(session_token):
    """Get session by token"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT * FROM web_sessions
            WHERE session_token = %s AND expires_at > NOW()
        """, (session_token,))

        session = cursor.fetchone()

        if session:
            # Update last activity
            cursor.execute("""
                UPDATE web_sessions
                SET last_activity = NOW()
                WHERE id = %s
            """, (session['id'],))
            conn.commit()

        cursor.close()
        conn.close()

        return session
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        return None

def delete_session(session_token):
    """Delete session (logout)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM web_sessions WHERE session_token = %s", (session_token,))

        conn.commit()
        cursor.close()
        conn.close()

        return True
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return False

# ==================== USER FUNCTIONS ====================

def get_user(user_id):
    """Get user by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        return user
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

def get_user_by_phone(phone_number):
    """Get user by phone number"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE phone = %s", (phone_number,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        return user
    except Exception as e:
        logger.error(f"Error getting user by phone: {e}")
        return None

def update_user(user_id, **kwargs):
    """Update user information"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Build UPDATE query dynamically
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = %s")
            values.append(value)

        values.append(user_id)

        query = f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s"
        cursor.execute(query, values)

        conn.commit()
        cursor.close()
        conn.close()

        return True
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return False

def set_user_password(user_id, password):
    """Set or update user password"""
    try:
        password_hash = generate_password_hash(password)
        return update_user(user_id, password_hash=password_hash)
    except Exception as e:
        logger.error(f"Error setting user password: {e}")
        return False

def check_user_password(user_id, password):
    """Check if password matches user's password"""
    try:
        user = get_user(user_id)
        if not user or not user.get('password_hash'):
            return False
        return check_password_hash(user['password_hash'], password)
    except Exception as e:
        logger.error(f"Error checking user password: {e}")
        return False

def check_password_by_phone(phone_number, password):
    """Check password for user by phone number"""
    try:
        user = get_user_by_phone(phone_number)
        if not user or not user.get('password_hash'):
            return False
        return check_password_hash(user['password_hash'], password)
    except Exception as e:
        logger.error(f"Error checking password by phone: {e}")
        return False

def user_has_password(user_id):
    """Check if user has a password set"""
    try:
        user = get_user(user_id)
        return user and user.get('password_hash') is not None
    except Exception as e:
        logger.error(f"Error checking if user has password: {e}")
        return False

def user_has_password_by_phone(phone_number):
    """Check if user has a password set by phone number"""
    try:
        user = get_user_by_phone(phone_number)
        return user and user.get('password_hash') is not None
    except Exception as e:
        logger.error(f"Error checking if user has password by phone: {e}")
        return False

# ==================== TRANSACTION FUNCTIONS ====================

def add_transaction(user_id, transaction_type, amount, currency='UZS', category=None, description=None):
    """Add new transaction"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO transactions (user_id, transaction_type, amount, currency, category, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, transaction_type, amount, currency, category, description))

        transaction_id = cursor.lastrowid

        conn.commit()
        cursor.close()
        conn.close()

        return transaction_id
    except Exception as e:
        logger.error(f"Error adding transaction: {e}")
        return None

def get_transactions(user_id, limit=50, offset=0, transaction_type=None):
    """Get user transactions"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if transaction_type:
            cursor.execute("""
                SELECT * FROM transactions
                WHERE user_id = %s AND transaction_type = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (user_id, transaction_type, limit, offset))
        else:
            cursor.execute("""
                SELECT * FROM transactions
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (user_id, limit, offset))

        transactions = cursor.fetchall()

        cursor.close()
        conn.close()

        return transactions
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        return []

def get_balance(user_id):
    """Calculate user's total balance"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END) as total_income,
                SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END) as total_expense
            FROM transactions
            WHERE user_id = %s
        """, (user_id,))

        result = cursor.fetchone()

        cursor.close()
        conn.close()

        total_income = float(result['total_income']) if result['total_income'] else 0
        total_expense = float(result['total_expense']) if result['total_expense'] else 0

        return total_income - total_expense
    except Exception as e:
        logger.error(f"Error calculating balance: {e}")
        return 0

def get_statistics(user_id, period='month'):
    """Get comprehensive user statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Determine date range based on period
        days_back = 30
        if period == 'week':
            days_back = 7
            date_filter = "DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
        elif period == 'month':
            days_back = 30
            date_filter = "DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
        elif period == 'year':
            days_back = 365
            date_filter = "DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 365 DAY)"
        else:
            days_back = 30
            date_filter = "1=1"

        # Get income and expense totals
        cursor.execute(f"""
            SELECT
                SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END) as total_income,
                SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END) as total_expense,
                COUNT(*) as total_transactions,
                COUNT(CASE WHEN transaction_type = 'income' THEN 1 END) as income_count,
                COUNT(CASE WHEN transaction_type = 'expense' THEN 1 END) as expense_count,
                AVG(CASE WHEN transaction_type = 'income' THEN amount END) as avg_income,
                AVG(CASE WHEN transaction_type = 'expense' THEN amount END) as avg_expense,
                MAX(CASE WHEN transaction_type = 'income' THEN amount END) as max_income,
                MAX(CASE WHEN transaction_type = 'expense' THEN amount END) as max_expense
            FROM transactions
            WHERE user_id = %s AND {date_filter}
        """, (user_id,))

        stats = cursor.fetchone()

        # Get category breakdown for expenses
        cursor.execute(f"""
            SELECT 
                category,
                SUM(amount) as total_amount,
                COUNT(*) as count
            FROM transactions
            WHERE user_id = %s AND transaction_type = 'expense' AND {date_filter} AND category IS NOT NULL AND category != ''
            GROUP BY category
            ORDER BY total_amount DESC
            LIMIT 10
        """, (user_id,))
        category_breakdown = cursor.fetchall()

        # Get daily distribution (last 7/30/365 days based on period)
        if period == 'week':
            group_format = "%Y-%m-%d"
        elif period == 'month':
            group_format = "%Y-%m-%d"
        else:  # year
            group_format = "%Y-%m"

        cursor.execute(f"""
            SELECT 
                DATE_FORMAT(created_at, %s) as date,
                SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END) as daily_income,
                SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END) as daily_expense,
                COUNT(*) as daily_transactions
            FROM transactions
            WHERE user_id = %s AND {date_filter}
            GROUP BY DATE_FORMAT(created_at, %s)
            ORDER BY date ASC
        """, (group_format, user_id, group_format))
        daily_distribution = cursor.fetchall()

        # Get top transactions
        cursor.execute(f"""
            SELECT * FROM transactions
            WHERE user_id = %s AND {date_filter}
            ORDER BY amount DESC
            LIMIT 5
        """, (user_id,))
        top_transactions = cursor.fetchall()

        cursor.close()
        conn.close()

        # Calculate additional metrics
        total_income = float(stats['total_income']) if stats['total_income'] else 0
        total_expense = float(stats['total_expense']) if stats['total_expense'] else 0
        net_balance = total_income - total_expense
        expense_ratio = (total_expense / total_income * 100) if total_income > 0 else 0
        avg_daily_expense = total_expense / days_back if days_back > 0 else 0

        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'net_balance': net_balance,
            'total_transactions': stats['total_transactions'] or 0,
            'income_count': stats['income_count'] or 0,
            'expense_count': stats['expense_count'] or 0,
            'avg_income': float(stats['avg_income']) if stats['avg_income'] else 0,
            'avg_expense': float(stats['avg_expense']) if stats['avg_expense'] else 0,
            'max_income': float(stats['max_income']) if stats['max_income'] else 0,
            'max_expense': float(stats['max_expense']) if stats['max_expense'] else 0,
            'expense_ratio': round(expense_ratio, 2),
            'avg_daily_expense': round(avg_daily_expense, 2),
            'category_breakdown': category_breakdown,
            'daily_distribution': daily_distribution,
            'top_transactions': top_transactions,
            'period_days': days_back
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {
            'total_income': 0, 'total_expense': 0, 'net_balance': 0,
            'total_transactions': 0, 'income_count': 0, 'expense_count': 0,
            'avg_income': 0, 'avg_expense': 0, 'max_income': 0, 'max_expense': 0,
            'expense_ratio': 0, 'avg_daily_expense': 0,
            'category_breakdown': [], 'daily_distribution': [], 'top_transactions': [],
            'period_days': 30
        }

# ==================== DEBT FUNCTIONS ====================

def add_debt(user_id, debt_type, amount, person_name, currency='UZS', description=None, due_date=None):
    """Add new debt"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO debts (user_id, debt_type, amount, person_name, currency, description, due_date, paid_amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
        """, (user_id, debt_type, amount, person_name, currency, description, due_date))

        debt_id = cursor.lastrowid

        conn.commit()
        cursor.close()
        conn.close()

        return debt_id
    except Exception as e:
        logger.error(f"Error adding debt: {e}")
        return None

def get_debts(user_id, debt_type=None):
    """Get user debts"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if debt_type:
            cursor.execute("""
                SELECT * FROM debts
                WHERE user_id = %s AND debt_type = %s AND status = 'active'
                ORDER BY created_at DESC
            """, (user_id, debt_type))
        else:
            cursor.execute("""
                SELECT * FROM debts
                WHERE user_id = %s AND status = 'active'
                ORDER BY created_at DESC
            """, (user_id,))

        debts = cursor.fetchall()

        cursor.close()
        conn.close()

        return debts
    except Exception as e:
        logger.error(f"Error getting debts: {e}")
        return []

# ==================== REMINDER FUNCTIONS ====================

def add_reminder(user_id, title, amount, currency='UZS', reminder_date=None, repeat_interval=None):
    """Add new reminder"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO reminders (user_id, title, amount, currency, reminder_date, repeat_interval)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, title, amount, currency, reminder_date, repeat_interval))

        reminder_id = cursor.lastrowid

        conn.commit()
        cursor.close()
        conn.close()

        return reminder_id
    except Exception as e:
        logger.error(f"Error adding reminder: {e}")
        return None

def get_reminders(user_id):
    """Get user reminders"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT * FROM reminders
            WHERE user_id = %s
            ORDER BY reminder_date ASC
        """, (user_id,))

        reminders = cursor.fetchall()

        cursor.close()
        conn.close()

        return reminders
    except Exception as e:
        logger.error(f"Error getting reminders: {e}")
        return []

# ==================== CONTACT FUNCTIONS ====================

def add_contact(user_id, name, phone=None, contact_type='person', notes=None):
    """Add new contact"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO contacts (user_id, name, phone, contact_type, notes)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, name, phone, contact_type, notes))

        contact_id = cursor.lastrowid

        conn.commit()
        cursor.close()
        conn.close()

        return contact_id
    except Exception as e:
        logger.error(f"Error adding contact: {e}")
        return None

def get_contacts(user_id, contact_type=None):
    """Get user contacts"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if contact_type:
            cursor.execute("""
                SELECT * FROM contacts
                WHERE user_id = %s AND contact_type = %s
                ORDER BY name ASC
            """, (user_id, contact_type))
        else:
            cursor.execute("""
                SELECT * FROM contacts
                WHERE user_id = %s
                ORDER BY name ASC
            """, (user_id,))

        contacts = cursor.fetchall()

        cursor.close()
        conn.close()

        return contacts
    except Exception as e:
        logger.error(f"Error getting contacts: {e}")
        return []

# ==================== LIMIT FUNCTIONS ====================

def set_monthly_limit(user_id, limit_amount):
    """Set monthly spending limit"""
    try:
        return update_user(user_id, monthly_limit=limit_amount)
    except Exception as e:
        logger.error(f"Error setting monthly limit: {e}")
        return False

def get_monthly_limit(user_id):
    """Get monthly spending limit"""
    try:
        user = get_user(user_id)
        return float(user['monthly_limit']) if user and user['monthly_limit'] else None
    except Exception as e:
        logger.error(f"Error getting monthly limit: {e}")
        return None

# ==================== WAREHOUSE FUNCTIONS ====================

def add_warehouse_product(user_id, name, quantity, unit='dona', price=0, category=None):
    """Add new warehouse product"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO warehouse_products (user_id, name, quantity, unit, price, category)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, name, quantity, unit, price, category))

        product_id = cursor.lastrowid

        conn.commit()
        cursor.close()
        conn.close()

        return product_id
    except Exception as e:
        logger.error(f"Error adding warehouse product: {e}")
        return None

def get_warehouse_products(user_id):
    """Get warehouse products"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT * FROM warehouse_products
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))

        products = cursor.fetchall()

        cursor.close()
        conn.close()

        return products
    except Exception as e:
        logger.error(f"Error getting warehouse products: {e}")
        return []

def update_warehouse_product(user_id, product_id, **kwargs):
    """Update warehouse product"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = %s")
            values.append(value)

        values.extend([user_id, product_id])

        query = f"UPDATE warehouse_products SET {', '.join(fields)} WHERE user_id = %s AND id = %s"
        cursor.execute(query, values)

        conn.commit()
        cursor.close()
        conn.close()

        return True
    except Exception as e:
        logger.error(f"Error updating warehouse product: {e}")
        return False

# ==================== EMPLOYEE FUNCTIONS ====================

def add_employee(user_id, name, position=None, phone=None, salary=0):
    """Add new employee"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO employees (user_id, name, position, phone, salary, status)
            VALUES (%s, %s, %s, %s, %s, 'active')
        """, (user_id, name, position, phone, salary))

        employee_id = cursor.lastrowid

        conn.commit()
        cursor.close()
        conn.close()

        return employee_id
    except Exception as e:
        logger.error(f"Error adding employee: {e}")
        return None

def get_employees(user_id):
    """Get employees"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT * FROM employees
            WHERE user_id = %s AND status = 'active'
            ORDER BY created_at DESC
        """, (user_id,))

        employees = cursor.fetchall()

        cursor.close()
        conn.close()

        return employees
    except Exception as e:
        logger.error(f"Error getting employees: {e}")
        return []

def update_employee(user_id, employee_id, **kwargs):
    """Update employee"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = %s")
            values.append(value)

        values.extend([user_id, employee_id])

        query = f"UPDATE employees SET {', '.join(fields)} WHERE user_id = %s AND id = %s"
        cursor.execute(query, values)

        conn.commit()
        cursor.close()
        conn.close()

        return True
    except Exception as e:
        logger.error(f"Error updating employee: {e}")
        return False

# ==================== TASK FUNCTIONS ====================

def add_task(user_id, title, description=None, due_date=None, priority='medium', assigned_to=None):
    """Add new task"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO tasks (user_id, title, description, due_date, priority, assigned_to, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
        """, (user_id, title, description, due_date, priority, assigned_to))

        task_id = cursor.lastrowid

        conn.commit()
        cursor.close()
        conn.close()

        return task_id
    except Exception as e:
        logger.error(f"Error adding task: {e}")
        return None

def get_tasks(user_id, status=None):
    """Get tasks"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if status:
            cursor.execute("""
                SELECT * FROM tasks
                WHERE user_id = %s AND status = %s
                ORDER BY created_at DESC
            """, (user_id, status))
        else:
            cursor.execute("""
                SELECT * FROM tasks
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))

        tasks = cursor.fetchall()

        cursor.close()
        conn.close()

        return tasks
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return []

def update_task(user_id, task_id, **kwargs):
    """Update task"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = %s")
            values.append(value)

        values.extend([user_id, task_id])

        query = f"UPDATE tasks SET {', '.join(fields)} WHERE user_id = %s AND id = %s"
        cursor.execute(query, values)

        conn.commit()
        cursor.close()
        conn.close()

        return True
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        return False

# ==================== REPORTING FUNCTIONS ====================

def get_report_summary(user_id, period='month'):
    """Get comprehensive report summary"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Determine date range
        if period == 'week':
            date_filter = "DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
        elif period == 'month':
            date_filter = "DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
        elif period == 'year':
            date_filter = "DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 365 DAY)"
        else:
            date_filter = "1=1"

        # Get financial summary
        cursor.execute(f"""
            SELECT
                SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END) as total_income,
                SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END) as total_expense,
                COUNT(*) as transaction_count
            FROM transactions
            WHERE user_id = %s AND {date_filter}
        """, (user_id,))

        financial = cursor.fetchone()

        # Get top categories
        cursor.execute(f"""
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE user_id = %s AND transaction_type = 'expense' AND {date_filter}
            GROUP BY category
            ORDER BY total DESC
            LIMIT 5
        """, (user_id,))

        top_categories = cursor.fetchall()

        # Get daily trend
        cursor.execute(f"""
            SELECT DATE(created_at) as date,
                   SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END) as income,
                   SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END) as expense
            FROM transactions
            WHERE user_id = %s AND {date_filter}
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 30
        """, (user_id,))

        daily_trend = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            'financial': financial,
            'top_categories': top_categories,
            'daily_trend': daily_trend,
            'period': period
        }
    except Exception as e:
        logger.error(f"Error getting report summary: {e}")
        return {}

def get_analytics(user_id, period='month'):
    """Get detailed analytics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if period == 'week':
            date_filter = "DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
        elif period == 'month':
            date_filter = "DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
        elif period == 'year':
            date_filter = "DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 365 DAY)"
        else:
            date_filter = "1=1"

        # Get transaction statistics
        cursor.execute(f"""
            SELECT
                COUNT(*) as total_transactions,
                AVG(amount) as avg_transaction,
                MAX(amount) as max_transaction,
                MIN(amount) as min_transaction
            FROM transactions
            WHERE user_id = %s AND {date_filter}
        """, (user_id,))

        stats = cursor.fetchone()

        # Get category breakdown
        cursor.execute(f"""
            SELECT category, transaction_type,
                   COUNT(*) as count,
                   SUM(amount) as total
            FROM transactions
            WHERE user_id = %s AND {date_filter}
            GROUP BY category, transaction_type
        """, (user_id,))

        categories = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            'statistics': stats,
            'categories': categories
        }
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return {}

def get_category_breakdown(user_id, period='month'):
    """Get spending by category"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if period == 'week':
            date_filter = "DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
        elif period == 'month':
            date_filter = "DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
        elif period == 'year':
            date_filter = "DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 365 DAY)"
        else:
            date_filter = "1=1"

        cursor.execute(f"""
            SELECT category,
                   SUM(amount) as total,
                   COUNT(*) as count,
                   AVG(amount) as average
            FROM transactions
            WHERE user_id = %s AND transaction_type = 'expense' AND {date_filter}
            GROUP BY category
            ORDER BY total DESC
        """, (user_id,))

        categories = cursor.fetchall()

        cursor.close()
        conn.close()

        return categories
    except Exception as e:
        logger.error(f"Error getting category breakdown: {e}")
        return []

# Initialize database on module import
init_database()
