// API handling
const api = {
    async signup() {
        const response = await fetch('/signup');
        if (!response.ok) throw new Error('Signup failed');
        return response.json();
    },

    async getInfo(userId) {
        const response = await fetch('/info', {
            headers: { 'Authorization': `Bearer ${userId}` }
        });
        if (!response.ok) throw new Error('Failed to get info');
        return response.json();
    },

    async getTicker(userId, symbol) {
        const response = await fetch(`/ticker/${symbol}`, {
            headers: { 'Authorization': `Bearer ${userId}` }
        });
        return { status: response.status, data: await response.json() };
    }
};

// Display handling
const display = {
    showNotification(message, duration = 5000) {
        const notification = document.getElementById('notification');
        notification.querySelector('p').textContent = message;
        notification.classList.remove('hidden');
        setTimeout(() => notification.classList.add('hidden'), duration);
    },

    updateResults(data) {
        const latestFinancials = data.financial_data[0];
        const results = document.getElementById('results');
        results.innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <h3 class="text-xl mb-2">Current Price</h3>
                    <p class="text-2xl font-bold">$${data.additional_data.current_price.toFixed(2)}</p>
                </div>
                <div>
                    <h3 class="text-xl mb-2">P/E Ratio</h3>
                    <p class="text-2xl font-bold">${data.additional_data.pe_ratio.toFixed(2)}</p>
                </div>
                <div>
                    <h3 class="text-xl mb-2">Revenue (Latest)</h3>
                    <p class="text-2xl font-bold">$${(latestFinancials.totalRevenue / 1e9).toFixed(2)}B</p>
                </div>
                <div>
                    <h3 class="text-xl mb-2">Net Income (Latest)</h3>
                    <p class="text-2xl font-bold">$${(latestFinancials.netIncome / 1e9).toFixed(2)}B</p>
                </div>
            </div>
        `;
        results.classList.remove('hidden');
    },

    showLoading() {
        const results = document.getElementById('results');
        results.classList.remove('hidden');
        results.innerHTML = `
            <div class="text-center py-4">
                <p class="text-xl">Loading...</p>
            </div>
        `;
    },

    clearResults() {
        const results = document.getElementById('results');
        results.classList.add('hidden');
        results.innerHTML = '';
    }
};

// Session management
const session = {
    userId: null,
    lastKnownCredits: null,

    async init() {
        this.userId = localStorage.getItem('userId');
        
        if (!this.userId) {
            await this.createNew();
        }
        
        document.getElementById('userId').value = this.userId;
        await this.refreshCredits();
    },

    async createNew() {
        const data = await api.signup();
        this.userId = data.id;
        localStorage.setItem('userId', this.userId);
        document.getElementById('userId').value = this.userId;
        await this.refreshCredits();
        display.showNotification(`New account created! You received ${data.credits} free credit(s)`);
    },

    async refreshCredits() {
        const data = await api.getInfo(this.userId);
        const newCredits = data.credits;
        document.getElementById('credits').textContent = newCredits;

        if (this.lastKnownCredits !== null && newCredits > this.lastKnownCredits) {
            const creditsAdded = newCredits - this.lastKnownCredits;
            display.showNotification(`Payment successful! Added ${creditsAdded} credit(s)`);
            payments.hideModal();
        }
        
        this.lastKnownCredits = newCredits;
    }
};

// Payment handling
const payments = {
    async showOffers(offers) {
        const modal = document.getElementById('paymentModal');
        const offersContainer = document.getElementById('offers');
        
        offersContainer.innerHTML = offers.map(offer => `
            <div class="bg-gray-700 p-4 rounded">
                <h3 class="text-xl mb-2">${offer.title}</h3>
                <p class="mb-4">${offer.description}</p>
                <div class="flex flex-wrap gap-2">
                    ${offer.payment_methods.map(method => this.createPaymentButton(method)).join('')}
                </div>
            </div>
        `).join('');

        modal.classList.remove('hidden');
    },

    createPaymentButton(method) {
        if (method.payment_type === 'lightning') {
            return `<button onclick="payments.showLightningQR('${method.payment_details.payment_request}')"
                    class="bg-yellow-600 hover:bg-yellow-700 transition-colors px-4 py-2 rounded flex items-center">
                    <span class="mr-2">⚡</span> Pay with Lightning</button>`;
        }
        if (method.payment_type === 'stripe') {
            return `<button onclick="window.location.href='${method.payment_details.payment_link}'"
                    class="bg-blue-600 hover:bg-blue-700 transition-colors px-4 py-2 rounded flex items-center">
                    <span class="mr-2">💳</span> Pay with Card</button>`;
        }
        if (method.payment_type === 'coinbase') {
            return `<button onclick="window.location.href='${method.payment_details.payment_request}'"
                    class="bg-blue-400 hover:bg-blue-500 transition-colors px-4 py-2 rounded flex items-center">
                    <span class="mr-2">₿</span> Pay with Crypto</button>`;
        }
    },

    showLightningQR(paymentRequest) {
        const qrDiv = document.getElementById('qrcode');
        qrDiv.innerHTML = '';
        
        const canvas = document.createElement('canvas');
        qrDiv.appendChild(canvas);
        
        QRCode.toCanvas(canvas, paymentRequest, { 
            width: 300,
            margin: 2,
            color: {
                dark: '#FFF',
                light: '#000'
            }
        });
    },

    hideModal() {
        document.getElementById('paymentModal').classList.add('hidden');
        document.getElementById('qrcode').innerHTML = '';
    }
};

// Initialize everything
document.addEventListener('DOMContentLoaded', () => {
    session.init();
    
    // Setup event listeners
    document.getElementById('getNewKey').addEventListener('click', () => session.createNew());
    document.getElementById('closeModal').addEventListener('click', () => payments.hideModal());
    
    document.querySelectorAll('.ticker-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            try {
                const symbol = btn.dataset.symbol;
                display.showLoading();
                
                const result = await api.getTicker(session.userId, symbol);
                
                if (result.status === 402) {
                    display.clearResults();
                    payments.showOffers(result.data.offers);
                } else if (result.status === 200) {
                    display.updateResults(result.data);
                } else {
                    throw new Error(`HTTP error! status: ${result.status}`);
                }
                
                await session.refreshCredits();
            } catch (error) {
                display.showNotification('Error: ' + error.message);
                display.clearResults();
            }
        });
    });

    // Start polling credits
    setInterval(() => session.refreshCredits(), 10000);
});