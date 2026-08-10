(function () {
    'use strict';

    var timer = null;

    function initRealtimeSearch() {
        document.addEventListener('input', function (e) {
            var input = e.target;
            if (!input.matches('.auto-realtime-search, input[name="q"], input[type="search"]')) return;
            if (input.id === 'pos-search-input') return; // POS maneja su filtrado reactivo en pos.js

            var form = input.closest('form');
            if (!form) return;

            clearTimeout(timer);
            timer = setTimeout(function () {
                if (typeof window.sessionStorage !== 'undefined') {
                    window.sessionStorage.setItem('realtime_search_focus', input.name || input.id);
                }
                form.submit();
            }, 350);
        });

        // Restaura el foco y el cursor al final de la casilla tras el envío en tiempo real
        if (typeof window.sessionStorage !== 'undefined') {
            var focusTargetName = window.sessionStorage.getItem('realtime_search_focus');
            if (focusTargetName) {
                window.sessionStorage.removeItem('realtime_search_focus');
                var targetInput = document.querySelector('[name="' + focusTargetName + '"], #' + focusTargetName);
                if (targetInput) {
                    targetInput.focus();
                    var valLen = targetInput.value.length;
                    try {
                        targetInput.setSelectionRange(valLen, valLen);
                    } catch (err) {}
                }
            }
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initRealtimeSearch);
    } else {
        initRealtimeSearch();
    }
})();
