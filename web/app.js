async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function card(device) {
  const badge = device.status === 'online' ? 'success' : 'secondary';
  return `
  <div class="col-md-4">
    <div class="card shadow-sm">
      <div class="card-body">
        <div class="form-check float-end">
          <input class="form-check-input device-select" type="checkbox" value="${device.device_id}">
        </div>
        <h5 class="card-title">${device.device_id}</h5>
        <p class="card-text">Host: ${device.hostname}<br>IP: ${device.local_ip}<br>Usuário: ${device.username}</p>
        <span class="badge text-bg-${badge}">${device.status}</span>
        <button class="btn btn-sm btn-outline-primary ms-2" onclick="requestShot('${device.device_id}')">Capturar screenshot</button>
        <div class="mt-2" id="shot-${device.device_id}"></div>
      </div>
    </div>
  </div>`;
}

function selectedIds() {
  return Array.from(document.querySelectorAll('.device-select:checked')).map((el) => el.value);
}

async function refreshDevices() {
  const devices = await fetchJson('/devices');
  document.getElementById('devices-grid').innerHTML = devices.map(card).join('');
}

async function requestShot(deviceId) {
  await fetchJson('/screenshots/request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify([deviceId]),
  });
  setTimeout(async () => {
    try {
      const payload = await fetchJson(`/screenshots/${deviceId}`);
      document.getElementById(`shot-${deviceId}`).innerHTML = `<img class="img-thumbnail" src="data:image/jpeg;base64,${payload.image_b64}" />`;
    } catch (_err) {
      document.getElementById(`shot-${deviceId}`).innerText = 'Aguardando screenshot...';
    }
  }, 3000);
}

async function applyPolicy(mode) {
  const ids = selectedIds();
  if (!ids.length) return;
  await fetchJson('/policies/apply', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode, device_ids: ids }),
  });
  await refreshDevices();
}

async function applyBlock() { await applyPolicy('block_http_https'); }
async function applyOpen() { await applyPolicy('open'); }

refreshDevices();
setInterval(refreshDevices, 7000);
