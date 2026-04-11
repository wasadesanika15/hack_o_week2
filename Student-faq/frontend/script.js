/* ============================================================
   CampusBot — Application Logic
   Handles API integration, UI state, animations, and analytics
   ============================================================ */

(function () {
    'use strict';

    // ── Configuration ──────────────────────────────────────
    const API_URL = 'http://localhost:8000/chat';
    const STAGGER_DELAY = 200;      // ms between staggered reveals
    const LOADER_DURATION = 2000;   // ms before loader fades

    // ── State ──────────────────────────────────────────────
    const state = {
        sessionId: getOrCreateSessionId(),
        questionsAsked: 0,
        intentCounts: {},
        entities: new Set(),
        recentTopics: [],
        currentContext: null,
        chipsVisible: true,
        chipsUsed: false,
        confidenceSum: 0,
        sidebarOpen: false,       // tracks sidebar state on mobile
    };

    // ── DOM References ─────────────────────────────────────
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const dom = {
        loader:           $('#page-loader'),
        app:              $('#app'),
        header:           $('#app-header'),
        sidebar:          $('#sidebar'),
        sidebarOverlay:   $('#sidebar-overlay'),
        sidebarToggle:    $('#sidebar-toggle'),
        chatArea:         $('#chat-area'),
        chatMessages:     $('#chat-messages'),
        chatForm:         $('#chat-form'),
        chatInput:        $('#chat-input'),
        sendBtn:          $('#send-btn'),
        typingIndicator:  $('#typing-indicator'),
        quickReplies:     $('#quick-replies'),
        chipContainer:    $('#chip-container'),
        chipToggle:       $('#chip-show-toggle'),
        contextBanner:    $('#context-banner'),
        contextText:      $('#context-banner-text'),
        contextDismiss:   $('#context-dismiss'),
        infoBtn:          $('#info-btn'),
        infoModal:        $('#info-modal'),
        modalClose:       $('#modal-close'),
        statQuestions:    $('#stat-questions'),
        statTopIntent:   $('#stat-top-intent'),
        statAvgConf:     $('#stat-avg-confidence'),
        statEntities:    $('#stat-entities'),
        recentTopics:    $('#recent-topics'),
        statusIndicator: $('#status-indicator'),
    };

    // ── Session ID ─────────────────────────────────────────
    function getOrCreateSessionId() {
        let id = sessionStorage.getItem('campusbot_session_id');
        if (!id) {
            id = crypto.randomUUID ? crypto.randomUUID() : generateUUID();
            sessionStorage.setItem('campusbot_session_id', id);
        }
        return id;
    }

    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
            const r = (Math.random() * 16) | 0;
            const v = c === 'x' ? r : (r & 0x3) | 0x8;
            return v.toString(16);
        });
    }


    // ── Initialization ─────────────────────────────────────
    function init() {
        // Page load sequence
        setTimeout(() => {
            dom.loader.classList.add('fade-out');
            setTimeout(() => {
                dom.loader.remove();
                revealUI();
            }, 600);
        }, LOADER_DURATION);

        bindEvents();
    }

    function revealUI() {
        const elements = [dom.header, dom.sidebar, dom.chatArea];
        elements.forEach((el, i) => {
            if (!el) return;
            setTimeout(() => {
                el.classList.remove('anim-hidden');
                el.classList.add('anim-visible');
            }, i * STAGGER_DELAY);
        });

        // Auto-focus input after animation
        setTimeout(() => {
            dom.chatInput.focus();
        }, elements.length * STAGGER_DELAY + 300);
    }


    // ── Event Binding ──────────────────────────────────────
    function bindEvents() {
        // Chat form submit
        dom.chatForm.addEventListener('submit', handleSubmit);

        // Input validation for send button state
        dom.chatInput.addEventListener('input', () => {
            dom.sendBtn.disabled = !dom.chatInput.value.trim();
        });

        // Quick reply chips
        dom.chipContainer.addEventListener('click', (e) => {
            const chip = e.target.closest('.chip');
            if (!chip) return;
            const query = chip.dataset.query;
            if (query) {
                dom.chatInput.value = query;
                dom.sendBtn.disabled = false;
                handleSubmit(new Event('submit'));
                hideChips();
            }
        });

        // Chip toggle (re-show chips)
        dom.chipToggle.addEventListener('click', () => {
            showChips();
        });

        // Sidebar toggle
        dom.sidebarToggle.addEventListener('click', toggleSidebar);
        dom.sidebarOverlay.addEventListener('click', closeSidebar);

        // Context banner dismiss
        dom.contextDismiss.addEventListener('click', () => {
            dom.contextBanner.classList.add('hidden');
            state.currentContext = null;
        });

        // Info modal
        dom.infoBtn.addEventListener('click', () => {
            dom.infoModal.classList.remove('hidden');
        });
        dom.modalClose.addEventListener('click', () => {
            dom.infoModal.classList.add('hidden');
        });
        dom.infoModal.addEventListener('click', (e) => {
            if (e.target === dom.infoModal) {
                dom.infoModal.classList.add('hidden');
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                dom.infoModal.classList.add('hidden');
                if (state.sidebarOpen && isMobile()) closeSidebar();
            }
        });
    }


    // ── Chat Submit Handler ────────────────────────────────
    async function handleSubmit(e) {
        e.preventDefault();
        const text = dom.chatInput.value.trim();
        if (!text) return;

        // Append user message
        appendMessage('user', text);
        dom.chatInput.value = '';
        dom.sendBtn.disabled = true;

        // Show typing indicator
        showTyping();
        scrollToBottom();

        try {
            const response = await sendMessage(text);
            hideTyping();
            handleBotResponse(response, text);
        } catch (err) {
            hideTyping();
            appendError(text);
            console.error('CampusBot API Error:', err);
        }

        scrollToBottom();
    }


    // ── API Communication ──────────────────────────────────
    async function sendMessage(message) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 15000); // 15s timeout

        try {
            const res = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    session_id: state.sessionId,
                }),
                signal: controller.signal,
            });

            clearTimeout(timeout);

            if (!res.ok) {
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }

            return await res.json();
        } catch (err) {
            clearTimeout(timeout);
            throw err;
        }
    }


    // ── Bot Response Handler ───────────────────────────────
    function handleBotResponse(data, originalQuery) {
        /* Expected shape:
           {
             answer: string,
             intent: string,
             confidence: number (0-1),
             entities: { key: value, ... },
             suggestions: string[],
             fallback: boolean
           }
        */
        const {
            answer = "I'm not sure how to help with that.",
            intent = 'general',
            confidence = 0.5,
            entities = {},
            suggestions = [],
            fallback = false,
        } = data;

        // Update analytics
        state.questionsAsked++;
        state.intentCounts[intent] = (state.intentCounts[intent] || 0) + 1;
        state.confidenceSum += confidence;

        // Track entities
        Object.entries(entities).forEach(([key, val]) => {
            state.entities.add(`${key}: ${val}`);
        });

        // Update recent topics
        if (intent && intent !== 'general' && intent !== 'unknown') {
            const topicLabel = formatIntentLabel(intent);
            if (!state.recentTopics.includes(topicLabel)) {
                state.recentTopics.unshift(topicLabel);
                if (state.recentTopics.length > 8) state.recentTopics.pop();
            }
        }

        // Show context banner for multi-turn
        if (intent && intent !== 'general' && intent !== 'unknown') {
            state.currentContext = intent;
            showContextBanner(formatIntentLabel(intent));
        }

        // Determine confidence level
        const confidenceLevel = confidence >= 0.75 ? 'high' :
                                confidence >= 0.45 ? 'medium' : 'low';

        // Append bot message
        appendMessage('bot', answer, {
            intent,
            confidenceLevel,
            confidence,
            fallback,
            suggestions,
        });

        // Update sidebar stats
        updateAnalytics();
    }


    // ── Message Rendering ──────────────────────────────────
    function appendMessage(type, text, meta = {}) {
        const wrapper = document.createElement('div');
        wrapper.className = `message ${type}-message`;

        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        if (type === 'bot') {
            wrapper.innerHTML = `
                <div class="message-avatar">
                    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M24 2L6 12V28C6 38 24 46 24 46C24 46 42 38 42 28V12L24 2Z" stroke="#d4a853" stroke-width="2" fill="none"/>
                        <path d="M24 10L14 16V26C14 32 24 38 24 38C24 38 34 32 34 26V16L24 10Z" fill="#d4a853" fill-opacity="0.15"/>
                        <text x="24" y="28" text-anchor="middle" fill="#d4a853" font-size="14" font-family="DM Serif Display, serif">S</text>
                    </svg>
                </div>
                <div class="message-body">
                    <div class="message-card">
                        <p>${escapeHtml(text)}</p>
                        ${meta.fallback ? buildFallbackUI(meta.suggestions) : ''}
                    </div>
                    <div class="message-meta">
                        ${meta.intent ? `<span class="intent-badge">${escapeHtml(formatIntentLabel(meta.intent))}</span>` : ''}
                        ${meta.confidenceLevel ? `
                            <span class="confidence-dot ${meta.confidenceLevel}" title="${Math.round((meta.confidence || 0) * 100)}% confidence"></span>
                            <span class="confidence-label">${meta.confidenceLevel}</span>
                        ` : ''}
                    </div>
                    <span class="message-time">${timeStr}</span>
                </div>
            `;
        } else {
            wrapper.innerHTML = `
                <div class="message-body">
                    <div class="message-card">
                        <p>${escapeHtml(text)}</p>
                    </div>
                    <span class="message-time">${timeStr}</span>
                </div>
            `;
        }

        dom.chatMessages.appendChild(wrapper);
        scrollToBottom();
    }

    function appendError(failedQuery) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message bot-message error-message';

        wrapper.innerHTML = `
            <div class="message-avatar">
                <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M24 2L6 12V28C6 38 24 46 24 46C24 46 42 38 42 28V12L24 2Z" stroke="#d4a853" stroke-width="2" fill="none"/>
                    <path d="M24 10L14 16V26C14 32 24 38 24 38C24 38 34 32 34 26V16L24 10Z" fill="#d4a853" fill-opacity="0.15"/>
                    <text x="24" y="28" text-anchor="middle" fill="#d4a853" font-size="14" font-family="DM Serif Display, serif">S</text>
                </svg>
            </div>
            <div class="message-body">
                <div class="message-card">
                    <div class="error-content">
                        <div class="error-icon">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/><line x1="15" y1="9" x2="9" y2="15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="9" y1="9" x2="15" y2="15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                        </div>
                        <div class="error-text">
                            <strong>Something went wrong</strong>
                            <p>Couldn't reach the server. Please check your connection and try again.</p>
                            <button class="retry-btn" data-query="${escapeAttr(failedQuery)}">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><path d="M1 4v6h6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                                Try again
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Bind retry button
        const retryBtn = wrapper.querySelector('.retry-btn');
        retryBtn.addEventListener('click', () => {
            const query = retryBtn.dataset.query;
            wrapper.remove();
            dom.chatInput.value = query;
            dom.sendBtn.disabled = false;
            handleSubmit(new Event('submit'));
        });

        dom.chatMessages.appendChild(wrapper);
        scrollToBottom();
    }


    // ── Fallback UI Builder ────────────────────────────────
    function buildFallbackUI(suggestions = []) {
        const chips = suggestions.length > 0
            ? suggestions.slice(0, 3).map(s =>
                `<button class="fallback-chip" data-query="${escapeAttr(s)}">${escapeHtml(s)}</button>`
              ).join('')
            : '';

        return `
            <div class="fallback-ui">
                <div class="fallback-label">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" stroke="currentColor" stroke-width="1.5"/><path d="M9 9a3 3 0 0 1 5.12-2.12A3 3 0 0 1 12 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="12" cy="17" r="0.5" fill="currentColor" stroke="currentColor"/></svg>
                    Did you mean…?
                </div>
                ${chips ? `<div class="fallback-suggestions">${chips}</div>` : ''}
                <a href="mailto:advisor@apex.edu.in?subject=Student%20Query%20-%20CampusBot%20Referral" class="fallback-advisor">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M13.73 21a2 2 0 0 1-3.46 0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    Connect to advisor →
                </a>
            </div>
        `;
    }


    // ── Post-render: bind fallback chip clicks ─────────────
    // Use event delegation on chat-messages
    dom.chatMessages.addEventListener('click', (e) => {
        const fallbackChip = e.target.closest('.fallback-chip');
        if (fallbackChip) {
            const query = fallbackChip.dataset.query;
            if (query) {
                dom.chatInput.value = query;
                dom.sendBtn.disabled = false;
                handleSubmit(new Event('submit'));
            }
        }
    });


    // ── Typing Indicator ───────────────────────────────────
    function showTyping() {
        dom.typingIndicator.classList.remove('hidden');
        scrollToBottom();
    }

    function hideTyping() {
        dom.typingIndicator.classList.add('hidden');
    }


    // ── Quick Reply Chips ──────────────────────────────────
    function hideChips() {
        state.chipsVisible = false;
        state.chipsUsed = true;
        dom.chipContainer.classList.add('hidden');
        dom.chipToggle.classList.remove('hidden');
    }

    function showChips() {
        state.chipsVisible = true;
        dom.chipContainer.classList.remove('hidden');
        dom.chipToggle.classList.add('hidden');
    }


    // ── Context Banner ─────────────────────────────────────
    function showContextBanner(topic) {
        dom.contextText.textContent = `Continuing: ${topic} topic`;
        dom.contextBanner.classList.remove('hidden');
    }


    // ── Sidebar ────────────────────────────────────────────
    function isMobile() {
        return window.innerWidth <= 768;
    }

    function toggleSidebar() {
        if (isMobile()) {
            if (state.sidebarOpen) {
                closeSidebar();
            } else {
                openSidebar();
            }
        } else {
            dom.sidebar.classList.toggle('collapsed');
        }
    }

    function openSidebar() {
        state.sidebarOpen = true;
        dom.sidebar.classList.add('mobile-open');
        dom.sidebarOverlay.classList.add('active');
        dom.sidebarOverlay.style.display = 'block';
    }

    function closeSidebar() {
        state.sidebarOpen = false;
        dom.sidebar.classList.remove('mobile-open');
        dom.sidebarOverlay.classList.remove('active');
        setTimeout(() => {
            dom.sidebarOverlay.style.display = 'none';
        }, 300);
    }


    // ── Analytics Update ───────────────────────────────────
    function updateAnalytics() {
        // Questions asked
        dom.statQuestions.textContent = state.questionsAsked;

        // Top intent
        const topIntent = Object.entries(state.intentCounts)
            .sort(([, a], [, b]) => b - a)[0];
        dom.statTopIntent.textContent = topIntent
            ? formatIntentLabel(topIntent[0])
            : '—';

        // Average confidence
        if (state.questionsAsked > 0) {
            const avg = Math.round((state.confidenceSum / state.questionsAsked) * 100);
            dom.statAvgConf.textContent = `${avg}%`;
        }

        // Entities count
        dom.statEntities.textContent = state.entities.size;

        // Recent topics list
        renderRecentTopics();

        // Animate stat values
        animateStatUpdate();
    }

    function renderRecentTopics() {
        if (state.recentTopics.length === 0) {
            dom.recentTopics.innerHTML = '<li class="topic-empty">No topics yet — start chatting!</li>';
            return;
        }
        dom.recentTopics.innerHTML = state.recentTopics
            .map(t => `<li>${escapeHtml(t)}</li>`)
            .join('');
    }

    function animateStatUpdate() {
        const cards = dom.sidebar.querySelectorAll('.analytics-value');
        cards.forEach(card => {
            card.style.transform = 'scale(1.1)';
            card.style.transition = 'transform 0.3s var(--ease-spring)';
            setTimeout(() => {
                card.style.transform = 'scale(1)';
            }, 300);
        });
    }


    // ── Utilities ──────────────────────────────────────────
    function scrollToBottom() {
        requestAnimationFrame(() => {
            dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
        });
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function escapeAttr(str) {
        return str.replace(/&/g, '&amp;')
                  .replace(/"/g, '&quot;')
                  .replace(/'/g, '&#39;')
                  .replace(/</g, '&lt;')
                  .replace(/>/g, '&gt;');
    }

    function formatIntentLabel(intent) {
        if (!intent) return 'General';
        return intent
            .replace(/[_-]/g, ' ')
            .replace(/\b\w/g, c => c.toUpperCase());
    }


    // ── Boot ───────────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
