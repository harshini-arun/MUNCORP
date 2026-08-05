// script.js
// Minor client-side UX helpers. The server always re-validates everything,
// so this is convenience only, not a security boundary.

document.addEventListener("DOMContentLoaded", function () {
    var loginForm = document.querySelector('form[action*="login"]');
    if (!loginForm) return;

    loginForm.addEventListener("submit", function (e) {
        var userId = document.getElementById("user_id");
        var password = document.getElementById("password");

        if (!userId.value.trim() || !password.value.trim()) {
            e.preventDefault();
            alert("Please fill in both User ID and Password.");
        }
    });
});
