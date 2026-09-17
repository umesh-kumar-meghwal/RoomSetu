/**
 * static/js/map.js
 * Mobile-responsive Leaflet.js Map and Geolocation integration for RoomSetu.
 * Uses OpenStreetMap tiles with complete attribution.
 */

let mapInstance = null;
let userMarker = null;
let roomMarkersGroup = null;
let currentCoords = null;

document.addEventListener("DOMContentLoaded", () => {
    initMap();
    setupEventListeners();
});

/**
 * Initializes Leaflet map centered by default on New Delhi (central fallback).
 */
function initMap() {
    const mapElement = document.getElementById("leaflet-map");
    if (!mapElement) return;

    // Default: New Delhi Coordinates [28.6139, 77.2090]
    mapInstance = L.map("leaflet-map").setView([28.6139, 77.2090], 12);

    // OpenStreetMap Tile Layer
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'
    }).addTo(mapInstance);

    roomMarkersGroup = L.layerGroup().addTo(mapInstance);
}

/**
 * Binds UI controls: Geolocation triggers, radius changes, and filter submissions.
 */
function setupEventListeners() {
    const locateBtn = document.getElementById("btn-locate-me");
    if (locateBtn) {
        locateBtn.addEventListener("click", handleGeolocationRequest);
    }

    const radiusSelect = document.getElementById("radius-select");
    if (radiusSelect) {
        radiusSelect.addEventListener("change", () => {
            if (currentCoords) {
                fetchNearbyRooms(currentCoords.latitude, currentCoords.longitude);
            }
        });
    }

    const filterForm = document.getElementById("map-filter-form");
    if (filterForm) {
        filterForm.addEventListener("submit", (e) => {
            e.preventDefault();
            if (currentCoords) {
                fetchNearbyRooms(currentCoords.latitude, currentCoords.longitude);
            } else {
                updateStatusNotice("Please click 'Use My Current Location' first.", "warning");
            }
        });
    }
}

/**
 * Requests device coordinates via W3C Geolocation API.
 */
function handleGeolocationRequest() {
    const locateBtn = document.getElementById("btn-locate-me");
    if (!navigator.geolocation) {
        updateStatusNotice("Geolocation is not supported by your browser.", "danger");
        return;
    }

    if (locateBtn) {
        locateBtn.disabled = true;
        locateBtn.innerText = "Locating GPS...";
    }

    updateStatusNotice("Detecting your location...", "info");

    navigator.geolocation.getCurrentPosition(
        (position) => {
            currentCoords = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude
            };

            if (locateBtn) {
                locateBtn.disabled = false;
                locateBtn.innerText = "✓ Location Found";
            }

            // Update user marker on map
            updateUserLocationMarker(currentCoords.latitude, currentCoords.longitude);

            // Fetch rooms from Flask backend
            fetchNearbyRooms(currentCoords.latitude, currentCoords.longitude);
        },
        (error) => {
            if (locateBtn) {
                locateBtn.disabled = false;
                locateBtn.innerText = "Use My Current Location";
            }
            handleGeoError(error);
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
}

/**
 * Places or updates the student's location marker with an animated pulse style.
 */
function updateUserLocationMarker(lat, lon) {
    if (!mapInstance) return;

    if (userMarker) {
        mapInstance.removeLayer(userMarker);
    }

    const pulseIcon = L.divIcon({
        className: "custom-user-pin",
        html: `<div class="w-4 h-4 bg-indigo-600 rounded-full border-2 border-white shadow-lg ring-4 ring-indigo-400/50 animate-pulse"></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8]
    });

    userMarker = L.marker([lat, lon], { icon: pulseIcon }).addTo(mapInstance);
    userMarker.bindPopup("<b>You are here</b><br>Searching rooms around this point.").openPopup();

    mapInstance.setView([lat, lon], 14);
}

/**
 * Calls GET /api/nearby-rooms and re-renders pins and side cards.
 */
async function fetchNearbyRooms(lat, lon) {
    const radius = document.getElementById("radius-select")?.value || "5.0";
    const roomType = document.getElementById("filter-room-type")?.value || "";
    const maxRent = document.getElementById("filter-max-rent")?.value || "";

    const url = new URL("/api/nearby-rooms", window.location.origin);
    url.searchParams.append("latitude", lat);
    url.searchParams.append("longitude", lon);
    url.searchParams.append("radius", radius);
    if (roomType) url.searchParams.append("room_type", roomType);
    if (maxRent) url.searchParams.append("max_rent", maxRent);

    updateStatusNotice("Fetching nearby available rooms...", "info");

    try {
        const response = await fetch(url.toString(), {
            headers: { "Accept": "application/json" }
        });
        const data = await response.json();

        if (!response.ok || !data.success) {
            updateStatusNotice(data.error || "Failed to find rooms in this radius.", "danger");
            return;
        }

        renderRoomPins(data.rooms);
        renderRoomCards(data.rooms, data.radius_km);
        updateStatusNotice(`Found ${data.count} available room(s) within ${data.radius_km} km.`, "success");

    } catch (err) {
        console.error("Map query error:", err);
        updateStatusNotice("Network error while loading nearby listings.", "danger");
    }
}

/**
 * Clears old pins and adds markers for each available room.
 */
function renderRoomPins(rooms) {
    if (!roomMarkersGroup) return;
    roomMarkersGroup.clearLayers();

    rooms.forEach((room) => {
        const pin = L.marker([room.latitude, room.longitude]);
        
        const popupContent = `
            <div class="text-xs p-1">
                <p class="font-bold text-slate-900">${room.room_name}</p>
                <p class="text-slate-500">${room.locality}, ${room.city}</p>
                <p class="font-black text-indigo-600 mt-1">₹${room.monthly_rent.toLocaleString('en-IN')}/mo</p>
                <p class="text-[10px] text-emerald-600 font-semibold mt-0.5">📍 ${room.distance_km} km away</p>
                <a href="/properties/rooms/${room.id}" class="mt-2 block text-center px-2 py-1 bg-indigo-600 text-white rounded font-bold hover:bg-indigo-700">View Details</a>
            </div>
        `;
        pin.bindPopup(popupContent);
        roomMarkersGroup.addLayer(pin);
    });
}

/**
 * Renders room cards in the side/bottom list.
 */
function renderRoomCards(rooms, radiusKm) {
    const listContainer = document.getElementById("rooms-results-container");
    if (!listContainer) return;

    if (rooms.length === 0) {
        listContainer.innerHTML = `
            <div class="text-center py-12 bg-white rounded-xl border border-slate-200 p-6">
                <p class="text-sm font-bold text-slate-700">No rooms available nearby</p>
                <p class="text-xs text-slate-500 mt-1">No vacant rooms found within ${radiusKm} km. Try expanding your search radius.</p>
            </div>
        `;
        return;
    }

    listContainer.innerHTML = rooms.map(room => `
        <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:border-indigo-400 transition flex flex-col justify-between">
            <div>
                <div class="flex items-center justify-between">
                    <span class="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-50 text-indigo-700">
                        ${room.room_type.replace('_', ' ')}
                    </span>
                    <span class="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                        ${room.distance_km} km away
                    </span>
                </div>
                <h4 class="font-bold text-slate-900 text-sm mt-2 line-clamp-1">${room.room_name}</h4>
                <p class="text-xs text-slate-500 line-clamp-1">${room.property_title} • ${room.locality}</p>
            </div>

            <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                <div>
                    <span class="text-base font-black text-slate-900">₹${room.monthly_rent.toLocaleString('en-IN')}</span>
                    <span class="text-[10px] text-slate-400">/mo</span>
                </div>
                <a href="/properties/rooms/${room.id}" class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold transition">
                    View Room
                </a>
            </div>
        </div>
    `).join("");
}

/**
 * Handles Geolocation error codes with clear user-facing messages.
 */
function handleGeoError(error) {
    let msg = "Could not retrieve your location.";
    switch (error.code) {
        case error.PERMISSION_DENIED:
            msg = "Location permission denied. Please allow location access in your browser settings.";
            break;
        case error.POSITION_UNAVAILABLE:
            msg = "Location information is unavailable. Please check your network or GPS.";
            break;
        case error.TIMEOUT:
            msg = "Location request timed out. Please try again.";
            break;
    }
    updateStatusNotice(msg, "danger");
}

/**
 * Updates status banner above the map.
 */
function updateStatusNotice(message, type) {
    const banner = document.getElementById("map-status-banner");
    if (!banner) return;

    banner.className = `p-3 rounded-lg text-xs font-semibold mb-4 border ${
        type === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-900' :
        type === 'danger' ? 'bg-red-50 border-red-200 text-red-900' :
        type === 'warning' ? 'bg-amber-50 border-amber-200 text-amber-900' :
        'bg-indigo-50 border-indigo-200 text-indigo-900'
    }`;
    banner.innerText = message;
    banner.classList.remove("hidden");
}