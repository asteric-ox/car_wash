// Auth State
let currentUser = null;

// Password Visibility Toggle
function togglePassword(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);

    if (input.type === "password") {
        input.type = "text";
        icon.classList.remove("fa-eye");
        icon.classList.add("fa-eye-slash");
    } else {
        input.type = "password";
        icon.classList.remove("fa-eye-slash");
        icon.classList.add("fa-eye");
    }
}

// Auth Functions (Global)
function toggleAuthModal() {
    const modal = document.getElementById('auth-modal');
    modal.classList.toggle('hidden');
}

function togglePickupStatusModal() {
    const modal = document.getElementById('pickup-status-modal');
    if (modal) modal.classList.toggle('hidden');
}

function switchAuthMode(mode) {
    const loginContainer = document.getElementById('login-form-container');
    const registerContainer = document.getElementById('register-form-container');
    const forgotContainer = document.getElementById('forgot-form-container');
    const resetContainer = document.getElementById('reset-form-container');
    const loginTab = document.getElementById('login-tab');
    const staffTab = document.getElementById('staff-tab');
    const loginTitle = document.getElementById('login-title');
    const loginSubtitle = document.getElementById('login-subtitle');

    if (mode === 'login' || mode === 'staff') {
        loginContainer.style.left = "30px";
        registerContainer.style.left = "450px";
        if (forgotContainer) forgotContainer.style.left = "450px";
        if (resetContainer) resetContainer.style.left = "450px";

        if (loginTab && staffTab) {
            if (mode === 'login') {
                loginTab.classList.add('bg-brand-primary', 'text-brand-dark');
                loginTab.classList.remove('text-slate-400');
                staffTab.classList.remove('bg-brand-primary', 'text-brand-dark');
                staffTab.classList.add('text-slate-400', 'hover:text-white');
                if (loginTitle) loginTitle.textContent = "Welcome Back";
                if (loginSubtitle) loginSubtitle.textContent = "Ready for a premium wash?";
            } else {
                staffTab.classList.add('bg-brand-primary', 'text-brand-dark');
                staffTab.classList.remove('text-slate-400', 'hover:text-white');
                loginTab.classList.remove('bg-brand-primary', 'text-brand-dark');
                loginTab.classList.add('text-slate-400', 'hover:text-white');
                if (loginTitle) loginTitle.textContent = "Staff";
                if (loginSubtitle) loginSubtitle.textContent = "Management Portal Login";
            }
        }
    } else if (mode === 'register') {
        loginContainer.style.left = "-400px";
        registerContainer.style.left = "30px";
        if (forgotContainer) forgotContainer.style.left = "450px";
        if (resetContainer) resetContainer.style.left = "450px";
    } else if (mode === 'forgot') {
        loginContainer.style.left = "-400px";
        registerContainer.style.left = "450px";
        if (forgotContainer) forgotContainer.style.left = "30px";
        if (resetContainer) resetContainer.style.left = "450px";
    } else if (mode === 'reset') {
        loginContainer.style.left = "-400px";
        registerContainer.style.left = "450px";
        if (forgotContainer) forgotContainer.style.left = "450px";
        if (resetContainer) resetContainer.style.left = "30px";
    }
}

async function logout() {
    try {
        await fetch('/api/logout', { method: 'POST' });
        window.location.href = '/index.html';
    } catch (err) {
        console.error(err);
        window.location.reload();
    }
}


document.addEventListener('DOMContentLoaded', () => {
    // Check Auth on Load
    checkAuth();

    async function checkAuth() {
        try {
            const res = await fetch('/api/check-auth');
            const data = await res.json();
            if (data.authenticated) {
                currentUser = data.user;
                updateUserUI(data.user);
                fetchNotifications();
                // Pre-fill booking form
                const nameInput = document.querySelector('input[name="name"]');
                const phoneInput = document.querySelector('input[name="phone"]');
                const emailInput = document.querySelector('input[name="email"]');

                if (nameInput) nameInput.value = data.user.name;
                if (phoneInput) phoneInput.value = data.user.phone;
                if (emailInput && data.user.email) emailInput.value = data.user.email;
            } else {
                updateUserUI(null);
            }
        } catch (err) {
            console.error('Auth check failed', err);
        }
    }

    async function fetchNotifications() {
        try {
            const res = await fetch('/api/notifications');
            const data = await res.json();
            const badge = document.getElementById('notif-badge');
            const btn = document.getElementById('notif-btn');

            if (badge && btn) {
                const unreadCount = data.filter(n => !n.is_read).length; // 0 or false

                if (unreadCount > 0) {
                    badge.textContent = unreadCount;
                    badge.classList.remove('hidden');
                } else {
                    badge.classList.add('hidden');
                }

                // Click to read
                btn.onclick = async () => {
                    if (data.length === 0) {
                        alert('No notifications.');
                        return;
                    }

                    // Format message nicely
                    const msg = data.map(n => {
                        const status = n.is_read ? '✓' : '•';
                        return `${status} ${n.message} (${new Date(n.created_at).toLocaleDateString()})`;
                    }).join('\n');

                    alert('Notifications:\n' + msg);

                    // Mark as read if there were unread ones
                    if (unreadCount > 0) {
                        try {
                            await fetch('/api/notifications/mark-read', { method: 'POST' });
                            // Update UI immediately
                            badge.classList.add('hidden');
                            // Re-fetch to sync simple state if needed, or just rely on hide
                        } catch (e) {
                            console.error('Failed to mark read', e);
                        }
                    }
                };
            }
        } catch (err) {
            console.error(err);
        }
    }

    function updateUserUI(user) {
        const container = document.getElementById('user-menu-container');
        if (user) {
            const profilePic = user.profile_pic || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(user.name) + '&background=06b6d4&color=fff';
            container.innerHTML = `
                <div class="flex items-center gap-4">
                    <button id="notif-btn" class="relative text-slate-300 hover:text-brand-primary transition-all p-2.5 rounded-xl bg-white/5 border border-white/5 hover:border-brand-primary/30">
                        <i class="fa-solid fa-bell text-lg"></i>
                        <span id="notif-badge" class="absolute top-0 right-0 bg-red-500 text-white text-[9px] font-black rounded-full w-4 h-4 flex items-center justify-center hidden shadow-lg border border-brand-dark scale-110">0</span>
                    </button>
                    <button onclick="toggleProfileModal()" class="flex items-center gap-2 hover:bg-white/10 p-1 pr-4 rounded-xl transition-all group bg-white/5 border border-white/5 hover:border-brand-primary/20">
                        <img src="${profilePic}" alt="Profile" class="w-8 h-8 rounded-lg border border-white/10 group-hover:border-brand-primary/50 transition-all">
                        <div class="flex flex-col items-start hidden lg:flex">
                            <span class="text-[9px] text-slate-500 uppercase tracking-widest font-black leading-none mb-0.5">Settings</span>
                            <span class="text-xs font-bold text-white leading-tight">${user.name.split(' ')[0]}</span>
                        </div>
                    </button>
                    
                    <!-- NEW: Impressive Logout Button -->
                    <button onclick="logout()" 
                        class="flex items-center gap-2 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500 hover:text-white transition-all duration-300 group shadow-lg shadow-red-500/5">
                        <i class="fa-solid fa-power-off text-sm group-hover:rotate-12 transition-transform"></i>
                        <span class="text-[10px] font-black uppercase tracking-widest hidden md:block">Logout</span>
                    </button>

                    <a href="#book" class="bg-brand-primary text-brand-dark font-black px-6 py-2.5 rounded-xl text-xs uppercase tracking-widest shadow-xl shadow-cyan-500/20 hover:brightness-110 hover:scale-105 transition-all">Book</a>
                </div>
            `;
        } else {
            container.innerHTML = `
                <button onclick="toggleAuthModal()" class="btn-primary px-6 py-2 rounded-full shadow-lg hover:shadow-cyan-500/20 transition-all font-bold">Login</button>
            `;
        }
    }

    // Login Form
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(loginForm);
            const data = Object.fromEntries(formData.entries());

            try {
                // Try Customer Login First
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                if (result.success) {
                    if (result.redirect) {
                        window.location.href = result.redirect;
                    } else {
                        window.location.reload();
                    }
                    return;
                } else {
                    alert(result.message || 'Invalid credentials');
                }
            } catch (err) {
                console.error(err);
                alert('Login process failed. Please check connection.');
            }
        });
    }

    // Register Form
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(registerForm);

            // Combine Phone
            const countryCode = formData.get('country_code');
            const localPhone = formData.get('phone_local');
            const fullPhone = `${countryCode} ${localPhone}`;

            const data = Object.fromEntries(formData.entries());
            data.phone = fullPhone; // Override/Set phone field

            // Ensure fullname is set (backend expects fullname or name)
            if (data.name && !data.fullname) {
                data.fullname = data.name;
            }

            // Check if passwords match
            if (data.password !== data.confirm_password) {
                alert('Passwords do not match. Please check again.');
                return;
            }

            console.log('Registration data being sent:', data);

            try {
                const res = await fetch('/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                console.log('Registration response:', result);

                if (result.success) {
                    alert('Registration successful! Please login.');
                    switchAuthMode('login');
                    registerForm.reset(); // Clear the form
                } else {
                    alert(result.message || 'Registration failed. Please try again.');
                }
            } catch (err) {
                console.error('Registration error:', err);
                alert('Registration failed: ' + err.message);
            }
        });
    }

    // Forgot Password Form
    const forgotForm = document.getElementById('forgot-form');
    if (forgotForm) {
        forgotForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = forgotForm.querySelector('button');
            const originalText = submitBtn.innerHTML;

            const email = new FormData(forgotForm).get('email');

            try {
                submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
                submitBtn.disabled = true;

                const res = await fetch('/api/forgot-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email })
                });
                const result = await res.json();
                if (result.success) {
                    showNotification('OTP Sent', result.message, 'success');
                    // Store email for step 2 in session storage
                    sessionStorage.setItem('resetEmail', email);
                    switchAuthMode('reset');
                } else {
                    showNotification('Error', result.message, 'error');
                }
            } catch (err) {
                showNotification('Error', 'Connection error. Please try again.', 'error');
            } finally {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        });
    }

    // Reset Password Form
    const resetForm = document.getElementById('reset-form');
    if (resetForm) {
        resetForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = resetForm.querySelector('button');
            const originalText = submitBtn.innerHTML;

            const formData = new FormData(resetForm);
            const data = Object.fromEntries(formData.entries());
            data.email = sessionStorage.getItem('resetEmail');

            if (!data.email) {
                showNotification('Error', 'Reference lost. Please start over.', 'warning');
                switchAuthMode('forgot');
                return;
            }

            try {
                submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Updating...';
                submitBtn.disabled = true;

                const res = await fetch('/api/reset-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                if (result.success) {
                    showNotification('Success', result.message, 'success');
                    switchAuthMode('login');
                    resetForm.reset();
                    sessionStorage.removeItem('resetEmail');
                } else {
                    showNotification('Error', result.message, 'error');
                }
            } catch (err) {
                showNotification('Error', 'Connection error. Please try again.', 'error');
            } finally {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        });
    }

    // Weather Widget Mock
    fetch('/api/weather')
        .then(res => res.json())
        .then(data => {
            const widget = document.getElementById('weather-widget');
            widget.innerHTML = `<span class="text-lg">${data.icon}</span> <span>${data.desc}</span>`;
        })
        .catch(err => {
            console.log('Weather API not available (using mock data)');
            // Fallback if server is not running or error
            const widget = document.getElementById('weather-widget');
            widget.innerHTML = `<span class="text-lg">☀️</span> <span>Great day for a shine!</span>`;
        });

    // Date Input Default to Today
    const dateInput = document.querySelector('input[name="date"]');
    if (dateInput) {
        dateInput.valueAsDate = new Date();
    }

    // Vehicle Selection - Hide Addons for Bike & Change Packages
    const vehicleRadios = document.querySelectorAll('input[name="vehicle"]');
    const addonsContainer = document.getElementById('addons-container');
    const addonCheckboxes = addonsContainer ? addonsContainer.querySelectorAll('input[type="checkbox"]') : [];
    const packageSelect = document.getElementById('package-select');
    // Store original car packages
    const carPackagesHTML = packageSelect ? packageSelect.innerHTML : '';

    function handleVehicleChange() {
        if (!addonsContainer || !packageSelect) return;

        const selectedVehicle = document.querySelector('input[name="vehicle"]:checked')?.value;

        if (selectedVehicle === 'Bike') {
            // Hide addons
            addonsContainer.classList.add('hidden');
            addonCheckboxes.forEach(cb => cb.checked = false);

            // Set Bike specific package
            packageSelect.innerHTML = '<option value="Full Body Wash">Full Body Wash - ₹200</option>';
        } else {
            // Show addons
            addonsContainer.classList.remove('hidden');

            // Restore Car packages if we are currently showing Bike packages
            if (packageSelect.innerHTML.includes('Full Body Wash')) {
                packageSelect.innerHTML = carPackagesHTML;
            }
            // Update package UI
            handlePackageChange();
        }
    }

    function handlePackageChange() {
        const coreFeatures = document.querySelectorAll('.core-feature');
        if (packageSelect && packageSelect.value === 'Customize') {
            coreFeatures.forEach(el => el.classList.remove('hidden'));
        } else {
            coreFeatures.forEach(el => {
                el.classList.add('hidden');
                const cb = el.querySelector('input');
                if (cb) cb.checked = false;
            });
        }
    }

    vehicleRadios.forEach(radio => {
        radio.addEventListener('change', handleVehicleChange);
    });

    if (packageSelect) {
        packageSelect.addEventListener('change', handlePackageChange);
    }

    // Run once on load
    handleVehicleChange();
});

// Mobile Menu
function toggleMobileMenu() {
    const menu = document.getElementById('mobile-menu');
    menu.classList.toggle('hidden');
    menu.classList.toggle('flex');
}

// Booking Wizard Steps
let currentStep = 1;

function nextStep(step) {
    document.getElementById(`step-${currentStep}`).classList.add('hidden');
    document.getElementById(`step-${step}`).classList.remove('hidden');

    // Update Dots
    updateDots(step);

    currentStep = step;
}

function prevStep(step) {
    document.getElementById(`step-${currentStep}`).classList.add('hidden');
    document.getElementById(`step-${step}`).classList.remove('hidden');

    updateDots(step);

    currentStep = step;
}

function updateDots(step) {
    for (let i = 1; i <= 3; i++) {
        const dot = document.getElementById(`step-dot-${i}`);
        if (i <= step) {
            dot.classList.remove('bg-slate-600');
            dot.classList.add('bg-brand-primary');
        } else {
            dot.classList.remove('bg-brand-primary');
            dot.classList.add('bg-slate-600');
        }
    }
}

// Handle general Book Now clicks
function handleBookClick() {
    if (!currentUser) {
        // alert('Please login to book an appointment.');
        toggleAuthModal();
        return;
    }
    const bookSection = document.getElementById('book') || document.getElementById('step-1');
    if (bookSection) bookSection.scrollIntoView({ behavior: 'smooth' });
}

// Quick Select Packet from Pricing Table
function selectPackage(pkgName) {
    if (!currentUser) {
        // alert('Please login to select a package.');
        toggleAuthModal();
        return;
    }
    const select = document.getElementById('package-select');
    if (select) {
        select.value = pkgName;
        // Trigger change event if needed for custom logic
        select.dispatchEvent(new Event('change'));
    }

    const bookSection = document.getElementById('book') || document.getElementById('booking-form');
    if (bookSection) bookSection.scrollIntoView({ behavior: 'smooth' });
}

// Booking Form Submission
const form = document.getElementById('booking-form');
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const btn = form.querySelector('button[type="submit"]');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
    btn.disabled = true;

    // Harvest Data
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Handle multi-checkbox
    const addons = [...form.querySelectorAll('input[name="addons"]:checked')].map(e => e.value);
    data.addons = addons;

    // ATTATCH PICKUP LOCATION IF EXISTS
    const pickupLoc = sessionStorage.getItem('pending_pickup_location');
    if (pickupLoc) {
        data.location = pickupLoc;
        data.is_pickup = 1;
    }

    try {
        const response = await fetch('/api/book', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (response.status === 401) {
            alert('Please login to continue booking.');
            toggleAuthModal();
            btn.innerHTML = originalText;
            btn.disabled = false;
            return;
        }

        const result = await response.json();

        if (result.success) {
            showNotification('Booking Confirmed!', `Check your email for details. ID: #${result.bookingId}`, 'success');

            // If it was a pickup, clear storage and show status modal
            if (pickupLoc) {
                sessionStorage.removeItem('pending_pickup_location');
                localStorage.setItem('active_pickup_id', result.bookingId);
                localStorage.setItem('active_pickup_time', Date.now());

                // Update Status Modal UI
                const statusModalId = document.getElementById('status-booking-id');
                const callBtn = document.getElementById('status-call-btn');

                // Reset call prompt flag for THIS session
                window.callPromptShown = false;

                if (statusModalId) statusModalId.textContent = `#${result.bookingId}`;
                if (callBtn) callBtn.href = `tel:${result.staffPhone || '8590624912'}`;

                // Show the specialized status modal
                togglePickupStatusModal();

                // Still start the background timer for automatic follow-up and status checks
                startPickupConfirmationTimer(result.bookingId);
            }

            // Print Bill
            if (confirm("Do you want to print the receipt?")) {
                try {
                    printBill(data, result.bookingId);
                } catch (e) {
                    console.error("Print failed", e);
                    alert("Unable to open print window. Please disable your popup blocker.");
                }
            }

            // window.location.reload(); // Don't reload, just reset and update UI
            form.reset();
            // Go back to step 1
            document.getElementById('step-3').classList.add('hidden');
            document.getElementById('step-1').classList.remove('hidden');
            updateDots(1);
            currentStep = 1;

            // Refresh notifications ensuring the red dot appears
            fetchNotifications();

            // Return to Slots if requested
            if (window.returnToSlots) {
                toggleSlotModal();
                showNotification('Slot Confirmed', 'Your slot has been reserved.', 'success');
                window.returnToSlots = false;
            }
        } else {
            alert('Something went wrong: ' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Could not connect to server. Please try again.');
    } finally {
        if (!btn.disabled && btn.innerHTML !== originalText) {
            // Already handled by 401 block or similar logic
        } else {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }
});

// Loyalty Check
function checkLoyalty() {
    const phone = document.getElementById('loyalty-phone').value;
    const msg = document.getElementById('loyalty-msg');

    if (!phone) {
        msg.textContent = 'Please enter a phone number.';
        msg.className = 'text-sm mt-3 text-center h-5 text-red-400';
        return;
    }

    // Mock API call
    fetch(`/api/loyalty/${phone}`)
        .then(res => res.json())
        .then(data => {
            if (data.freeWash) {
                msg.textContent = `🎉 You have ${data.stamps} stamps! Next one is FREE!`;
                msg.className = 'text-sm mt-3 text-center h-5 text-green-400 font-bold';
            } else {
                msg.textContent = `You have ${data.stamps} stamps. ${5 - data.stamps} more for a free wash!`;
                msg.className = 'text-sm mt-3 text-center h-5 text-amber-400';
            }
        })
        .catch(() => {
            // Mock fallback
            const stamps = Math.floor(Math.random() * 5);
            msg.textContent = `Mock: You have ${stamps} stamps.`;
            msg.className = 'text-sm mt-3 text-center h-5 text-slate-400';
        });
}



document.addEventListener('DOMContentLoaded', () => {


    // Start Loops
    fetchShopStatus();
    setInterval(fetchShopStatus, 10000); // Poll every 10s
});

async function fetchShopStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();

        const container = document.getElementById('hero-status-container');
        const card = document.getElementById('hero-status-card');
        const text = document.getElementById('status-text');
        const dot = document.getElementById('status-dot');
        const ping = document.getElementById('status-ping');

        const queueEl = document.getElementById('status-queue');
        const waitEl = document.getElementById('status-wait');

        if (container) {
            container.classList.remove('hidden');

            const status = data.status || 'OPEN';

            // --- MAINTENANCE BANNER LOGIC ---
            const isMaintenance = status === 'MAINTENANCE' || status === 'EMERGENCY MAINTENANCE';
            let maintenanceBanner = document.getElementById('maintenance-overlay');

            if (isMaintenance) {
                // Create or show maintenance overlay
                if (!maintenanceBanner) {
                    maintenanceBanner = document.createElement('div');
                    maintenanceBanner.id = 'maintenance-overlay';
                    maintenanceBanner.style.cssText = `
                        position: fixed; inset: 0; z-index: 9999;
                        display: flex; align-items: center; justify-content: center;
                        background: rgba(3,7,18,0.93);
                        backdrop-filter: blur(20px);
                        flex-direction: column; gap: 24px;
                        animation: fadeIn 0.5s ease;
                    `;
                    maintenanceBanner.innerHTML = `
                        <div style="text-align:center; max-width: 520px; padding: 2rem;">
                            <div style="font-size:5rem; margin-bottom:1rem; animation: pulse 2s infinite;">🔧</div>
                            <h1 style="font-size:2rem; font-weight:900; color:#f59e0b; margin-bottom:0.5rem; letter-spacing:-0.05em;">Under Maintenance</h1>
                            <p style="color:#94a3b8; font-size:1rem; margin-bottom:1.5rem; line-height:1.6;">
                                ${data.message || 'D2 Car Wash is temporarily undergoing maintenance. We will be back shortly!'}
                            </p>
                            <div style="display:inline-flex; align-items:center; gap:8px; background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); padding:12px 24px; border-radius:100px; color:#f59e0b; font-weight:700;">
                                <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#f59e0b; animation:ping 1s infinite;"></span>
                                ${status}
                            </div>
                            <p style="color:#475569; font-size:0.75rem; margin-top:1.5rem;">Last updated by: ${data.updated_by || 'Admin'}</p>
                        </div>
                    `;
                    document.body.appendChild(maintenanceBanner);
                } else {
                    maintenanceBanner.style.display = 'flex';
                }
            } else {
                // Hide banner if status is normal
                if (maintenanceBanner) {
                    maintenanceBanner.style.display = 'none';
                }
            }

            // UI Themes based on status
            const themes = {
                'OPEN': { dot: 'bg-green-500', ping: 'bg-green-400', text: 'Station Free' },
                'BUSY': { dot: 'bg-yellow-500', ping: 'bg-yellow-400', text: 'Washing' },
                'FULLY BOOKED': { dot: 'bg-orange-500', ping: 'bg-orange-400', text: 'Full Output' },
                'CLOSED': { dot: 'bg-red-500', ping: 'bg-red-400', text: 'Closed' },
                'MAINTENANCE': { dot: 'bg-amber-500', ping: 'bg-amber-400', text: 'Maintenance' },
                'EMERGENCY MAINTENANCE': { dot: 'bg-red-600', ping: 'bg-red-500', text: 'Maintenance' }
            };

            const theme = themes[status] || themes['OPEN'];

            // Update Text (Use custom message if BUSY or CLOSED)
            if (status === 'BUSY' && data.current_vehicle && data.current_vehicle !== 'AUTH_REQUIRED') {
                text.textContent = data.current_vehicle;
            } else if (data.message && status !== 'OPEN') {
                text.textContent = data.message.substring(0, 24);
            } else {
                text.textContent = theme.text;
            }

            // Apply Colors
            if (dot) dot.className = `relative inline-flex rounded-full h-3.5 w-3.5 ${theme.dot}`;
            if (ping) ping.className = `animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${theme.ping}`;

            // Update Stats
            if (queueEl) queueEl.textContent = data.queue_count || 0;
            if (waitEl) waitEl.textContent = data.wait_time || 0;

            // Updated Click Behavior
            card.onclick = () => {
                if (status === 'CLOSED' || status === 'EMERGENCY MAINTENANCE' || status === 'MAINTENANCE') {
                    showNotification('Status Update', data.message || 'We are currently offline.', 'info');
                } else {
                    handleBookClick();
                }
            };
        }
    } catch (e) {
        console.error('Fetch status error', e);
    }
}




// Pickup Service Logic
let map, marker, circle, geocoder;
const SHOP_COORDS = [10.3423754, 76.2625883]; // Kallettumkara
const SERVICE_RADIUS_KM = 3;

function togglePickupModal() {
    const modal = document.getElementById('pickup-modal');
    modal.classList.toggle('hidden');

    if (!modal.classList.contains('hidden') && !map) {
        // Initialize map only when shown
        setTimeout(() => {
            initMap();
        }, 300); // Slight delay for transition
    }
}

function initMap() {
    if (map) return;

    map = L.map('map').setView(SHOP_COORDS, 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    // Initialize Geocoder
    geocoder = L.Control.Geocoder.nominatim();
    const searchInput = document.getElementById('pickup-search-input');
    if (searchInput) {
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') searchLocation();
        });
    }

    // Shop Marker
    const shopIcon = L.icon({
        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/markers/marker-icon-2x-blue.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34]
    });

    L.marker(SHOP_COORDS, { icon: shopIcon }).addTo(map)
        .bindPopup("<b>D2 CAR WASH</b><br>We are here.").openPopup();

    // Service Radius Circle
    L.circle(SHOP_COORDS, {
        color: '#06b6d4',
        fillColor: '#06b6d4',
        fillOpacity: 0.1,
        radius: SERVICE_RADIUS_KM * 1000 // meters
    }).addTo(map);

    // Click handler
    map.on('click', onMapClick);
}

function searchLocation() {
    const searchInput = document.getElementById('pickup-search-input');
    const query = searchInput.value;
    if (!query) return;

    console.log("Searching for:", query);
    if (!geocoder) geocoder = L.Control.Geocoder.nominatim();

    geocoder.geocode(query, function (results) {
        console.log("Results:", results);
        if (results && results.length > 0) {
            const res = results[0];
            const latlng = res.center || res.latlng;
            if (map && latlng) {
                map.setView(latlng, 16);
                onMapClick({ latlng: latlng });
                showNotification('Location Found', res.name, 'success');
            }
        } else {
            showNotification('Location Not Found', 'Try a different search or pin on map.', 'info');
        }
    });
}

function locateMe() {
    const loading = document.getElementById('map-loading');
    if (loading) loading.classList.remove('hidden');

    if (!navigator.geolocation) {
        showNotification('Not Supported', 'Geolocation is not supported by your browser', 'error');
        if (loading) loading.classList.add('hidden');
        return;
    }

    navigator.geolocation.getCurrentPosition((pos) => {
        const coords = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        if (map) {
            map.setView(coords, 16);
            onMapClick({ latlng: coords });
        }
        if (loading) loading.classList.add('hidden');
        showNotification('Location Found', 'GPS coordinates updated.', 'success');
    }, (err) => {
        let msg = 'Could not get your location';
        if (err.code === 1) msg = 'Location access denied. Please allow GPS.';
        showNotification('GPS Error', msg, 'error');
        if (loading) loading.classList.add('hidden');
    }, {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
    });
}

function onMapClick(e) {
    const coords = e.latlng;

    if (marker) {
        marker.setLatLng(coords);
    } else {
        const userIcon = L.icon({
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/markers/marker-icon-2x-red.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41]
        });
        marker = L.marker(coords, { icon: userIcon }).addTo(map);
    }

    // Check Distance
    const dist = getDistanceFromLatLonInKm(SHOP_COORDS[0], SHOP_COORDS[1], coords.lat, coords.lng);
    const btn = document.getElementById('confirm-pickup-btn');
    const msg = document.getElementById('pickup-status-msg');

    if (dist <= SERVICE_RADIUS_KM) {
        // Valid
        msg.innerHTML = `<span class="text-green-400 font-bold"><i class="fa-solid fa-check-circle"></i> Service Available!</span> Distance: ${dist.toFixed(2)} km`;
        btn.disabled = false;
        btn.classList.remove('bg-slate-700', 'text-slate-400', 'cursor-not-allowed');
        btn.classList.add('bg-brand-primary', 'text-brand-dark', 'hover:brightness-110');
        btn.textContent = "Confirm Pickup Location";
    } else {
        // Invalid
        msg.innerHTML = `<span class="text-red-400 font-bold"><i class="fa-solid fa-circle-xmark"></i> Out of Service Area.</span> Distance: ${dist.toFixed(2)} km`;
        btn.disabled = true;
        btn.classList.add('bg-slate-700', 'text-slate-400', 'cursor-not-allowed');
        btn.classList.remove('bg-brand-primary', 'text-brand-dark', 'hover:brightness-110');
        btn.textContent = "Location Too Far";
    }
}

function getDistanceFromLatLonInKm(lat1, lon1, lat2, lon2) {
    var R = 6371; // Radius of the earth in km
    var dLat = deg2rad(lat2 - lat1);
    var dLon = deg2rad(lon2 - lon1);
    var a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);
    var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    var d = R * c; // Distance in km
    return d;
}

function deg2rad(deg) {
    return deg * (Math.PI / 180);
}

// Notification Logic
function showNotification(title, message, type = 'info') {
    const container = document.getElementById('notification-container');
    if (!container) return;

    // Create Toast Element
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    // Icon Map
    const icons = {
        success: 'fa-circle-check',
        error: 'fa-circle-xmark',
        warning: 'fa-triangle-exclamation',
        info: 'fa-circle-info'
    };

    toast.innerHTML = `
        <div class="toast-icon"><i class="fa-solid ${icons[type] || icons.info}"></i></div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-msg">${message}</div>
        </div>
    `;

    container.appendChild(toast);

    // Auto Remove
    setTimeout(() => {
        toast.classList.add('hiding');
        toast.addEventListener('animationend', () => {
            toast.remove();
        });
    }, 4000);
}

// Slot System Logic
let currentSlotDate = new Date();
let currentMonthSlots = [];

function toggleSlotModal() {
    // Remove strict frontend check here, let the API decide or check specifically
    // We will handle the auth error in renderSlotCalendar if the fetch fails with 401

    const modal = document.getElementById('slot-modal');
    modal.classList.toggle('hidden');

    if (!modal.classList.contains('hidden')) {
        renderSlotCalendar();
    }
}

function changeSlotMonth(delta) {
    currentSlotDate.setMonth(currentSlotDate.getMonth() + delta);
    renderSlotCalendar();
}

async function renderSlotCalendar() {
    const grid = document.getElementById('slot-calendar-grid');
    const label = document.getElementById('slot-month-label');

    // Set Label
    const monthNames = ["January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"];
    label.textContent = `${monthNames[currentSlotDate.getMonth()]} ${currentSlotDate.getFullYear()}`;

    // Fetch Slots
    const year = currentSlotDate.getFullYear();
    const month = currentSlotDate.getMonth() + 1;

    // Calc start and end date for query (simple: first to last day)
    const lastDay = new Date(year, month, 0).getDate();
    const startDateStr = `${year}-${String(month).padStart(2, '0')}-01`;
    const endDateStr = `${year}-${String(month).padStart(2, '0')}-${lastDay}`;

    try {
        const res = await fetch(`/api/slots?start=${startDateStr}&end=${endDateStr}`);

        // Public access allowed now

        const data = await res.json();
        if (Array.isArray(data)) {
            currentMonthSlots = data;
        } else {
            currentMonthSlots = [];
        }
    } catch (e) {
        currentMonthSlots = [];
    }

    grid.innerHTML = '';

    // Calendar Logic
    const firstDay = new Date(year, month - 1, 1).getDay();

    // Empty slots for previous month
    for (let i = 0; i < firstDay; i++) {
        const empty = document.createElement('div');
        empty.className = 'h-24 bg-white/5 rounded-xl opacity-50';
        grid.appendChild(empty);
    }

    // Days
    for (let d = 1; d <= lastDay; d++) {
        const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
        const daySlots = currentMonthSlots.filter(s => s.date === dateStr);

        const cell = document.createElement('div');
        cell.className = 'h-24 bg-white/5 rounded-xl p-2 hover:bg-white/10 transition cursor-pointer relative group flex flex-col justify-between';
        cell.onclick = () => openSlotDay(dateStr, daySlots);

        // Date Number
        const isToday = new Date().toISOString().split('T')[0] === dateStr;
        cell.innerHTML = `<div class="font-bold ${isToday ? 'text-brand-primary' : 'text-slate-400'}">${d}</div>`;

        // Slot Indicators
        if (daySlots.length > 0) {
            cell.innerHTML += `
                <div class="space-y-1">
                    <div class="text-[10px] bg-brand-primary/20 text-brand-primary px-1 rounded text-center font-bold">
                        ${daySlots.length} Booked
                    </div>
                </div>
            `;
        } else {
            cell.innerHTML += `<div class="text-[10px] text-slate-600 text-center">Available</div>`;
        }

        grid.appendChild(cell);
    }
}

function openSlotDay(dateStr, bookedSlots) {
    const view = document.getElementById('slot-day-view');
    const label = document.getElementById('slot-day-label');
    const list = document.getElementById('slot-day-list');

    // Format Date for Title
    const dateObj = new Date(dateStr);
    label.textContent = dateObj.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
    list.innerHTML = '';

    // Generate Standard Time Slots (09:00 to 18:00)
    const standardSlots = [
        "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"
    ];

    const bookedTimes = bookedSlots.map(s => s.time);

    standardSlots.forEach(time => {
        const isBooked = bookedTimes.includes(time);
        const bookingDetail = bookedSlots.find(s => s.time === time);

        const item = document.createElement('div');
        item.className = `p-4 rounded-xl border flex justify-between items-center transition ${isBooked ? 'bg-red-500/10 border-red-500/20' : 'bg-green-500/10 border-green-500/20 hover:bg-green-500/20'}`;

        let content = '';
        if (isBooked) {
            content = `
                <div class="flex items-center gap-3">
                    <div class="text-red-400 font-bold">${time}</div>
                    <div class="text-sm text-slate-400">
                        <i class="fa-solid fa-car"></i> ${bookingDetail.vehicle_number || 'Reserved'}
                    </div>
                </div>
                <div class="text-xs text-red-500 font-bold uppercase tracking-wider">Booked</div>
             `;
        } else {
            content = `
                <div class="flex items-center gap-3">
                    <div class="text-green-400 font-bold">${time}</div>
                    <div class="text-sm text-slate-400">Available</div>
                </div>
                <button onclick="bookSpecificSlot('${dateStr}', '${time}')" class="px-4 py-1.5 rounded-lg bg-green-500 text-white text-xs font-bold hover:bg-green-600 transition shadow-lg shadow-green-500/20">
                    Book Now
                </button>
             `;
        }

        item.innerHTML = content;
        list.appendChild(item);
    });

    view.classList.remove('hidden');
}

function closeSlotDayView() {
    document.getElementById('slot-day-view').classList.add('hidden');
}

// Profile Management
function toggleProfileModal() {
    const modal = document.getElementById('profile-modal');
    modal.classList.toggle('hidden');

    if (!modal.classList.contains('hidden') && currentUser) {
        document.getElementById('profile-name').value = currentUser.name;
        document.getElementById('profile-email').value = currentUser.email || '';
        document.getElementById('profile-phone').value = currentUser.phone || '';
        const preview = document.getElementById('profile-pic-preview');
        preview.src = currentUser.profile_pic || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(currentUser.name) + '&background=06b6d4&color=fff';
    }
}

async function updateProfile(event) {
    if (event) event.preventDefault();
    const email = document.getElementById('profile-email').value;
    const phone = document.getElementById('profile-phone').value;

    try {
        const res = await fetch('/api/update-profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, phone })
        });
        const data = await res.json();
        if (data.success) {
            showNotification('Success', 'Profile updated successfully', 'success');
            // Update local state and UI
            currentUser.email = email;
            currentUser.phone = phone;
            // No need to reload, just update UI
        } else {
            showNotification('Error', data.message, 'error');
        }
    } catch (err) {
        showNotification('Error', 'Connection failed', 'error');
    }
}

async function uploadProfilePic(input) {
    if (!input.files || !input.files[0]) return;

    const formData = new FormData();
    formData.append('file', input.files[0]);

    try {
        const res = await fetch('/api/upload-profile-pic', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            currentUser.profile_pic = data.profile_pic;
            document.getElementById('profile-pic-preview').src = data.profile_pic;
            // Update the nav bar pic too
            const navPics = document.querySelectorAll('img[alt="Profile"]');
            navPics.forEach(img => img.src = data.profile_pic);
            showNotification('Success', 'Profile picture updated', 'success');
        } else {
            showNotification('Error', data.message, 'error');
        }
    } catch (err) {
        showNotification('Error', 'Upload failed', 'error');
    }
}

// Dynamic Booking Time Logic
async function updateTimeSlots() {
    const dateInput = document.getElementById('booking-date-input');
    const timeSelect = document.getElementById('booking-time-select');

    if (!dateInput.value) return;

    const dateStr = dateInput.value;

    // Show Loading
    timeSelect.innerHTML = '<option>Loading slots...</option>';
    timeSelect.disabled = true;

    try {
        // Fetch slots for this specific day
        const res = await fetch(`/api/slots?start=${dateStr}&end=${dateStr}`);
        const bookedData = await res.json();

        // Normalize booked times
        const bookedTimes = Array.isArray(bookedData) ? bookedData.map(b => b.time) : [];

        // Generate Options (09:00 to 18:00)
        const times = [
            "09:00", "10:00", "11:00", "12:00",
            "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"
        ];

        timeSelect.innerHTML = '<option value="" disabled selected>Select Time</option>';

        times.forEach(time => {
            const isBooked = bookedTimes.includes(time);
            const option = document.createElement('option');
            option.value = time;

            // Format for display (e.g. 13:00 -> 01:00 PM)
            const [h, m] = time.split(':');
            const hour = parseInt(h);
            const suffix = hour >= 12 ? 'PM' : 'AM';
            const displayHour = hour > 12 ? hour - 12 : (hour === 0 ? 12 : hour);
            const displayTime = `${String(displayHour).padStart(2, '0')}:${m} ${suffix}`;

            if (isBooked) {
                option.text = `${displayTime} (Reserved)`;
                option.disabled = true;
                option.classList.add('text-red-400');
            } else {
                option.text = displayTime;
                option.classList.add('text-green-400');
            }

            timeSelect.appendChild(option);
        });

        timeSelect.disabled = false;

        // If pre-selected time exists (from bookSpecificSlot), select it
        if (window.preSelectedTime) {
            timeSelect.value = window.preSelectedTime;
            window.preSelectedTime = null;
        }

    } catch (e) {
        console.error("Error fetching slots", e);
        timeSelect.innerHTML = '<option>Error loading times</option>';
    }
}

function bookSpecificSlot(dateStr, timeStr) {
    // 1. Close Slot Modal
    toggleSlotModal();

    // Set flag to reopening slots after booking
    window.returnToSlots = true;
    window.preSelectedTime = timeStr; // Store for the dynamic fetch

    // 2. Open Booking Wizard
    handleBookClick();

    // 3. Pre-fill Data
    // We need to wait for the booking wizard to be visible/initialized
    setTimeout(() => {
        // Set Date
        const dateInput = document.querySelector('input[name="date"]');
        if (dateInput) {
            dateInput.value = dateStr;
            // Trigger the change to load times
            updateTimeSlots();
        }
    }, 500);
}

function confirmPickup() {
    if (!marker) return;
    const pos = marker.getLatLng();
    const dist = getDistanceFromLatLonInKm(SHOP_COORDS[0], SHOP_COORDS[1], pos.lat, pos.lng);

    if (dist > SERVICE_RADIUS_KM) {
        showNotification('Too Far', 'Please select a location within 3km.', 'error');
        return;
    }

    // Save to session storage to be picked up by the booking form
    sessionStorage.setItem('pending_pickup_location', `${pos.lat},${pos.lng}`);

    showNotification('Location Selected', 'Please complete your appointment booking.', 'success');
    togglePickupModal();

    // Redirect to booking wizard
    handleBookClick();

    // Visual feedback in notes
    setTimeout(() => {
        const notes = document.querySelector('textarea[name="notes"]');
        if (notes) {
            notes.value = "PICKUP SERVICE REQUESTED (Location Pinned)";
            notes.classList.add('border-brand-primary');
            setTimeout(() => notes.classList.remove('border-brand-primary'), 2000);
        }
    }, 800);
}

function startPickupConfirmationTimer(bookingId) {
    // Clear any existing timer
    if (window.pickupTimer) clearInterval(window.pickupTimer);

    // Initial modal update if ID is known
    const statusModalId = document.getElementById('status-booking-id');
    if (statusModalId && !statusModalId.textContent.includes('#')) {
        statusModalId.textContent = `#${bookingId}`;
    }

    window.pickupTimer = setInterval(async () => {
        const startTime = localStorage.getItem('active_pickup_time');
        const statusTimerSpan = document.getElementById('status-timer');

        if (!startTime) {
            clearInterval(window.pickupTimer);
            return;
        }

        const elapsedMs = Date.now() - parseInt(startTime);
        const elapsedMins = Math.floor(elapsedMs / (1000 * 60));
        const elapsedSecs = Math.floor((elapsedMs / 1000) % 60);

        // Update timer UI in modal if it's open
        if (statusTimerSpan) {
            statusTimerSpan.textContent = `Pending for ${elapsedMins}m ${elapsedSecs.toString().padStart(2, '0')}s`;
        }

        // Only check API every 30 seconds, but keep timer ticking every second
        if (elapsedSecs % 30 !== 0 && elapsedMs > 5000) {
            return;
        }

        // Check Status
        try {
            const res = await fetch(`/api/pickup/status/${bookingId}`);
            const data = await res.json();

            if (data.status === 'Confirmed') {
                showNotification('Pickup Confirmed!', 'The staff has confirmed your pickup request.', 'success');

                // Update Modal UI to success state before closing or just close
                if (statusTimerSpan) statusTimerSpan.textContent = "STAFF CONFIRMED!";

                localStorage.removeItem('active_pickup_id');
                localStorage.removeItem('active_pickup_time');
                clearInterval(window.pickupTimer);

                setTimeout(() => {
                    togglePickupStatusModal();
                }, 2000);
                return;
            }

        } catch (e) {
            console.error('Status check failed', e);
        }
    }, 1000); // Check every second for countdown feel
}


// Check for active pickup on page load
document.addEventListener('DOMContentLoaded', () => {
    const activeId = localStorage.getItem('active_pickup_id');
    if (activeId) {
        startPickupConfirmationTimer(activeId);
    }

    // Start Notification Polling & Live Status
    fetchNotifications();
    updateLiveStatus();
    setInterval(() => {
        fetchNotifications();
        updateLiveStatus();
    }, 10000); // Poll every 10s
});


// Notification System
let lastNotificationCount = 0;

async function updateLiveStatus() {
    const statusText = document.getElementById('status-text');
    const statusDot = document.getElementById('status-dot');
    const statusPing = document.getElementById('status-ping');
    const heroStatusCard = document.getElementById('hero-status-card');

    if (!statusText) return;

    // 1. Check Personal Booking Status first
    const currentUser = JSON.parse(localStorage.getItem('currentUser'));
    if (currentUser) {
        try {
            const res = await fetch(`/api/my_bookings/${currentUser.id}`);
            const bookings = await res.json();

            // Find active booking (not completed/cancelled)
            const activeBooking = bookings.find(b =>
                !['completed', 'cancelled', 'rejected'].includes(b.status.toLowerCase())
            );

            if (activeBooking) {
                if (heroStatusCard) heroStatusCard.parentElement.classList.remove('hidden');

                let displayStatus = activeBooking.status;
                let colorClass = 'bg-blue-500';

                if (displayStatus.toLowerCase() === 'washing') {
                    displayStatus = 'Washing...';
                    colorClass = 'bg-cyan-400';
                } else if (displayStatus.toLowerCase() === 'drying') {
                    displayStatus = 'Drying...';
                    colorClass = 'bg-purple-400';
                } else if (displayStatus.toLowerCase() === 'picked') {
                    displayStatus = 'Picked Up';
                    colorClass = 'bg-pink-500';
                } else if (displayStatus.toLowerCase() === 'delivered') {
                    displayStatus = 'Out for Delivery';
                    colorClass = 'bg-green-500';
                }

                statusText.textContent = `Your Car: ${displayStatus}`;
                statusDot.className = `relative inline-flex rounded-full h-3 w-3 ${colorClass}`;
                statusPing.className = `animate-ping absolute inline-flex h-full w-full rounded-full ${colorClass} opacity-75`;
                return; // Exit if personal status shown
            }
        } catch (e) { console.error(e); }
    }

    // 2. Fallback to Shop Global Status
    try {
        // We need an endpoint for global status or assume free?
        // Reuse admin status endpoint? Or just mock "Station Free" if no personal booking?
        // For this MVP, let's just default to "Station Free" or "Busy" based on a simple fetch if exists.
        // Assuming we implemented /api/shop/status or similar. check app.py

        // Mock for now if no endpoint:
        statusText.textContent = "Station Free";
        statusDot.className = "relative inline-flex rounded-full h-3 w-3 bg-green-500";
        statusPing.className = "animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75";

    } catch (e) { }
}

async function fetchNotifications() {
    const currentUser = JSON.parse(localStorage.getItem('currentUser'));
    if (!currentUser) return; // Not logged in

    try {
        const res = await fetch('/api/notifications');
        const notifications = await res.json();

        if (notifications.length > lastNotificationCount) {
            // New notification!
            const newNotif = notifications[0]; // Assuming sorted DESC
            // Only show toast if it's recent (e.g. within last minute) to avoid spam on page reload? 
            // Ideally we track 'is_read' or last checked timestamp.
            // For now, simple count check.
            if (lastNotificationCount !== 0) { // Don't spam on first load
                showNotification('Update', newNotif.message, 'info');
            }
        }
        lastNotificationCount = notifications.length;

        // Update any UI list if it exists (e.g. bell icon dropdown)
        // updateNotificationList(notifications); 

    } catch (e) {
        console.error("Error fetching notifications", e);
    }
}


function printBill(bookingData, bookingId) {
    const printWindow = window.open('', '', 'height=600,width=800');

    if (!printWindow) {
        alert("Popup blocked! Please allow popups for this site to print your receipt.");
        return;
    }

    // Calculate Total (Simple logic based on packet name - assuming prices for now or passing it)
    let priceEstimate = "Pending Inspection";

    if (bookingData.package.includes('Premium')) priceEstimate = "₹1200 + Addons";
    if (bookingData.package.includes('Deluxe')) priceEstimate = "₹800 + Addons";
    if (bookingData.package.includes('Express')) priceEstimate = "₹450 + Addons";

    printWindow.document.write('<html><head><title>Booking Receipt</title>');
    printWindow.document.write('<style>');
    printWindow.document.write('body { font-family: sans-serif; padding: 40px; color: #333; }');
    printWindow.document.write('.header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #eee; padding-bottom: 20px; }');
    printWindow.document.write('.logo { font-size: 24px; font-weight: bold; color: #06b6d4; }');
    printWindow.document.write('.details { margin-bottom: 20px; line-height: 1.6; }');
    printWindow.document.write('.footer { margin-top: 40px; text-align: center; font-size: 12px; color: #777; border-top: 1px solid #eee; padding-top: 20px; }');
    printWindow.document.write('.btn { display: inline-block; background: #06b6d4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 10px; }');
    printWindow.document.write('</style>');
    printWindow.document.write('</head><body>');

    printWindow.document.write('<div class="header">');
    printWindow.document.write('<div class="logo">D2 CAR WASH</div>');
    printWindow.document.write(`<div>Booking Receipt #${bookingId}</div>`);
    printWindow.document.write('</div>');

    printWindow.document.write('<div class="details">');
    printWindow.document.write(`<strong>Customer:</strong> ${bookingData.name}<br>`);
    printWindow.document.write(`<strong>Vehicle:</strong> ${bookingData.vehicleNumber || 'N/A'} (${bookingData.vehicleType})<br>`);
    printWindow.document.write(`<strong>Service:</strong> ${bookingData.package}<br>`);
    printWindow.document.write(`<strong>Date:</strong> ${bookingData.date} at ${bookingData.time}<br>`);
    printWindow.document.write(`<strong>Add-ons:</strong> ${bookingData.addons.length ? bookingData.addons.join(', ') : 'None'}<br>`);

    printWindow.document.write('<hr style="border: 0; border-top: 1px dashed #ccc; margin: 15px 0;">');
    printWindow.document.write(`<strong>Est. Cost:</strong> ${priceEstimate}<br>`);
    printWindow.document.write('</div>');

    printWindow.document.write('<div class="footer">');
    printWindow.document.write('<p>Thank you for choosing D2 Car Wash!</p>');
    printWindow.document.write('<p>Please rate us on Google Maps:</p>');
    printWindow.document.write('<a href="https://maps.app.goo.gl/AbLovHuWNUxwr5ez7" target="_blank" class="btn">Leave a Review</a>');
    printWindow.document.write('</div>');

    printWindow.document.write('</body></html>');
    printWindow.document.close();
    printWindow.print();
}

// Initialize Scroll Observer for main content
window.addEventListener('load', () => {
    initializeScrollObserver();
});

function typeText(elementId, text) {
    const container = document.getElementById(elementId);
    if (!container) return;

    // Clear and add cursor
    container.innerHTML = '';
    const cursor = document.createElement('span');
    cursor.className = 'typing-cursor';

    text.split('').forEach((char, index) => {
        const span = document.createElement('span');
        span.className = 'letter';
        span.textContent = char === ' ' ? '\u00A0' : char; // Handle spaces
        span.style.animationDelay = `${index * 0.08}s`;
        container.appendChild(span);
    });

    // Add cursor at the end
    container.appendChild(cursor);

    // Remove cursor after typing completes
    setTimeout(() => {
        cursor.style.opacity = '0';
        setTimeout(() => cursor.remove(), 500);
    }, (text.length * 80) + 1000);
}

function initializeScrollObserver() {
    document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scroll').forEach(el => {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                }
            });
        }, { threshold: 0.15 });
        observer.observe(el);
    });
}

function createGlassShards(container) {
    const shardCount = 25;
    for (let i = 0; i < shardCount; i++) {
        const shard = document.createElement('div');
        shard.className = 'shard';

        // Randomize shard properties
        const size = Math.random() * 25 + 5;
        shard.style.width = size + 'px';
        shard.style.height = size + 'px';
        shard.style.left = '50%';
        shard.style.top = '50%';

        // Random clip path for irregular shapes
        const p1 = Math.random() * 100;
        const p2 = Math.random() * 100;
        const p3 = Math.random() * 100;
        shard.style.clipPath = `polygon(${p1}% 0%, 100% ${p2}%, 0% ${p3}%)`;

        container.appendChild(shard);

        // Animation Destinations
        const angle = Math.random() * Math.PI * 2;
        const velocity = Math.random() * 800 + 400;
        const destX = Math.cos(angle) * velocity;
        const destY = Math.sin(angle) * velocity;
        const rotate = Math.random() * 1080 - 540;

        // Force reflow
        shard.offsetHeight;

        shard.style.opacity = '1';
        shard.style.transition = 'all 1.2s cubic-bezier(0.1, 0.5, 0.1, 1)';
        shard.style.transform = `translate(${destX}px, ${destY}px) rotate(${rotate}deg)`;

        setTimeout(() => {
            shard.style.opacity = '0';
            setTimeout(() => shard.remove(), 1000);
        }, 800);
    }
}

// Scroll Reveal Observer
document.addEventListener('DOMContentLoaded', () => {
    const observerOptions = {
        threshold: 0.15
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
            }
        });
    }, observerOptions);

    document.querySelectorAll('.reveal, .reveal-left, .reveal-right').forEach(el => {
        observer.observe(el);
    });
});

function togglePassword(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (input.type === "password") {
        input.type = "text";
        icon.classList.remove("fa-eye");
        icon.classList.add("fa-eye-slash");
    } else {
        input.type = "password";
        icon.classList.remove("fa-eye-slash");
        icon.classList.add("fa-eye");
    }
}
