"""Centralized Head HTML and CSS Style Injector for MathWeave Studio.

Provides 100% offline-compatible typographic styles, local KaTeX integration,
OpenType math font bindings, and custom scrollbar rules without any external CDN
or internet dependencies.
"""

from __future__ import annotations


def get_head_html() -> str:
    """Return consolidated HTML head string for NiceGUI page injection.

    Includes:
    1. Local KaTeX stylesheet and script links.
    2. KaTeX DOM rendering and MutationObserver engine.
    3. Offline OpenType font-face definition for DejaVu Math TeX Gyre.
    4. Clean system-native UI typography without external font downloads.
    5. Math typesetting, scrollbars, and conclusion card styling.
    """
    return """
    <link rel="stylesheet" href="/assets/katex/katex.css">
    <script src="/assets/katex/katex.js"></script>
    <script>
    (function() {
        function renderMathElement(el) {
            if (!window.katex || el.getAttribute('data-rendered') === 'true') return;
            const tex = el.getAttribute('data-tex');
            if (!tex) return;
            const isBlock = el.getAttribute('data-display') === 'block';
            try {
                window.katex.render(tex, el, {
                    displayMode: isBlock,
                    throwOnError: false,
                    output: 'htmlAndMathml',
                    strict: function(errorCode, errorMsg, token) {
                        if (errorCode === 'unknownSymbol' || errorCode === 'unicodeTextInMathMode') {
                            return 'ignore';
                        }
                        return 'warn';
                    }
                });
                el.setAttribute('data-rendered', 'true');
            } catch (e) {
                console.warn('KaTeX render error:', e);
            }
        }

        function renderAllMath(root) {
            if (!window.katex) return;
            const target = root || document.body;
            if (!target) return;
            if (target.matches && target.matches('.math-tex:not([data-rendered="true"])')) {
                renderMathElement(target);
            }
            const elements = target.querySelectorAll('.math-tex:not([data-rendered="true"])');
            elements.forEach(renderMathElement);
        }

        window.renderAllMath = renderAllMath;

        // MutationObserver to automatically render new math elements added dynamically by NiceGUI/Vue
        const observer = new MutationObserver(function(mutations) {
            if (!window.katex) return;
            for (let i = 0; i < mutations.length; i++) {
                const m = mutations[i];
                if (m.type === 'childList') {
                    for (let j = 0; j < m.addedNodes.length; j++) {
                        const node = m.addedNodes[j];
                        if (node.nodeType === 1) { // ELEMENT_NODE
                            renderAllMath(node);
                        }
                    }
                } else if (m.type === 'attributes' && m.target && m.target.nodeType === 1) {
                    m.target.removeAttribute('data-rendered');
                    renderMathElement(m.target);
                }
            }
        });

        document.addEventListener('DOMContentLoaded', function() {
            renderAllMath();
            if (document.body) {
                observer.observe(document.body, {
                    childList: true,
                    subtree: true,
                    attributes: true,
                    attributeFilter: ['data-tex']
                });
            }
        });

        window.addEventListener('load', function() {
            renderAllMath();
        });

        // Bounded startup retries for late-rendered Quasar/Vue components (terminates after 5 cycles)
        let initRetries = 0;
        const maxRetries = 5;
        const initInterval = setInterval(function() {
            initRetries++;
            renderAllMath();
            if (initRetries >= maxRetries) {
                clearInterval(initInterval);
            }
        }, 500);
    })();
    </script>
    <style>
        /* Offline OpenType Math Font */
        @font-face {
            font-family: 'DejaVu Math TeX Gyre';
            src: url('/assets/fonts/DejaVuMathTeXGyre.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
            font-display: swap;
        }

        /* Native System Font Stack - Zero Remote CDN Dependency */
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f8fafc;
            color: #0f172a;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        code, pre, kbd {
            font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
        }

        math {
            font-family: 'DejaVu Math TeX Gyre', 'Noto Sans Math', 'STIX Two Math', 'Latin Modern Math', 'Cambria Math', 'KaTeX_Math', 'TeX Gyre Termes Math', 'TeX Gyre Pagella Math', 'Lucida Bright Math', math, serif !important;
            font-size: 1.15em;
            font-weight: normal !important;
            font-style: normal !important;
            letter-spacing: normal !important;
            line-height: normal;
        }

        .math-container {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            vertical-align: middle;
            overflow: visible !important;
            max-width: 100%;
            line-height: normal;
        }

        .math-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            overflow: visible !important;
            pointer-events: none;
            user-select: none;
            max-width: 100%;
            max-height: 100%;
            line-height: normal;
        }

        .math-icon math, .math-icon .katex {
            font-size: 0.88em;
        }

        math mtable, mtable {
            border-spacing: 0.85em 0.35em !important;
            border-collapse: separate !important;
        }

        math mtd, mtd {
            padding: 0.15em 0.45em !important;
            text-align: center !important;
        }

        html, body {
            max-width: 100vw !important;
        }

        .q-page, .nicegui-content {
            max-width: 100% !important;
            min-width: 0 !important;
        }

        .math-inline {
            display: inline !important;
            vertical-align: -0.08em;
            line-height: inherit;
            white-space: nowrap;
            max-width: 100%;
        }

        .math-inline .katex {
            display: inline !important;
            line-height: inherit !important;
            font-size: 1.05em;
            white-space: nowrap;
        }

        .math-inline math {
            display: inline !important;
            vertical-align: -0.08em;
            line-height: inherit !important;
        }

        .math-block {
            display: flex;
            justify-content: flex-start;
            align-items: center;
            margin: 0.25rem 0;
            overflow-x: auto;
            overflow-y: hidden !important;
            max-width: 100%;
            -webkit-overflow-scrolling: touch;
            padding: 0.35rem 0.5rem;
            scrollbar-width: thin;
            scrollbar-color: #cbd5e1 transparent;
            font-weight: normal !important;
        }

        .math-block .katex-display {
            margin: 0 !important;
            padding: 0 !important;
            text-align: left !important;
        }

        .prose-text {
            overflow-wrap: break-word;
            word-break: normal;
            max-width: 100%;
            min-width: 0;
            overflow-x: auto;
            overflow-y: hidden;
        }

        /* Accessibility: Visible Keyboard Focus Ring */
        button:focus-visible,
        a:focus-visible,
        input:focus-visible,
        [role="button"]:focus-visible,
        .q-btn:focus-visible,
        .q-chip:focus-visible {
            outline: 2px solid #2563eb !important;
            outline-offset: 2px !important;
        }

        /* Prevent unintended flex/grid horizontal overflow across narrow viewports */
        .q-card, .nicegui-card, .nicegui-row, .nicegui-column {
            min-width: 0;
        }

        .q-field {
            min-width: 0;
            max-width: 100%;
        }

        /* Allow long Vietnamese example chips to wrap cleanly instead of clipping */
        .mw-example-chip.q-chip {
            height: auto !important;
            min-height: 28px;
            max-width: 100%;
            white-space: normal !important;
            line-height: 1.35 !important;
            padding-top: 0.25rem !important;
            padding-bottom: 0.25rem !important;
        }

        .mw-example-chip .q-chip__content {
            white-space: normal !important;
            overflow-wrap: anywhere;
        }

        .math-scroll-box {
            overflow-x: auto !important;
            overflow-y: hidden !important;
            max-width: 100%;
            scrollbar-width: thin;
            scrollbar-color: #cbd5e1 transparent;
        }

        /* Responsive typography for mobile (<=640px) and tablet (<=768px) */
        @media (max-width: 640px) {
            .math-block {
                padding: 0.25rem 0.35rem;
                font-size: 0.95em;
            }
            .math-block .katex-display {
                font-size: 0.95em;
            }
            .q-card, .nicegui-card {
                padding: 0.75rem !important;
            }
            .mw-page-shell {
                padding: 0.65rem !important;
            }
        }

        @media (max-width: 768px) {
            .math-block {
                scrollbar-width: thin;
            }
        }

        /* Clean conclusion card formula: eliminate inner boxed borders while preserving outer card */
        .conclusion-formula menclose[notation="box"],
        .conclusion-formula .fbox {
            border: none !important;
        }

        /* Eliminate native browser scrollbar stepper arrows and customize scrollbar track */
        ::-webkit-scrollbar-button,
        *::-webkit-scrollbar-button,
        ::-webkit-scrollbar-button:start,
        ::-webkit-scrollbar-button:end,
        ::-webkit-scrollbar-button:vertical:decrement,
        ::-webkit-scrollbar-button:vertical:increment,
        ::-webkit-scrollbar-button:horizontal:decrement,
        ::-webkit-scrollbar-button:horizontal:increment,
        .math-container::-webkit-scrollbar-button,
        .math-block::-webkit-scrollbar-button,
        math::-webkit-scrollbar-button {
            display: none !important;
            width: 0 !important;
            height: 0 !important;
            visibility: hidden !important;
        }

        /* Ensure MathML formulas have natural line height without vertical clipping,
           while keeping KaTeX's screen-reader-only .katex-mathml strictly clipped to 1px
           so invisible MathML never expands document scrollWidth on narrow viewports. */
        .math-tex math, .math-block math, .math-inline math {
            overflow: visible !important;
        }

        .katex {
            position: relative;
        }

        .katex .katex-mathml {
            overflow: hidden !important;
            max-width: 1px !important;
            max-height: 1px !important;
            left: 0 !important;
            top: 0 !important;
        }

        .katex .katex-mathml math {
            overflow: hidden !important;
        }

        .math-container::-webkit-scrollbar,
        .math-block::-webkit-scrollbar,
        math::-webkit-scrollbar {
            height: 4px;
            width: 4px;
        }

        .math-container::-webkit-scrollbar-thumb,
        .math-block::-webkit-scrollbar-thumb,
        math::-webkit-scrollbar-thumb {
            background-color: #cbd5e1;
            border-radius: 4px;
        }
    </style>
    """
