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
    _invoiceCache: new Map(), // Cache for storing only lightning invoices

    async showOffers(offersData) {
        window._lastOffers = offersData; // Store the entire response data
        const modal = document.getElementById('paymentModal');
        const offersContainer = document.getElementById('offers');
        
        offersContainer.innerHTML = offersData.offers.map(offer => `
            <div class="bg-gray-700 p-4 rounded">
                <h3 class="text-xl mb-2">${offer.title}</h3>
                <p class="mb-4">${offer.description}</p>
                <p class="mb-4 text-lg">$${(offer.amount / 100).toFixed(2)} USD</p>
                <div class="flex flex-col gap-2">
                    ${this.createPaymentButtons(offer)}
                </div>
            </div>
        `).join('');

        modal.classList.remove('hidden');
    },

    createPaymentButtons(offer) {
        return `
            <div class="grid grid-cols-3 gap-2">
                ${offer.payment_methods.map(method => `
                    <button onclick="payments.initiatePayment('${offer.offer_id}', '${method}')"
                            class="payment-btn ${this.getButtonStyle(method)} px-4 py-2 rounded flex items-center justify-center">
                        <span class="mr-2">${this.getPaymentIcon(method)}</span> 
                        ${this.getPaymentLabel(method)}
                    </button>
                `).join('')}
            </div>
        `;
    },

    getButtonStyle(method) {
        const styles = {
            'lightning': 'bg-yellow-600 hover:bg-yellow-700',
            'coinbase_commerce': 'bg-blue-400 hover:bg-blue-500',
            'credit_card': 'bg-blue-600 hover:bg-blue-700'
        };
        return styles[method] || 'bg-gray-600 hover:bg-gray-700';
    },

    getPaymentIcon(method) {
        const icons = {
            'lightning': '⚡',
            'coinbase_commerce': '₿',
            'credit_card': '💳'
        };
        
        return icons[method] || '💰';
    },

    getPaymentLabel(method) {
        const labels = {
            'lightning': 'Lightning',
            'coinbase_commerce': 'Crypto',
            'credit_card': 'Card'
        };
        return labels[method] || method;
    },

    getCacheKey(offerId) {
        return `lightning_${offerId}`;
    },

    async initiatePayment(offerId, paymentMethod) {
        try {
            let paymentData;
            const paymentContextToken = window._lastOffers?.payment_context_token;
            
            if (!paymentContextToken) {
                throw new Error('Missing payment context token');
            }

            if (paymentMethod === 'lightning') {
                const cacheKey = this.getCacheKey(offerId);
                paymentData = this._invoiceCache.get(cacheKey);

                if (!paymentData) {
                    const response = await fetch('/l402/payment-request', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            offer_id: offerId,
                            payment_method: paymentMethod,
                            payment_context_token: paymentContextToken
                        })
                    });

                    if (!response.ok) {
                        throw new Error('Failed to initiate payment');
                    }

                    paymentData = await response.json();
                    
                    // Only cache lightning invoices that aren't close to expiring
                    const expiryTime = new Date(paymentData.expires_at);
                    const fiveMinutesFromNow = new Date(Date.now() + 5 * 60 * 1000);
                    
                    if (expiryTime > fiveMinutesFromNow) {
                        this._invoiceCache.set(cacheKey, paymentData);
                    }
                }
                
                await qrcode.showLightningQR(paymentData.payment_request.lightning_invoice);
            } else {
                // Handle credit card and coinbase commerce payments
                const response = await fetch('/l402/payment-request', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        offer_id: offerId,
                        payment_method: paymentMethod,
                        payment_context_token: paymentContextToken
                    })
                });

                if (!response.ok) {
                    throw new Error('Failed to initiate payment');
                }

                paymentData = await response.json();
                
                if (paymentData.payment_request.checkout_url) {
                    window.location.href = paymentData.payment_request.checkout_url;
                } else {
                    throw new Error('No checkout URL provided');
                }
            }
        } catch (error) {
            display.showNotification('Error initiating payment: ' + error.message);
        }
    },

    toggleLightningQR(button, paymentRequest) {
        const selectedContainer = button.closest('.payment-method-container').querySelector('.qr-container');
        
        // First hide all QR containers
        document.querySelectorAll('.qr-container').forEach(container => {
            if (container !== selectedContainer) {
                container.classList.add('hidden');
                container.innerHTML = '';
            }
        });
        
        // Toggle the selected QR container
        if (!selectedContainer.classList.contains('hidden')) {
            selectedContainer.classList.add('hidden');
            selectedContainer.innerHTML = '';
            return;
        }

        // Show and generate QR for selected container
        selectedContainer.classList.remove('hidden');
        const canvas = document.createElement('canvas');
        selectedContainer.appendChild(canvas);
        
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
        document.querySelectorAll('.qr-container').forEach(container => {
            container.innerHTML = '';
            container.classList.add('hidden');
        });
        qrcode.clearCheckInterval(); // Clear the payment check interval
        this._invoiceCache.clear(); // Clear the invoice cache
    },

    clearCache() {
        this._invoiceCache.clear();
    }
};

// First, add this helper function for QR code generation
const qrcode = {
    _checkInterval: null,

    async showLightningQR(invoice) {
        const offersContainer = document.getElementById('offers');
        
        // Add QR content alongside the existing offers
        offersContainer.innerHTML = `
            <div class="bg-gray-700 p-4 rounded">
                <h3 class="text-xl mb-4">Scan Lightning Invoice</h3>
                <div id="qrcode" class="flex justify-center mb-4 bg-black p-4 rounded mx-auto" style="width: fit-content;"></div>
                <div class="flex items-center justify-center gap-2 mb-4">
                    <button onclick="navigator.clipboard.writeText('${invoice}')" 
                            class="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                  d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/>
                        </svg>
                        Copy Invoice
                    </button>
                </div>
                <button onclick="payments.showOffers(window._lastOffers)" 
                        class="mt-4 text-sm text-blue-400 hover:text-blue-300">
                    ← Back to payment methods
                </button>
            </div>
        `;

        // Clear any existing QR code and interval
        const qrContainer = document.getElementById("qrcode");
        qrContainer.innerHTML = '';
        this.clearCheckInterval();

        // Create canvas and generate QR
        const canvas = document.createElement('canvas');
        qrContainer.appendChild(canvas);
        
        QRCode.toCanvas(canvas, invoice, { 
            width: 300,
            margin: 2,
            color: {
                dark: '#FFF',
                light: '#000'
            }
        });

        // Start checking for payment completion
        this.startPaymentCheck();
    },

    startPaymentCheck() {
        const initialCredits = session.lastKnownCredits;
        
        this._checkInterval = setInterval(async () => {
            await session.refreshCredits();
            
            // If credits increased, payment was successful
            if (session.lastKnownCredits > initialCredits) {
                this.clearCheckInterval();
                location.reload(); // Reload the page to show new data
            }
        }, 2000); // Check every 2 seconds
    },

    clearCheckInterval() {
        if (this._checkInterval) {
            clearInterval(this._checkInterval);
            this._checkInterval = null;
        }
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
                    payments.showOffers(result.data);
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