/* =====================================================================
   CareerAI - app.js
   Shared helpers used on every page: toast notifications and a thin
   wrapper around fetch() for talking to the Flask JSON API (/api/*).
===================================================================== */

(function () {

    /* -----------------------------------------------------------
       TOAST NOTIFICATIONS
       window.showToast(title, message, type)
       type: 'success' | 'error' | 'info' | 'warning'
    ----------------------------------------------------------- */

    function ensureToastContainer() {
        let container = document.querySelector('.toast-container-custom');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container-custom';
            document.body.appendChild(container);
        }
        return container;
    }

    function alertClassForType(type) {
        switch (type) {
            case 'success': return 'alert-success';
            case 'error': return 'alert-danger';
            case 'warning': return 'alert-warning';
            default: return 'alert-info';
        }
    }

    window.showToast = function (title, message, type) {
        const container = ensureToastContainer();

        const toast = document.createElement('div');
        toast.className = 'alert ' + alertClassForType(type) + ' shadow-sm mb-2';
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.25s ease';

        toast.innerHTML =
            '<strong>' + title + '</strong>' +
            (message ? '<div class="small mb-0">' + message + '</div>' : '');

        container.appendChild(toast);

        requestAnimationFrame(function () {
            toast.style.opacity = '1';
        });

        setTimeout(function () {
            toast.style.opacity = '0';
            setTimeout(function () {
                toast.remove();
            }, 250);
        }, 3500);
    };

    /* -----------------------------------------------------------
       API HELPER
       window.apiGet(url) / window.apiPost(url, body) / window.apiUpload(url, formData)
       All return a Promise resolving to the parsed JSON body.
       On a non-2xx response, the promise rejects with an Error
       whose .message is the server's error text (if any).
    ----------------------------------------------------------- */

    async function handleResponse(response) {
        let data = null;
        try {
            data = await response.json();
        } catch (e) {
            data = null;
        }

        if (!response.ok) {
            const msg = (data && data.error) ? data.error : ('Request failed (' + response.status + ')');
            throw new Error(msg);
        }

        return data;
    }

    window.apiGet = function (url) {
        return fetch(url, {
            method: 'GET',
            headers: { 'Accept': 'application/json' },
            credentials: 'same-origin'
        }).then(handleResponse);
    };

    window.apiPost = function (url, body) {
        return fetch(url, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify(body || {})
        }).then(handleResponse);
    };

    window.apiUpload = function (url, formData) {
        return fetch(url, {
            method: 'POST',
            headers: { 'Accept': 'application/json' },
            credentials: 'same-origin',
            body: formData
        }).then(handleResponse);
    };

    /* -----------------------------------------------------------
       SMALL SHARED RENDER HELPER
       Builds skill-chip <span> badges consistent with the existing
       design system (badge / badge-pill-custom classes).
    ----------------------------------------------------------- */

    window.renderSkillChips = function (container, skills, variant) {
        if (!container) return;

        variant = variant || 'primary';
        container.innerHTML = '';

        if (!skills || skills.length === 0) {
            container.innerHTML = '<span class="small text-muted">None detected</span>';
            return;
        }

        skills.forEach(function (skill) {
            const span = document.createElement('span');
            span.className = 'badge badge-pill-custom badge-' + variant + '-soft p-2 mr-1 mb-1';
            span.textContent = skill;
            container.appendChild(span);
        });
    };

})();
