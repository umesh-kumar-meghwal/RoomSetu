/**
 * static/js/property_form.js
 * Assists landlords in populating GPS coordinates using device location.
 */

function fillCoordinatesFromGPS() {
    const latInput = document.querySelector('input[name="latitude"]');
    const lonInput = document.querySelector('input[name="longitude"]');
    const statusMsg = document.getElementById("coord-status-msg");

    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser.");
        return;
    }

    if (statusMsg) {
        statusMsg.innerText = "Detecting current coordinates...";
        statusMsg.classList.remove("hidden");
    }

    navigator.geolocation.getCurrentPosition(
        (position) => {
            if (latInput) latInput.value = position.coords.latitude.toFixed(6);
            if (lonInput) lonInput.value = position.coords.longitude.toFixed(6);
            if (statusMsg) {
                statusMsg.innerText = "Coordinates detected successfully.";
                statusMsg.className = "text-xs text-emerald-600 font-semibold mt-1";
            }
        },
        (error) => {
            if (statusMsg) {
                statusMsg.innerText = "Failed to detect coordinates. Please enter them manually.";
                statusMsg.className = "text-xs text-red-600 font-semibold mt-1";
            }
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
}