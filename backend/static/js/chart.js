// ----------------- Socket.IO + Sensor Updates -----------------
const socket = io();
const username = document.body.dataset.username || "{{ username }}"; // optional fallback
socket.emit("join", { username: username });

// Sensor chart
const ctx = document.getElementById('chartContainer').getContext('2d');
const chartData = {
    labels: [],
    datasets: [
        { label: 'Temperature °C', data: [], borderColor: '#ff5733', backgroundColor: 'rgba(255,87,51,0.2)', tension: 0.3 },
        { label: 'Humidity %', data: [], borderColor: '#33c3ff', backgroundColor: 'rgba(51,195,255,0.2)', tension: 0.3 }
    ]
};
const chart = new Chart(ctx, {
    type: 'line',
    data: chartData,
    options: {
        responsive: true,
        plugins: { legend: { display: true } },
        scales: { x: { display: true }, y: { beginAtZero: true } }
    }
});

// Update chart & sensor snapshot
function updateChart(temp, hum) {
    const t = new Date().toLocaleTimeString();
    chartData.labels.push(t);
    chartData.datasets[0].data.push(temp);
    chartData.datasets[1].data.push(hum);

    if (chartData.labels.length > 10) {
        chartData.labels.shift();
        chartData.datasets[0].data.shift();
        chartData.datasets[1].data.shift();
    }
    chart.update();
}

// Display toast messages
function showToast(msg) {
    const box = document.createElement("div");
    box.className = "alert alert-info";
    box.textContent = msg;
    document.getElementById("toast-container").appendChild(box);
    setTimeout(() => box.remove(), 5000);
}

// ----------------- Socket.IO Events -----------------
socket.on("sensor_alerts", function(data) {
    document.getElementById("s_temp").textContent = data.data.temperature;
    document.getElementById("s_humidity").textContent = data.data.humidity;
    document.getElementById("s_smoke").textContent = data.data.smoke;

    const ul = document.getElementById("alerts-list");
    ul.innerHTML = "";
    if (data.alerts.length === 0) ul.innerHTML = "<li>No alerts</li>";
    else data.alerts.forEach(a => {
        const li = document.createElement("li");
        li.textContent = a;
        li.className = "text-danger";
        ul.appendChild(li);
    });

    updateChart(data.data.temperature, data.data.humidity);
});

socket.on("document_status_update", function(data) {
    const el = document.getElementById("status-" + CSS.escape(data.filename));
    if (el) {
        el.textContent = data.status;
        el.className = data.status === "Approved" ? "status-approved" :
                       (data.status === "Rejected" ? "status-rejected" : "status-pending");
    }
    showToast(`Document ${data.filename} → ${data.status}`);
});

socket.on("route_assigned", function(data) {
    showToast(`New route assigned to ${data.driver}`);
    loadAndDrawRoutes();
});

socket.on("routes_changed", function() {
    loadAndDrawRoutes();
});

// ----------------- Notifications -----------------
async function loadNotifications() {
    const res = await fetch("/notifications");
    if (res.ok) {
        const arr = await res.json();
        const container = document.getElementById("notifications");
        container.innerHTML = "";
        if (arr.length === 0) container.innerHTML = "<small>No notifications</small>";
        else arr.forEach(n => {
            const d = document.createElement("div");
            d.className = "mb-1";
            d.innerHTML = `<small>${n.timestamp}: ${n.message}</small>`;
            container.appendChild(d);
        });
    }
}
loadNotifications();
setInterval(loadNotifications, 7000);

// ----------------- Document Status Update -----------------
async function updateStatusWithRemarks(filename, action) {
    const remarks = prompt("Add remarks (optional):");
    const res = await fetch("/update_status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename, action, remarks })
    });
    const data = await res.json();
    if (data.success) showToast(`Updated ${filename} → ${data.status}`);
    else alert(data.error || "Failed to update status");
}

