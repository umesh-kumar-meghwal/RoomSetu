# RoomSetu — All India Student Room Rental Platform

RoomSetu is a student accommodation and room rental platform built for Indian college and university hubs (Kota, Pune, Delhi NCR, Bengaluru, Hyderabad, Dehradun, and beyond). It connects students seeking verified monthly rooms, PGs, flats, and hostels with property owners through admin-moderated KYC, house rule disclosures, and geospatial distance searches.

---

## 1. Key Features

- **Role-Based Access Control (RBAC):** Three distinct roles (`STUDENT`, `LANDLORD`, `ADMIN`) protected by server-side decorators and PostgreSQL Row Level Security (RLS).
- **Landlord KYC Verification:** Property owners must submit proof of ownership (electricity bills, tax receipts, or rent agreements) to an administrative review queue before publishing rooms.
- **Privacy-Conscious Identity Handling:** Identity documents are stored in private Supabase Storage buckets, viewable by administrators only via short-lived (15-minute) signed URLs. Aadhaar numbers are never stored.
- **Interactive Nearby Rooms Radar:** Uses Leaflet.js, OpenStreetMap tiles, and client Geolocation to show vacant rooms within 1, 3, 5, 10, or 25 km of the student's current location.
- **Occupancy Automation:** Rooms marked as `OCCUPIED` are automatically excluded from public searches and map markers.
- **Rental Policies Transparency:** Curfew times, 24-hour entry permissions, guest policies, cooking permissions, notice periods, and rent payment due dates are displayed prior to inquiry submission.
- **Student Watchlist & Inquiries:** Students can bookmark rooms and send direct inquiries to landlords with desired move-in dates.
- **Immutable Security Audit Log:** Administrative approvals, user suspensions, and listing takedowns are permanently recorded in an append-only audit log.

---

## 2. Tech Stack

- **Backend:** Python 3.11+, Flask 3.0.3 (Modular Blueprints)
- **Database:** Supabase PostgreSQL with PostGIS / Haversine distance functions and Row Level Security
- **Authentication & Storage:** Supabase Auth & Supabase Storage
- **Frontend:** HTML5, Jinja2 Templates, Tailwind CSS, Vanilla JavaScript
- **Mapping:** Leaflet.js with OpenStreetMap tiles (no proprietary map API keys required)
- **Security & Validation:** Bleach, Werkzeug, Python-Magic byte sniffing, CSRF token validation

---

## 3. Project Directory Structure