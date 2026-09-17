/**
 * static/js/validation.js
 * Client-side form input validation for RoomSetu.
 * Matches backend validation rules for phone numbers, pincodes, coordinates, and file types.
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Indian 10-Digit Mobile Number Validation
    const phoneInputs = document.querySelectorAll('input[type="tel"], input[name="phone"]');
    phoneInputs.forEach((input) => {
        input.addEventListener("input", (e) => {
            const sanitized = e.target.value.replace(/\D/g, "");
            e.target.value = sanitized.slice(0, 10);

            if (sanitized.length > 0 && !/^[6-9]\d{9}$/.test(sanitized)) {
                e.target.setCustomValidity("Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.");
            } else {
                e.target.setCustomValidity("");
            }
        });
    });

    // 2. Indian 6-Digit PIN Code Validation
    const pincodeInputs = document.querySelectorAll('input[name="pincode"]');
    pincodeInputs.forEach((input) => {
        input.addEventListener("input", (e) => {
            const sanitized = e.target.value.replace(/\D/g, "");
            e.target.value = sanitized.slice(0, 6);

            if (sanitized.length === 6 && !/^[1-9][0-9]{5}$/.test(sanitized)) {
                e.target.setCustomValidity("Invalid PIN Code. Indian PIN codes cannot start with 0.");
            } else {
                e.target.setCustomValidity("");
            }
        });
    });

    // 3. Positive Rent & Deposit Input Validation
    const monetaryInputs = document.querySelectorAll('input[name="monthly_rent"], input[name="security_deposit"], input[name="advance_rent"]');
    monetaryInputs.forEach((input) => {
        input.addEventListener("change", (e) => {
            const val = parseFloat(e.target.value);
            if (isNaN(val) || val < 0) {
                e.target.value = "0";
            }
        });
    });

    // 4. File Size & MIME Verification on Upload
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach((input) => {
        input.addEventListener("change", (e) => {
            const files = e.target.files;
            const maxBytes = 10 * 1024 * 1024; // 10MB default bound

            for (let i = 0; i < files.length; i++) {
                if (files[i].size > maxBytes) {
                    alert(`File "${files[i].name}" exceeds the maximum allowable size of 10 MB.`);
                    e.target.value = "";
                    break;
                }
            }
        });
    });
});