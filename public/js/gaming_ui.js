/**
 * D2 CAR WASH - Gaming-Inspired UI Features
 * Premium animations, interactions, and visual effects
 */

// =========================
// PARTICLE SYSTEM (Water Droplets)
// =========================
class WaterParticleSystem {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        this.particles = [];
        this.maxParticles = 50;
        this.init();
    }

    init() {
        // Create canvas for particles
        const canvas = document.createElement('canvas');
        canvas.id = 'particle-canvas';
        canvas.style.position = 'fixed';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        canvas.style.pointerEvents = 'none';
        canvas.style.zIndex = '1';

        this.container.appendChild(canvas);
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');

        this.resize();
        window.addEventListener('resize', () => this.resize());

        this.createParticles();
        this.animate();
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    createParticles() {
        for (let i = 0; i < this.maxParticles; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                size: Math.random() * 3 + 1,
                speedY: Math.random() * 2 + 1,
                speedX: Math.random() * 0.5 - 0.25,
                opacity: Math.random() * 0.5 + 0.2
            });
        }
    }

    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        this.particles.forEach(particle => {
            // Update position
            particle.y += particle.speedY;
            particle.x += particle.speedX;

            // Reset if out of bounds
            if (particle.y > this.canvas.height) {
                particle.y = -10;
                particle.x = Math.random() * this.canvas.width;
            }

            // Draw particle
            this.ctx.beginPath();
            this.ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(6, 182, 212, ${particle.opacity})`;
            this.ctx.fill();
        });

        requestAnimationFrame(() => this.animate());
    }
}

// =========================
// NEON GLOW EFFECT
// =========================
function addNeonGlow(selector) {
    const elements = document.querySelectorAll(selector);
    elements.forEach(el => {
        el.addEventListener('mouseenter', function () {
            this.style.boxShadow = '0 0 20px rgba(6, 182, 212, 0.8), 0 0 40px rgba(6, 182, 212, 0.4)';
            this.style.transform = 'translateY(-2px) scale(1.02)';
        });

        el.addEventListener('mouseleave', function () {
            this.style.boxShadow = '';
            this.style.transform = '';
        });
    });
}

// =========================
// RIPPLE EFFECT
// =========================
function createRipple(event) {
    const button = event.currentTarget;
    const ripple = document.createElement('span');
    const rect = button.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;

    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    ripple.classList.add('ripple-effect');

    button.style.position = 'relative';
    button.style.overflow = 'hidden';
    button.appendChild(ripple);

    setTimeout(() => ripple.remove(), 600);
}

// Add ripple CSS dynamically
const rippleStyle = document.createElement('style');
rippleStyle.textContent = `
    .ripple-effect {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.6);
        transform: scale(0);
        animation: ripple-animation 0.6s ease-out;
        pointer-events: none;
    }
    
    @keyframes ripple-animation {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
`;
document.head.appendChild(rippleStyle);

// =========================
// ANIMATED COUNTER
// =========================
function animateCounter(element, target, duration = 2000) {
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;

    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = Math.round(target);
            clearInterval(timer);
        } else {
            element.textContent = Math.round(current);
        }
    }, 16);
}

// =========================
// STATION STATUS CARDS
// =========================
function createStationCard(station) {
    const statusColors = {
        free: { bg: 'rgba(16, 185, 129, 0.1)', border: '#10b981', glow: 'rgba(16, 185, 129, 0.3)' },
        occupied: { bg: 'rgba(239, 68, 68, 0.1)', border: '#ef4444', glow: 'rgba(239, 68, 68, 0.3)' },
        maintenance: { bg: 'rgba(245, 158, 11, 0.1)', border: '#f59e0b', glow: 'rgba(245, 158, 11, 0.3)' }
    };

    const color = statusColors[station.status] || statusColors.free;

    return `
        <div class="station-card" style="
            background: ${color.bg};
            border: 2px solid ${color.border};
            border-radius: 16px;
            padding: 24px;
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
            cursor: pointer;
        " onmouseenter="this.style.transform='translateY(-8px) scale(1.02)'; this.style.boxShadow='0 20px 40px ${color.glow}'"
           onmouseleave="this.style.transform=''; this.style.boxShadow=''">
            
            <div class="status-indicator" style="
                position: absolute;
                top: 12px;
                right: 12px;
                width: 12px;
                height: 12px;
                background: ${color.border};
                border-radius: 50%;
                animation: pulse-glow 2s infinite;
            "></div>
            
            <h3 style="color: white; font-size: 20px; font-weight: bold; margin-bottom: 8px;">
                ${station.station_name}
            </h3>
            
            <div style="color: ${color.border}; font-size: 14px; text-transform: uppercase; letter-spacing: 2px; font-weight: 600;">
                ${station.status}
            </div>
            
            ${station.current_vehicle ? `
                <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.1);">
                    <div style="color: rgba(255,255,255,0.6); font-size: 12px;">Current Vehicle</div>
                    <div style="color: white; font-weight: 600; margin-top: 4px;">${station.current_vehicle}</div>
                </div>
            ` : ''}
        </div>
    `;
}

// Add pulse animation
const pulseStyle = document.createElement('style');
pulseStyle.textContent = `
    @keyframes pulse-glow {
        0%, 100% {
            box-shadow: 0 0 0 0 currentColor;
            opacity: 1;
        }
        50% {
            box-shadow: 0 0 0 8px transparent;
            opacity: 0.7;
        }
    }
`;
document.head.appendChild(pulseStyle);

// =========================
// LOYALTY STAMP CARD
// =========================
function createLoyaltyCard(totalWashes, freeWashes) {
    const stamps = totalWashes % 5;
    const completedCards = Math.floor(totalWashes / 5);

    let stampHTML = '';
    for (let i = 0; i < 5; i++) {
        const isStamped = i < stamps;
        stampHTML += `
            <div class="stamp-slot" style="
                width: 60px;
                height: 60px;
                border: 2px dashed ${isStamped ? '#10b981' : 'rgba(255,255,255,0.2)'};
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
                transition: all 0.3s ease;
                ${isStamped ? 'background: rgba(16, 185, 129, 0.2); animation: stamp-pop 0.5s ease;' : ''}
            ">
                ${isStamped ? '✓' : ''}
            </div>
        `;
    }

    return `
        <div class="loyalty-card" style="
            background: linear-gradient(135deg, rgba(6, 182, 212, 0.1), rgba(16, 185, 129, 0.1));
            border: 2px solid rgba(6, 182, 212, 0.3);
            border-radius: 20px;
            padding: 32px;
            position: relative;
            overflow: hidden;
        ">
            <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: radial-gradient(circle, rgba(6, 182, 212, 0.1), transparent); border-radius: 50%;"></div>
            
            <h3 style="color: white; font-size: 24px; font-weight: bold; margin-bottom: 8px;">
                Loyalty Rewards
            </h3>
            <p style="color: rgba(255,255,255,0.6); margin-bottom: 24px;">
                Wash 5 times, get 1 FREE!
            </p>
            
            <div style="display: flex; gap: 12px; justify-content: center; margin-bottom: 24px;">
                ${stampHTML}
            </div>
            
            <div style="text-align: center; padding: 16px; background: rgba(0,0,0,0.2); border-radius: 12px;">
                <div style="color: rgba(255,255,255,0.6); font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">
                    Progress
                </div>
                <div style="color: #10b981; font-size: 32px; font-weight: bold; margin-top: 4px;">
                    ${stamps}/5
                </div>
            </div>
            
            ${freeWashes > 0 ? `
                <div style="margin-top: 16px; padding: 12px; background: linear-gradient(90deg, rgba(16, 185, 129, 0.2), rgba(6, 182, 212, 0.2)); border-radius: 12px; text-align: center;">
                    <span style="color: #10b981; font-weight: bold;">🎉 ${freeWashes} Free Wash${freeWashes > 1 ? 'es' : ''} Available!</span>
                </div>
            ` : ''}
        </div>
    `;
}

const stampStyle = document.createElement('style');
stampStyle.textContent = `
    @keyframes stamp-pop {
        0% {
            transform: scale(0) rotate(-45deg);
            opacity: 0;
        }
        50% {
            transform: scale(1.2) rotate(5deg);
        }
        100% {
            transform: scale(1) rotate(0deg);
            opacity: 1;
        }
    }
`;
document.head.appendChild(stampStyle);

// =========================
// SUBSCRIPTION CARD
// =========================
function createSubscriptionCard(subscription) {
    const isActive = subscription && subscription.subscribed;

    return `
        <div class="subscription-card" style="
            background: linear-gradient(135deg, rgba(251, 191, 36, 0.1), rgba(245, 158, 11, 0.1));
            border: 2px solid ${isActive ? '#fbbf24' : 'rgba(251, 191, 36, 0.3)'};
            border-radius: 20px;
            padding: 32px;
            position: relative;
            overflow: hidden;
            ${isActive ? 'animation: golden-glow 3s infinite;' : ''}
        ">
            ${isActive ? `
                <div style="position: absolute; top: 16px; right: 16px; background: #10b981; color: white; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; text-transform: uppercase;">
                    Active
                </div>
            ` : ''}
            
            <div style="position: absolute; top: -50px; left: -50px; width: 200px; height: 200px; background: radial-gradient(circle, rgba(251, 191, 36, 0.1), transparent); border-radius: 50%;"></div>
            
            <div style="position: relative; z-index: 1;">
                <div style="color: #fbbf24; font-size: 14px; text-transform: uppercase; letter-spacing: 2px; font-weight: 600; margin-bottom: 8px;">
                    💎 Premium
                </div>
                
                <h3 style="color: white; font-size: 28px; font-weight: bold; margin-bottom: 8px;">
                    Unlimited Club
                </h3>
                
                <div style="color: rgba(255,255,255,0.6); margin-bottom: 24px;">
                    Unlimited washes for 30 days
                </div>
                
                <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 24px;">
                    <span style="color: #fbbf24; font-size: 48px; font-weight: bold;">₹999</span>
                    <span style="color: rgba(255,255,255,0.6);">/month</span>
                </div>
                
                <div style="margin-bottom: 24px;">
                    <div style="color: rgba(255,255,255,0.8); margin-bottom: 12px; font-weight: 600;">
                        ✨ Benefits:
                    </div>
                    <ul style="color: rgba(255,255,255,0.6); list-style: none; padding: 0;">
                        <li style="margin-bottom: 8px;">✓ Unlimited basic washes</li>
                        <li style="margin-bottom: 8px;">✓ Priority booking</li>
                        <li style="margin-bottom: 8px;">✓ 20% off on add-ons</li>
                        <li style="margin-bottom: 8px;">✓ Free pickup & delivery</li>
                    </ul>
                </div>
                
                ${isActive ? `
                    <div style="padding: 16px; background: rgba(0,0,0,0.3); border-radius: 12px; text-align: center;">
                        <div style="color: rgba(255,255,255,0.6); font-size: 12px; margin-bottom: 4px;">
                            Expires on
                        </div>
                        <div style="color: #fbbf24; font-weight: bold;">
                            ${new Date(subscription.subscription.end_date).toLocaleDateString()}
                        </div>
                    </div>
                ` : `
                    <button onclick="subscribeToUnlimitedClub()" style="
                        width: 100%;
                        padding: 16px;
                        background: linear-gradient(90deg, #fbbf24, #f59e0b);
                        border: none;
                        border-radius: 12px;
                        color: #0f172a;
                        font-weight: bold;
                        font-size: 16px;
                        cursor: pointer;
                        transition: all 0.3s ease;
                    " onmouseenter="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 10px 20px rgba(251, 191, 36, 0.3)'"
                       onmouseleave="this.style.transform=''; this.style.boxShadow=''">
                        Subscribe Now
                    </button>
                `}
            </div>
        </div>
    `;
}

const goldenStyle = document.createElement('style');
goldenStyle.textContent = `
    @keyframes golden-glow {
        0%, 100% {
            box-shadow: 0 0 20px rgba(251, 191, 36, 0.2);
        }
        50% {
            box-shadow: 0 0 40px rgba(251, 191, 36, 0.4);
        }
    }
`;
document.head.appendChild(goldenStyle);

// =========================
// CONFETTI ANIMATION
// =========================
function triggerConfetti() {
    const duration = 3 * 1000;
    const animationEnd = Date.now() + duration;
    const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 9999 };

    function randomInRange(min, max) {
        return Math.random() * (max - min) + min;
    }

    const interval = setInterval(function () {
        const timeLeft = animationEnd - Date.now();

        if (timeLeft <= 0) {
            return clearInterval(interval);
        }

        const particleCount = 50 * (timeLeft / duration);

        // Create confetti particles manually
        for (let i = 0; i < particleCount; i++) {
            createConfettiParticle(randomInRange(0.1, 0.9), randomInRange(0.1, 0.9));
        }
    }, 250);
}

function createConfettiParticle(x, y) {
    const particle = document.createElement('div');
    particle.style.position = 'fixed';
    particle.style.left = (x * window.innerWidth) + 'px';
    particle.style.top = (y * window.innerHeight) + 'px';
    particle.style.width = '10px';
    particle.style.height = '10px';
    particle.style.background = `hsl(${Math.random() * 360}, 100%, 50%)`;
    particle.style.borderRadius = '50%';
    particle.style.pointerEvents = 'none';
    particle.style.zIndex = '9999';
    particle.style.animation = 'confetti-fall 3s ease-out forwards';

    document.body.appendChild(particle);
    setTimeout(() => particle.remove(), 3000);
}

const confettiStyle = document.createElement('style');
confettiStyle.textContent = `
    @keyframes confetti-fall {
        to {
            transform: translateY(100vh) rotate(720deg);
            opacity: 0;
        }
    }
`;
document.head.appendChild(confettiStyle);

// =========================
// SUBSCRIPTION HANDLER
// =========================
async function subscribeToUnlimitedClub() {
    try {
        const response = await fetch('/api/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        const data = await response.json();

        if (data.success) {
            triggerConfetti();
            showNotification('🎉 Welcome to Unlimited Club!', 'success');
            setTimeout(() => location.reload(), 2000);
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        showNotification('Failed to subscribe. Please try again.', 'error');
    }
}

// =========================
// SCROLL REVEAL ANIMATIONS
// =========================
function initScrollReveal() {
    const reveals = document.querySelectorAll('.reveal-scroll');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
            }
        });
    }, { threshold: 0.1 });

    reveals.forEach(reveal => observer.observe(reveal));
}

// =========================
// INITIALIZE ON LOAD
// =========================
document.addEventListener('DOMContentLoaded', function () {
    // Initialize water particles on hero section
    if (document.querySelector('.hero-bg')) {
        // new WaterParticleSystem('hero-bg'); // Uncomment if needed
    }

    // Add neon glow to buttons
    addNeonGlow('.btn-primary');
    addNeonGlow('.btn-outline');

    // Add ripple effect to all buttons
    document.querySelectorAll('button, .btn-primary, .btn-outline').forEach(btn => {
        btn.addEventListener('click', createRipple);
    });

    // Initialize scroll reveal
    initScrollReveal();

    console.log('🎮 Gaming UI Features Loaded!');
});

// Export functions for global use
window.GamingUI = {
    createStationCard,
    createLoyaltyCard,
    createSubscriptionCard,
    animateCounter,
    triggerConfetti,
    subscribeToUnlimitedClub
};
