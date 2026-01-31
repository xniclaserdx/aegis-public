// Dashboard JavaScript
// Chart initialization
const bytesChart = new Chart(document.getElementById('bytesChart'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'Source Bytes',
                data: [],
                borderColor: 'rgba(0, 0, 0, 1)',
                pointBackgroundColor: [],
                pointRadius: 5,
                backgroundColor: 'rgba(0, 0, 0, 0.2)',
                fill: false
            },
            {
                label: 'Destination Bytes',
                data: [],
                borderColor: 'rgba(0, 0, 255, 1)',
                pointBackgroundColor: [],
                pointRadius: 5,
                backgroundColor: 'rgba(0, 0, 255, 0.6)',
                fill: false
            }
        ]
    },
    options: {
        scales: {
            x: {
                title: {
                    display: true,
                    text: 'Timestamp'
                }
            },
            y: {
                title: {
                    display: true,
                    text: 'Bytes'
                },
                beginAtZero: true
            }
        }
    }
});

const pieChart = new Chart(document.getElementById('pieChart'), {
    type: 'pie',
    data: {
        labels: [],
        datasets: [
            {
                data: [],
                backgroundColor: [
                    'rgba(255, 99, 132, 0.6)',
                    'rgba(54, 162, 235, 0.6)',
                    'rgba(255, 206, 86, 0.6)',
                    'rgba(75, 192, 192, 0.6)',
                    'rgba(153, 102, 255, 0.6)',
                    'rgba(255, 159, 64, 0.6)'
                ],
                borderColor: 'rgba(255, 255, 255, 1)',
                borderWidth: 1
            }
        ]
    },
    options: {
        responsive: true,
        plugins: {
            legend: {
                position: 'top'
            },
            title: {
                display: true,
                text: 'Predicted Labels Distribution'
            }
        }
    }
});

// Socket.IO connection and event handlers
const socket = io();
const labelCounts = {};

socket.on('update_data', (data) => {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('logged_in='));
    let cookieValue = cookie ? cookie.split('=')[1] : '';
    const cookieHash = CryptoJS.SHA256((encodeURIComponent(cookieValue))).toString(CryptoJS.enc.Hex);
    const isVerified = data.uuid === cookieHash;
    if (!isVerified) {
        return;
    }
    // Update line chart
    bytesChart.data.labels.push(data.timestamp);
    bytesChart.data.datasets[0].data.push(data.src_bytes);
    bytesChart.data.datasets[1].data.push(data.dst_bytes);

    // Set point color based on predicted_label
    const color = data.predicted_label === 'normal.' ? 'rgba(0, 255, 0, 1)' : 'rgba(255, 0, 0, 1)';
    bytesChart.data.datasets[0].pointBackgroundColor.push(color);
    bytesChart.data.datasets[1].pointBackgroundColor.push(color);

    if (bytesChart.data.labels.length > 30) {
        bytesChart.data.labels.shift();
        bytesChart.data.datasets[0].data.shift();
        bytesChart.data.datasets[1].data.shift();
        bytesChart.data.datasets[0].pointBackgroundColor.shift();
        bytesChart.data.datasets[1].pointBackgroundColor.shift();
    }
    bytesChart.update();

    // Update pie chart
    labelCounts[data.predicted_label] = (labelCounts[data.predicted_label] || 0) + 1;
    pieChart.data.labels = Object.keys(labelCounts);
    pieChart.data.datasets[0].data = Object.values(labelCounts);
    pieChart.update();

    // Update data table
    const newRow = document.createElement('tr');
    newRow.innerHTML = `
        <td>${data.timestamp}</td>
        <td>${data.duration}</td>
        <td>${data.protocol_type}</td>
        <td>${data.service}</td>
        <td>${data.flag}</td>
        <td>${data.src_bytes}</td>
        <td>${data.dst_bytes}</td>
        <td>${data.logged_in}</td>
        <td>${data.count}</td>
        <td>${data.srv_count}</td>
        <td>${data.same_srv_rate}</td>
        <td>${data.diff_srv_rate}</td>
        <td>${data.srv_diff_host_rate}</td>
        <td>${data.dst_host_count}</td>
        <td>${data.dst_host_srv_count}</td>
        <td>${data.predicted_label}</td>
        <td>${data.real_label}</td>`;
    document.getElementById('dataTableBody').insertBefore(newRow, document.getElementById('dataTableBody').firstChild);
    if (document.getElementById('dataTableBody').rows.length > 5) {
        document.getElementById('dataTableBody').deleteRow(5);
    }

    // Update traffic counts
    document.getElementById('goodTrafficCount').innerText = data.normal_count;
    document.getElementById('badTrafficCount').innerText = data.bad_count;
    document.getElementById('badTrafficPercentage').innerText = `${data.bad_traffic_percentage.toFixed(2)}%`;
});

// Button event listeners
document.querySelector('.sidebar button:nth-child(3)').addEventListener('click', () => {
    socket.emit('start_simulation');
});

document.querySelector('.sidebar button:nth-child(4)').addEventListener('click', () => {
    socket.emit('stop_simulation');
});

document.querySelector('.sidebar button:nth-child(2)').addEventListener('click', () => {
    socket.emit('reset_data');
    location.reload();
});

// Dark Mode Toggle
// Set dark mode based on browser preference on first load
if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.body.classList.add('dark');
}
document.getElementById('toggleDarkMode').addEventListener('click', () => {
    document.body.classList.toggle('dark');
});

// Fetch user info
fetch('/user_info')
    .then(response => response.json())
    .then(data => {
        document.getElementById('userEmail').innerText = data.email;
        document.getElementById('userRole').innerText = `Role: ${data.role}`;
    });
