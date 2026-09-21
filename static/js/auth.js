/* =====================================================================
   CareerAI - auth.js
   Authentication itself (login/signup/logout, password hashing,
   sessions) is handled entirely by the Flask backend using
   Flask-Login + Flask-Bcrypt — see app/routes.py.

   This file only holds small, purely client-side niceties for the
   auth pages (e.g. confirming before logout). It intentionally does
   NOT store users or passwords in the browser.
===================================================================== */

document.addEventListener('DOMContentLoaded', function () {
    const logoutLinks = document.querySelectorAll('a[href$="/logout"]');

    logoutLinks.forEach(function (link) {
        link.addEventListener('click', function (e) {
            const confirmed = window.confirm('Are you sure you want to log out?');
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });
});
