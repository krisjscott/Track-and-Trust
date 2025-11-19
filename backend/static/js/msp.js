// ----------------- Leaflet Map -----------------
let map = L.map('map').setView([21.1458, 79.0882], 5); // India-ish center
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(map);

const drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);

const drawControl = new L.Control.Draw({
    draw: {
        polygon: false, rectangle: false, circle: false, marker: false, circlemarker: false,
        polyline: { shapeOptions: { color: '#ff6600', weight: 4 } }
    },
    edit: { featureGroup: drawnItems, edit: true, remove: true }
});
map.addControl(drawControl);

let currentRouteCoords = null;
let routeLayers = [];
let driverMarkers = {};

// Draw / edit / delete
map.on(L.Draw.Event.CREATED, function(e) {
    const layer = e.layer;
    drawnItems.clearLayers();
    drawnItems.addLayer(layer);
    if (layer instanceof L.Polyline) currentRouteCoords = layer.getLatLngs().map(ll => [ll.lat, ll.lng]);
});
map.on('draw:edited', function(e) {
    e.layers.eachLayer(layer => {
        if (layer instanceof L.Polyline) currentRouteCoords = layer.getLatLngs().map(ll => [ll.lat, ll.lng]);
    });
});
map.on('draw:deleted', function(){ currentRouteCoords = null; });

// ----------------- Fetch & Draw Routes -----------------
async function loadAndDrawRoutes() {
    try {
        const res = await fetch("/routes_api");
        if (!res.ok) return;
        const arr = await res.json();

        // clear previous
        routeLayers.forEach(l => map.removeLayer(l));
        Object.values(driverMarkers).forEach(m => map.removeLayer(m));
        routeLayers = []; driverMarkers = {};

        arr.forEach(r => {
            if (r.route && r.route.length > 0) {
                const coords = r.route.map(p => Array.isArray(p) ? [p[0], p[1]] : [p.lat, p.lng || p.longitude]);
                const poly = L.polyline(coords, { color: '#3388ff', weight: 4, opacity:0.7 }).addTo(map);
                routeLayers.push(poly);

                // driver marker
                const start = coords[0];
                if (start) {
                    const marker = L.marker(start).addTo(map).bindPopup(`<b>${r.driver_username || 'driver'}</b><br/>Assigned: ${r.assigned_on || ''}`);
                    driverMarkers[r.driver_username || r.id] = marker;
                }
            }
        });
    } catch(e){ console.error(e); }
}

// Initial load & auto-refresh
loadAndDrawRoutes();
setInterval(loadAndDrawRoutes, 15000);

// ----------------- Draw Mode -----------------
document.getElementById('start-draw')?.addEventListener('click', () => {
    new L.Draw.Polyline(map, drawControl.options.draw.polyline).enable();
});

// ----------------- Load Driver List -----------------
async function loadDriverList() {
    try {
        const res = await fetch('/drivers_list');
        if (!res.ok) return;
        const sel = document.getElementById('driver-select');
        if (!sel) return;
        const arr = await res.json();
        sel.innerHTML = '<option value="">Select driver...</option>';
        arr.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.username;
            opt.textContent = d.username + (d.email ? ' — ' + d.email : '');
            sel.appendChild(opt);
        });
    } catch(e){ console.error(e); }
}
loadDriverList();

// ----------------- Assign Route -----------------
document.getElementById('assign-route-btn')?.addEventListener('click', async () => {
    const driver = document.getElementById('driver-select')?.value;
    if (!driver) { alert("Select a driver"); return; }
    if (!currentRouteCoords || currentRouteCoords.length < 2) { alert("Draw a route first"); return; }

    try {
        const res = await fetch('/assign_route', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ driver, route: currentRouteCoords })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Route assigned to " + driver);
            drawnItems.clearLayers();
            currentRouteCoords = null;
            loadAndDrawRoutes();
        } else alert(data.error || "Failed to assign route");
    } catch(e){ console.error(e); alert("Network error"); }
});
