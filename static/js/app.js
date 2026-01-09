// App State
const state = {
    currentPage: 'pageHome',
    user: null,
    transactions: [],
    statistics: null,
    currentFilter: 'all',
    currentPeriod: 'month',
    charts: {}
};

// API Helper
const api = {
    async fetch(endpoint, options = {}) {
        try {
            const response = await fetch(endpoint, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (response.status === 401) {
                window.location.href = '/login';
                return null;
            }

            const data = await response.json();
            return { ok: response.ok, data, status: response.status };
        } catch (error) {
            console.error('API Error:', error);
            showNotification('Tarmoq xatosi yuz berdi', 'error');
            return { ok: false, error };
        }
    },

    async get(endpoint) {
        return this.fetch(endpoint);
    },

    async post(endpoint, body) {
        return this.fetch(endpoint, {
            method: 'POST',
            body: JSON.stringify(body)
        });
    }
};

// Utility Functions
function formatNumber(num) {
    return new Intl.NumberFormat('uz-UZ').format(num);
}

function formatCurrency(amount, currency = 'UZS') {
    return `${formatNumber(amount)} ${currency}`;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) {
        return 'Bugun';
    } else if (date.toDateString() === yesterday.toDateString()) {
        return 'Kecha';
    } else {
        return date.toLocaleDateString('uz-UZ', { day: 'numeric', month: 'short' });
    }
}

function showNotification(message, type = 'info') {
    // Simple notification (can be enhanced with a library)
    alert(message);
}

// Navigation
function setupNavigation() {
    // Bottom navigation (mobile)
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const pageId = item.dataset.page;
            navigateToPage(pageId);
        });
    });

    // Sidebar navigation (desktop)
    const sidebarItems = document.querySelectorAll('.sidebar-menu-item');
    sidebarItems.forEach(item => {
        item.addEventListener('click', () => {
            const pageId = item.dataset.page;
            navigateToPage(pageId);
        });
    });

    // View all transactions link
    document.getElementById('viewAllTransactions')?.addEventListener('click', (e) => {
        e.preventDefault();
        navigateToPage('pageTransactions');
    });
}

function navigateToPage(pageId) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });

    // Show selected page
    document.getElementById(pageId)?.classList.add('active');

    // Update bottom nav items (mobile)
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === pageId) {
            item.classList.add('active');
        }
    });

    // Update sidebar menu items (desktop)
    document.querySelectorAll('.sidebar-menu-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === pageId) {
            item.classList.add('active');
        }
    });

    // Load page data
    state.currentPage = pageId;
    loadPageData(pageId);
}

function loadPageData(pageId) {
    switch (pageId) {
        case 'pageHome':
            loadDashboard();
            break;
        case 'pageTransactions':
            loadTransactions();
            break;
        case 'pageStatistics':
            loadStatistics();
            break;
        case 'pageProfile':
            loadProfile();
            break;
    }
}

// Dashboard
async function loadDashboard() {
    // Show skeleton loaders
    showDashboardSkeleton();
    
    try {
        // Load user info
        const userResponse = await api.get('/api/auth/me');
        if (userResponse.ok) {
            state.user = userResponse.data;
            updateUserInfo();
        }

        // Load balance
        const balanceResponse = await api.get('/api/balance');
        if (balanceResponse.ok) {
            updateBalance(balanceResponse.data.balance);
        }

        // Load statistics
        const statsResponse = await api.get('/api/statistics?period=month');
        if (statsResponse.ok) {
            updateQuickStats(statsResponse.data);
        }

        // Load recent transactions
        const transactionsResponse = await api.get('/api/transactions?limit=5');
        if (transactionsResponse.ok) {
            renderRecentTransactions(transactionsResponse.data);
        }
        
        // Hide skeleton loaders
        hideDashboardSkeleton();
    } catch (error) {
        console.error('Error loading dashboard:', error);
        hideDashboardSkeleton();
    }
}

function showDashboardSkeleton() {
    // Skeleton loaders are shown by default in HTML
    document.getElementById('skeletonBalance').style.display = 'block';
    document.getElementById('balanceContent').style.display = 'none';
    document.getElementById('skeletonTransactions').style.display = 'block';
}

function hideDashboardSkeleton() {
    document.getElementById('skeletonBalance').style.display = 'none';
    document.getElementById('balanceContent').style.display = 'block';
    document.getElementById('skeletonTransactions').style.display = 'none';
    
    // Show stat values
    const incomeAmount = document.getElementById('incomeAmount');
    const expenseAmount = document.getElementById('expenseAmount');
    if (incomeAmount) {
        incomeAmount.style.display = 'block';
        incomeAmount.previousElementSibling.style.display = 'none';
    }
    if (expenseAmount) {
        expenseAmount.style.display = 'block';
        expenseAmount.previousElementSibling.style.display = 'none';
    }
}

function updateUserInfo() {
    if (!state.user) return;

    const userName = state.user.name || 'User';
    const userPhone = state.user.phone || '+998';
    const initial = userName.charAt(0).toUpperCase();

    // Update mobile header
    document.getElementById('userName').textContent = userName;
    document.getElementById('userInitial').textContent = initial;

    // Update desktop sidebar
    document.getElementById('sidebarUserName').textContent = userName;
    document.getElementById('sidebarUserInitial').textContent = initial;
    document.getElementById('sidebarUserPhone').textContent = userPhone;
}

function updateBalance(balance) {
    const balanceElement = document.getElementById('totalBalance');
    if (balanceElement) {
        balanceElement.textContent = formatNumber(balance);
    }

    // Update gauge (simple version)
    const maxBalance = Math.max(balance, 10000000); // 10M UZS as reference
    const percentage = (balance / maxBalance) * 100;
    // Gauge animation can be added here
}

function updateQuickStats(stats) {
    document.getElementById('incomeAmount').textContent = formatCurrency(stats.total_income);
    document.getElementById('expenseAmount').textContent = formatCurrency(stats.total_expense);
}

function renderRecentTransactions(transactions) {
    const container = document.getElementById('recentTransactions');
    if (!container) return;

    // Hide skeleton
    const skeleton = document.getElementById('skeletonTransactions');
    if (skeleton) skeleton.style.display = 'none';

    if (transactions.length === 0) {
        container.innerHTML = '<div class="empty-state">Tranzaksiyalar yo\'q</div>';
        return;
    }

    const transactionsHTML = transactions.map(transaction => `
        <div class="transaction-item">
            <div class="transaction-icon ${transaction.transaction_type}">
                <i class="fas ${transaction.transaction_type === 'income' ? 'fa-arrow-up' : 'fa-arrow-down'}"></i>
            </div>
            <div class="transaction-info">
                <div class="transaction-category">${transaction.category || 'Kategoriyasiz'}</div>
                <div class="transaction-description">${transaction.description || formatDate(transaction.created_at)}</div>
            </div>
            <div class="transaction-amount">
                <div class="amount-value ${transaction.transaction_type}">
                    ${transaction.transaction_type === 'income' ? '+' : '-'}${formatCurrency(transaction.amount, transaction.currency)}
                </div>
                <div class="transaction-date">${formatDate(transaction.created_at)}</div>
            </div>
        </div>
    `).join('');
    
    // Append to container instead of replacing all content
    container.innerHTML = transactionsHTML;
}

// Transactions
async function loadTransactions() {
    // Show skeleton loader
    showTransactionsSkeleton();
    
    try {
        const type = state.currentFilter === 'all' ? '' : `&type=${state.currentFilter}`;
        const response = await api.get(`/api/transactions?limit=50${type}`);

        if (response.ok) {
            state.transactions = response.data;
            hideTransactionsSkeleton();
            renderTransactions(response.data);
        } else {
            hideTransactionsSkeleton();
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
        hideTransactionsSkeleton();
    }
}

function showTransactionsSkeleton() {
    const skeleton = document.getElementById('skeletonTransactionsList');
    if (skeleton) {
        skeleton.style.display = 'block';
    }
}

function hideTransactionsSkeleton() {
    const skeleton = document.getElementById('skeletonTransactionsList');
    if (skeleton) {
        skeleton.style.display = 'none';
    }
}

function renderTransactions(transactions) {
    const container = document.getElementById('allTransactions');
    if (!container) return;

    // Hide skeleton first
    hideTransactionsSkeleton();

    if (transactions.length === 0) {
        // Remove skeleton if exists
        const skeleton = document.getElementById('skeletonTransactionsList');
        if (skeleton && skeleton.parentNode === container) {
            container.removeChild(skeleton);
        }
        container.innerHTML = '<div class="empty-state">Tranzaksiyalar yo\'q</div>';
        return;
    }

    const transactionsHTML = transactions.map(transaction => `
        <div class="transaction-item">
            <div class="transaction-icon ${transaction.transaction_type}">
                <i class="fas ${transaction.transaction_type === 'income' ? 'fa-arrow-up' : 'fa-arrow-down'}"></i>
            </div>
            <div class="transaction-info">
                <div class="transaction-category">${transaction.category || 'Kategoriyasiz'}</div>
                <div class="transaction-description">${transaction.description || ''}</div>
            </div>
            <div class="transaction-amount">
                <div class="amount-value ${transaction.transaction_type}">
                    ${transaction.transaction_type === 'income' ? '+' : '-'}${formatCurrency(transaction.amount, transaction.currency)}
                </div>
                <div class="transaction-date">${formatDate(transaction.created_at)}</div>
            </div>
        </div>
    `).join('');
    
    // Remove skeleton if it exists in container
    const skeleton = document.getElementById('skeletonTransactionsList');
    if (skeleton && skeleton.parentNode === container) {
        container.removeChild(skeleton);
    }
    
    // Add transactions HTML
    container.innerHTML = transactionsHTML;
}

function setupTransactionFilters() {
    const filterTabs = document.querySelectorAll('.filter-tab');
    filterTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            filterTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            state.currentFilter = tab.dataset.filter;
            loadTransactions();
        });
    });
}

// Statistics
async function loadStatistics() {
    // Show skeleton loaders
    showStatisticsSkeleton();
    
    try {
        const response = await api.get(`/api/statistics?period=${state.currentPeriod}`);

        if (response.ok) {
            state.statistics = response.data;
            hideStatisticsSkeleton();
            updateAllStatistics(response.data);
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
        hideStatisticsSkeleton();
    }
}

function showStatisticsSkeleton() {
    // Skeleton loaders are shown by default in HTML
    document.querySelectorAll('.skeleton-stat-card, .skeleton-summary-item, .skeleton-chart, .skeleton-list, .skeleton-metric-card').forEach(el => {
        el.style.display = 'block';
    });
    document.getElementById('incomeExpenseChart').style.display = 'none';
    document.getElementById('dailyDistributionChart').style.display = 'none';
    document.getElementById('categoryBreakdown').style.display = 'none';
    document.getElementById('topTransactionsList').style.display = 'none';
    document.getElementById('statsGrid').innerHTML = '';
    document.getElementById('metricsGrid').innerHTML = '';
}

function hideStatisticsSkeleton() {
    document.querySelectorAll('.skeleton-stat-card, .skeleton-summary-item, .skeleton-chart, .skeleton-list, .skeleton-metric-card').forEach(el => {
        el.style.display = 'none';
    });
}

function updateAllStatistics(stats) {
    updateStatsSummary(stats);
    updateStatsCards(stats);
    renderIncomeExpenseChart(stats);
    renderDailyDistributionChart(stats);
    renderCategoryBreakdown(stats);
    renderTopTransactions(stats);
    updateMetrics(stats);
}

function updateStatsSummary(stats) {
    const summaryContainer = document.querySelector('.stats-summary');
    summaryContainer.innerHTML = `
        <div class="summary-item">
            <span class="summary-label">Jami daromad:</span>
            <span class="summary-value income" id="statIncome">${formatCurrency(stats.total_income)}</span>
        </div>
        <div class="summary-item">
            <span class="summary-label">Jami xarajat:</span>
            <span class="summary-value expense" id="statExpense">${formatCurrency(stats.total_expense)}</span>
        </div>
        <div class="summary-item">
            <span class="summary-label">Sof foyda:</span>
            <span class="summary-value ${stats.net_balance >= 0 ? 'income' : 'expense'}" id="statDifference">${formatCurrency(Math.abs(stats.net_balance))}</span>
        </div>
    `;
}

function updateStatsCards(stats) {
    const statsGrid = document.getElementById('statsGrid');
    statsGrid.innerHTML = `
        <div class="stat-card-wrapper">
            <div class="stat-card-label">Jami tranzaksiyalar</div>
            <div class="stat-card-value">${stats.total_transactions || 0}</div>
        </div>
        <div class="stat-card-wrapper">
            <div class="stat-card-label">Daromadlar soni</div>
            <div class="stat-card-value income">${stats.income_count || 0}</div>
        </div>
        <div class="stat-card-wrapper">
            <div class="stat-card-label">Xarajatlar soni</div>
            <div class="stat-card-value expense">${stats.expense_count || 0}</div>
        </div>
        <div class="stat-card-wrapper">
            <div class="stat-card-label">Xarajat foizi</div>
            <div class="stat-card-value">${stats.expense_ratio || 0}%</div>
        </div>
    `;
}

function renderIncomeExpenseChart(stats) {
    const ctx = document.getElementById('incomeExpenseChart');
    if (!ctx) return;

    // Hide skeleton, show chart
    document.getElementById('skeletonIncomeExpenseChart').style.display = 'none';
    ctx.style.display = 'block';

    // Destroy existing chart
    if (state.charts.incomeExpense) {
        state.charts.incomeExpense.destroy();
    }

    // Create new chart
    state.charts.incomeExpense = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Daromad', 'Xarajat'],
            datasets: [{
                label: 'Summa',
                data: [stats.total_income, stats.total_expense],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(239, 68, 68, 0.8)'
                ],
                borderColor: [
                    'rgb(16, 185, 129)',
                    'rgb(239, 68, 68)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function renderDailyDistributionChart(stats) {
    const ctx = document.getElementById('dailyDistributionChart');
    if (!ctx) return;

    // Hide skeleton, show chart
    document.getElementById('skeletonDailyChart').style.display = 'none';
    ctx.style.display = 'block';

    const dailyData = stats.daily_distribution || [];
    const labels = dailyData.map(d => d.date);
    const incomeData = dailyData.map(d => parseFloat(d.daily_income) || 0);
    const expenseData = dailyData.map(d => parseFloat(d.daily_expense) || 0);

    // Destroy existing chart
    if (state.charts.dailyDistribution) {
        state.charts.dailyDistribution.destroy();
    }

    // Create new chart
    state.charts.dailyDistribution = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Daromad',
                data: incomeData,
                borderColor: 'rgb(16, 185, 129)',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                tension: 0.4
            }, {
                label: 'Xarajat',
                data: expenseData,
                borderColor: 'rgb(239, 68, 68)',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function renderCategoryBreakdown(stats) {
    const container = document.getElementById('categoryBreakdown');
    if (!container) return;

    // Hide skeleton, show breakdown
    document.getElementById('skeletonCategoryList').style.display = 'none';
    container.style.display = 'block';

    const categories = stats.category_breakdown || [];
    
    if (categories.length === 0) {
        container.innerHTML = '<div class="empty-state">Kategoriyalar bo\'yicha ma\'lumotlar yo\'q</div>';
        return;
    }

    const total = categories.reduce((sum, cat) => sum + parseFloat(cat.total_amount || 0), 0);

    container.innerHTML = categories.map(cat => {
        const percentage = total > 0 ? ((parseFloat(cat.total_amount || 0) / total) * 100).toFixed(1) : 0;
        return `
            <div class="category-item">
                <div class="category-info">
                    <span class="category-name">${cat.category || 'Kategoriyasiz'}</span>
                    <span class="category-count">${cat.count || 0} ta</span>
                </div>
                <div class="category-amount">${formatCurrency(parseFloat(cat.total_amount || 0))}</div>
                <div class="category-bar">
                    <div class="category-bar-fill" style="width: ${percentage}%"></div>
                </div>
                <div class="category-percentage">${percentage}%</div>
            </div>
        `;
    }).join('');
}

function renderTopTransactions(stats) {
    const container = document.getElementById('topTransactionsList');
    if (!container) return;

    // Hide skeleton, show list
    document.getElementById('skeletonTopTransactions').style.display = 'none';
    container.style.display = 'block';

    const transactions = stats.top_transactions || [];
    
    if (transactions.length === 0) {
        container.innerHTML = '<div class="empty-state">Tranzaksiyalar yo\'q</div>';
        return;
    }

    container.innerHTML = transactions.map(trans => `
        <div class="transaction-item">
            <div class="transaction-icon ${trans.transaction_type}">
                <i class="fas ${trans.transaction_type === 'income' ? 'fa-arrow-up' : 'fa-arrow-down'}"></i>
            </div>
            <div class="transaction-info">
                <div class="transaction-category">${trans.category || 'Kategoriyasiz'}</div>
                <div class="transaction-description">${trans.description || ''}</div>
            </div>
            <div class="transaction-amount">
                <div class="amount-value ${trans.transaction_type}">
                    ${trans.transaction_type === 'income' ? '+' : '-'}${formatCurrency(trans.amount, trans.currency)}
                </div>
            </div>
        </div>
    `).join('');
}

function updateMetrics(stats) {
    const metricsGrid = document.getElementById('metricsGrid');
    metricsGrid.innerHTML = `
        <div class="metric-card">
            <div class="metric-label">O'rtacha daromad</div>
            <div class="metric-value income">${formatCurrency(stats.avg_income || 0)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">O'rtacha xarajat</div>
            <div class="metric-value expense">${formatCurrency(stats.avg_expense || 0)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Eng katta daromad</div>
            <div class="metric-value income">${formatCurrency(stats.max_income || 0)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Eng katta xarajat</div>
            <div class="metric-value expense">${formatCurrency(stats.max_expense || 0)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Kunlik o'rtacha xarajat</div>
            <div class="metric-value">${formatCurrency(stats.avg_daily_expense || 0)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Davr (kun)</div>
            <div class="metric-value">${stats.period_days || 0}</div>
        </div>
    `;
}

function setupStatsPeriod() {
    const periodBtns = document.querySelectorAll('.period-btn');
    periodBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            periodBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.currentPeriod = btn.dataset.period;
            loadStatistics();
        });
    });
}

// Profile
async function loadProfile() {
    if (!state.user) {
        const response = await api.get('/api/auth/me');
        if (response.ok) {
            state.user = response.data;
        }
    }

    if (state.user) {
        const name = state.user.name || 'User';
        const phone = state.user.phone || '+998 XX XXX XX XX';
        const initial = name.charAt(0).toUpperCase();

        document.getElementById('profileName').textContent = name;
        document.getElementById('profilePhone').textContent = phone;
        document.getElementById('profileInitial').textContent = initial;
    }
}

// Modals
function setupModals() {
    // Add Transaction Modal
    const addTransactionBtn = document.getElementById('addTransactionBtn');
    const addTransactionModal = document.getElementById('addTransactionModal');
    const modalClose = addTransactionModal?.querySelector('.modal-close');
    const modalOverlay = addTransactionModal?.querySelector('.modal-overlay');

    addTransactionBtn?.addEventListener('click', () => {
        addTransactionModal?.classList.add('active');
    });

    modalClose?.addEventListener('click', () => {
        addTransactionModal?.classList.remove('active');
    });

    modalOverlay?.addEventListener('click', () => {
        addTransactionModal?.classList.remove('active');
    });

    // Transaction Form Submit
    const transactionForm = document.getElementById('transactionForm');
    transactionForm?.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(transactionForm);
        const data = {
            type: formData.get('type'),
            amount: parseFloat(formData.get('amount')),
            currency: formData.get('currency'),
            category: formData.get('category'),
            description: formData.get('description')
        };

        const response = await api.post('/api/transactions', data);

        if (response.ok) {
            showNotification('Tranzaksiya qo\'shildi', 'success');
            addTransactionModal?.classList.remove('active');
            transactionForm.reset();
            loadDashboard();
        } else {
            showNotification(response.data.error || 'Xatolik yuz berdi', 'error');
        }
    });
}

// Services
function setupServices() {
    const serviceCards = document.querySelectorAll('.service-card');
    serviceCards.forEach(card => {
        card.addEventListener('click', () => {
            const service = card.dataset.service;
            showNotification(`${service} xizmati hozircha ishlab chiqilmoqda`, 'info');
        });
    });
}

// Sidebar Toggle
function setupSidebarToggle() {
    const sidebarNav = document.getElementById('sidebarNav');
    const toggleBtn = document.getElementById('sidebarToggleBtn');
    
    if (!sidebarNav || !toggleBtn) return;

    // Load saved state from localStorage
    const savedState = localStorage.getItem('sidebarCollapsed');
    if (savedState === 'true') {
        sidebarNav.classList.add('collapsed');
    }

    toggleBtn.addEventListener('click', () => {
        sidebarNav.classList.toggle('collapsed');
        
        // Save state to localStorage
        const isCollapsed = sidebarNav.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', isCollapsed.toString());
    });
}

// Settings and Logout
function setupSettings() {
    const settingsBtn = document.getElementById('settingsBtn');
    const notificationBtn = document.getElementById('notificationBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const changePasswordBtn = document.getElementById('changePasswordBtn');
    const changePasswordModal = document.getElementById('changePasswordModal');
    const changePasswordForm = document.getElementById('changePasswordForm');
    const changePasswordError = document.getElementById('changePasswordError');

    settingsBtn?.addEventListener('click', () => {
        navigateToPage('pageProfile');
    });

    notificationBtn?.addEventListener('click', () => {
        showNotification('Bildirishnomalar yo\'q', 'info');
    });

    logoutBtn?.addEventListener('click', async () => {
        if (confirm('Tizimdan chiqmoqchimisiz?')) {
            const response = await api.post('/api/auth/logout');
            if (response.ok || response.status === 401) {
                window.location.href = '/login';
            }
        }
    });

    // Change Password Modal
    changePasswordBtn?.addEventListener('click', () => {
        changePasswordModal?.classList.add('active');
        changePasswordForm.reset();
        changePasswordError.style.display = 'none';
    });

    const changePasswordModalClose = changePasswordModal?.querySelector('.modal-close');
    const changePasswordModalOverlay = changePasswordModal?.querySelector('.modal-overlay');

    changePasswordModalClose?.addEventListener('click', () => {
        changePasswordModal?.classList.remove('active');
    });

    changePasswordModalOverlay?.addEventListener('click', () => {
        changePasswordModal?.classList.remove('active');
    });

    // Change Password Form
    changePasswordForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Hide previous errors
        if (changePasswordError) {
            changePasswordError.style.display = 'none';
            changePasswordError.textContent = '';
        }

        const oldPassword = document.getElementById('oldPassword')?.value;
        const newPassword = document.getElementById('newPassword')?.value;
        const confirmNewPassword = document.getElementById('confirmNewPassword')?.value;

        // Validation
        if (!oldPassword) {
            if (changePasswordError) {
                changePasswordError.textContent = 'Joriy parolni kiriting';
                changePasswordError.style.display = 'block';
            }
            return;
        }

        if (!newPassword) {
            if (changePasswordError) {
                changePasswordError.textContent = 'Yangi parolni kiriting';
                changePasswordError.style.display = 'block';
            }
            return;
        }

        if (newPassword !== confirmNewPassword) {
            if (changePasswordError) {
                changePasswordError.textContent = 'Yangi parollar mos kelmaydi';
                changePasswordError.style.display = 'block';
            }
            return;
        }

        if (newPassword.length < 6) {
            if (changePasswordError) {
                changePasswordError.textContent = 'Parol kamida 6 belgidan iborat bo\'lishi kerak';
                changePasswordError.style.display = 'block';
            }
            return;
        }

        const submitBtn = changePasswordForm.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'O\'zgartirilmoqda...';
        }

        try {
            const response = await api.post('/api/auth/change-password', {
                old_password: oldPassword,
                new_password: newPassword,
                confirm_password: confirmNewPassword
            });

            if (!response) {
                throw new Error('No response from server');
            }

            if (response.ok) {
                showNotification('Parol muvaffaqiyatli o\'zgartirildi', 'success');
                setTimeout(() => {
                    if (changePasswordModal) {
                        changePasswordModal.classList.remove('active');
                    }
                    if (changePasswordForm) {
                        changePasswordForm.reset();
                    }
                }, 500);
            } else {
                const errorMsg = (response.data && response.data.error) ? response.data.error : 'Xatolik yuz berdi';
                if (changePasswordError) {
                    changePasswordError.textContent = errorMsg;
                    changePasswordError.style.display = 'block';
                } else {
                    showNotification(errorMsg, 'error');
                }
            }
        } catch (error) {
            console.error('Change password error:', error);
            const errorMsg = 'Tarmoq xatosi. Qaytadan urinib ko\'ring';
            if (changePasswordError) {
                changePasswordError.textContent = errorMsg;
                changePasswordError.style.display = 'block';
            } else {
                showNotification(errorMsg, 'error');
            }
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Parolni o\'zgartirish';
            }
        }
    });
}

// Initialize App
function initApp() {
    console.log('Initializing Balans AI Web App...');

    // Setup all event listeners
    setupNavigation();
    setupSidebarToggle();
    setupTransactionFilters();
    setupStatsPeriod();
    setupModals();
    setupServices();
    setupSettings();

    // Load initial data
    loadDashboard();
}

// Start app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
