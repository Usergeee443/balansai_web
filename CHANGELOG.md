# Changelog - Balans AI Web Business Version

## [1.1.0] - 2026-01-06

### Major Features Added

#### 1. Business Tariff Verification
- ✅ Added Business subscription requirement for web access
- ✅ Non-business users are automatically redirected to https://balansai-app.onrender.com
- ✅ New `business_required` decorator for API endpoints
- ✅ Subscription check on main page load

#### 2. Warehouse Management System
- ✅ Product inventory tracking
- ✅ Add/update products with quantity, price, and category
- ✅ API endpoints:
  - `GET /api/warehouse/products` - Get all products
  - `POST /api/warehouse/products` - Add new product
  - `PUT /api/warehouse/products/<id>` - Update product

#### 3. Employee Management
- ✅ Employee records with position, phone, and salary
- ✅ Employee status tracking (active/inactive)
- ✅ API endpoints:
  - `GET /api/employees` - Get all employees
  - `POST /api/employees` - Add new employee
  - `PUT /api/employees/<id>` - Update employee

#### 4. Task Management System
- ✅ Task creation with title, description, and due dates
- ✅ Priority levels: low, medium, high
- ✅ Task status: pending, in_progress, completed, cancelled
- ✅ Task assignment to employees
- ✅ API endpoints:
  - `GET /api/tasks` - Get all tasks (optional status filter)
  - `POST /api/tasks` - Create new task
  - `PUT /api/tasks/<id>` - Update task

#### 5. Enhanced Reports & Analytics
- ✅ Comprehensive financial summary reports
- ✅ Top spending categories
- ✅ Daily transaction trends (last 30 days)
- ✅ Detailed analytics with averages, max, min
- ✅ Category breakdown with counts and averages
- ✅ API endpoints:
  - `GET /api/reports/summary?period=month` - Comprehensive summary
  - `GET /api/reports/analytics?period=month` - Detailed analytics
  - `GET /api/reports/categories?period=month` - Category breakdown

### Database Changes
- ✅ New table: `warehouse_products`
- ✅ New table: `employees`
- ✅ New table: `tasks`

### Authentication Improvements
- ✅ Fixed authentication flow
- ✅ Better session management
- ✅ Proper error handling for 401 responses

## Authentication Issue Resolution

### Problem
All API requests were returning 401 (Unauthorized) errors because users weren't logged in.

### Solution
1. Users must first visit `/login` and authenticate via phone + OTP
2. OTP is sent to their Telegram account
3. After successful authentication, session is created
4. Session lasts 30 days with activity tracking
5. Business subscription is checked before granting access

## How to Use

### For Users:
1. Navigate to the web application
2. Login with your phone number (registered in Telegram bot)
3. Enter OTP code sent to your Telegram
4. ⚠️ **Important**: Only Business plan subscribers can access the web version
5. Free/Plus users will be redirected to the mobile app

### For Developers:
All new tables will be created automatically on first run. The `init_database()` function creates:
- warehouse_products
- employees
- tasks

### API Period Parameters:
- `week` - Last 7 days
- `month` - Last 30 days (default)
- `year` - Last 365 days

## Breaking Changes
- Web access now requires Business subscription
- Non-business users are redirected to mobile app

## Next Steps (Future Enhancements)
- Add UI components for warehouse, employees, and tasks
- Create visual charts for new analytics data
- Add export functionality for reports
- Implement real-time notifications for tasks
- Add calendar view for task due dates
