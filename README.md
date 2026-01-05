# Balans AI - Web Version

Moliyaviy boshqaruv tizimining desktop web versiyasi. Telefon raqam va Telegram bot orqali autentifikatsiya qilish imkoniyati.

## Xususiyatlar

### 🔐 Autentifikatsiya
- **Telefon raqam orqali kirish**: Foydalanuvchi telefon raqamini kiritadi
- **Telegram bot orqali tasdiqlash**: OTP kod Telegram botga yuboriladi
- **Session boshqaruvi**: 30 kunlik sessiya vaqti
- **Xavfsiz logout**: Sessiyani to'liq tozalash

### 💰 Asosiy funksiyalar
- **Balans boshqaruvi**: Real-time balans ko'rsatkichi
- **Tranzaksiyalar**: Daromad va xarajatlarni qo'shish va ko'rish
- **Ko'p valyuta**: UZS, USD, EUR, RUB
- **Statistika**: Grafik va tahlillar
- **Qarzlar**: Qarzlarni boshqarish
- **Eslatmalar**: To'lov eslatmalari
- **Kontaktlar**: Shaxslar va kategoriyalar
- **Limit**: Oylik xarajat limiti

### 🎨 Dizayn
- **Desktop-optimized**: Katta ekranlar uchun moslashtirilgan
- **Responsive**: Barcha ekran o'lchamlari uchun
- **Mini app dizayni**: Telegram mini app bilan bir xil dizayn
- **Modern UI**: Gradient, shadow, smooth animations

## Texnologiyalar

### Backend
- **Python 3.10+**: Dasturlash tili
- **Flask 3.0.0**: Web framework
- **MySQL**: Database
- **python-telegram-bot**: Telegram integratsiyasi
- **DBUtils**: Connection pooling

### Frontend
- **HTML5, CSS3, JavaScript**: Asosiy texnologiyalar
- **Chart.js**: Grafik kutubxonasi
- **Vanilla JS**: Framework ishlatilmagan (yengil va tez)

## O'rnatish

### 1. Repository'ni klonlash
```bash
git clone https://github.com/Usergeee443/balansai_web.git
cd balansai_web
```

### 2. Virtual environment yaratish
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate  # Windows
```

### 3. Dependencies o'rnatish
```bash
pip install -r requirements.txt
```

### 4. Environment o'rnatish
`.env` faylini yaratish va quyidagi ma'lumotlarni kiritish:

```env
# Database Configuration
DB_HOST=146.103.126.207
DB_USER=phpmyadmin
DB_PASSWORD=your_password
DB_NAME=BalansAiBot
DB_PORT=3306

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_BOT_USERNAME=BalansAiBot

# Flask Configuration
SECRET_KEY=your_secret_key_here
DEBUG=True

# OTP Configuration
OTP_EXPIRY_MINUTES=5
OTP_LENGTH=6
```

### 5. Database yaratish
Database avtomatik yaratiladi. Agar kerak bo'lsa, qo'lda yaratish:

```sql
CREATE DATABASE IF NOT EXISTS BalansAiBot;
```

### 6. Ilovani ishga tushirish
```bash
python app.py
```

Server `http://localhost:5000` da ishga tushadi.

## Foydalanish

### Kirish
1. `http://localhost:5000/login` ga o'ting
2. Telefon raqamingizni kiriting (bazada mavjud bo'lishi kerak)
3. Telegram botdan kelgan 6 raqamli kodni kiriting
4. Asosiy sahifaga yo'naltirilasiz

### Tranzaksiya qo'shish
1. Asosiy sahifada "Tranzaksiya qo'shish" tugmasini bosing
2. Turi (daromad/xarajat), summa, valyuta, kategoriya va izohni kiriting
3. "Saqlash" tugmasini bosing

### Statistikani ko'rish
1. Pastki navigatsiyada "Statistika" tugmasini bosing
2. Davr (hafta/oy/yil) tanlang
3. Grafik va jadvalni ko'ring

## API Endpoints

### Autentifikatsiya
- `POST /api/auth/request-code` - OTP kod so'rash
- `POST /api/auth/verify-code` - OTP kodni tasdiqlash
- `POST /api/auth/logout` - Tizimdan chiqish
- `GET /api/auth/me` - Joriy foydalanuvchi

### Tranzaksiyalar
- `GET /api/transactions` - Tranzaksiyalar ro'yxati
- `POST /api/transactions` - Yangi tranzaksiya
- `GET /api/balance` - Balans
- `GET /api/statistics` - Statistika

### Qarzlar
- `GET /api/debts` - Qarzlar ro'yxati
- `POST /api/debts` - Yangi qarz

### Eslatmalar
- `GET /api/reminders` - Eslatmalar ro'yxati
- `POST /api/reminders` - Yangi eslatma

### Kontaktlar
- `GET /api/contacts` - Kontaktlar ro'yxati
- `POST /api/contacts` - Yangi kontakt

### Limit
- `GET /api/limit` - Oylik limit
- `POST /api/limit` - Limit o'rnatish

## Xavfsizlik

- **HMAC-SHA256**: Telegram WebApp validatsiya
- **Session tokens**: Xavfsiz sessiya boshqaruvi
- **OTP expiry**: Kod 5 daqiqada amal qiladi
- **SQL injection protection**: Parametrlangan querylar
- **XSS protection**: Input sanitization

## Deployment

### Render.com
1. `render.yaml` faylini tekshiring
2. Render.com'da yangi web service yarating
3. Environment variables'larni o'rnating
4. Deploy qiling

### Docker
```bash
docker build -t balansai-web .
docker run -p 5000:5000 balansai-web
```

## Muammolarni hal qilish

### Database ulanmayapti
- `.env` faylidagi database ma'lumotlarini tekshiring
- MySQL serverning ishlab turganini tekshiring
- Firewall sozlamalarini tekshiring

### Telegram bot javob bermayapti
- Bot tokenni tekshiring
- Bot ishga tushganini tekshiring
- User Telegram ID to'g'ri ekanligini tekshiring

### OTP kod kelmayapti
- User telefon raqami bazada mavjudligini tekshiring
- User Telegram ID to'g'ri ekanligini tekshiring
- Bot user bilan chat boshlagan bo'lishi kerak

## Development

### Debug mode
```bash
export DEBUG=True
python app.py
```

### Database migration
Database schema o'zgarsa, `database.py` faylidagi `init_database()` funksiyasini yangilang.

## Litsenziya

MIT License

## Muallif

Balans AI Development Team

## Aloqa

- GitHub: [Usergeee443/balansai_web](https://github.com/Usergeee443/balansai_web)
- Telegram Bot: [@BalansAiBot](https://t.me/BalansAiBot)

---

**Eslatma**: Bu loyiha [balansai_app](https://github.com/Usergeee443/balansai_app) Telegram mini app asosida yaratilgan web versiya.
