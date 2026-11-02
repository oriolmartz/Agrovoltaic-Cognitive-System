/* Client dels treballs llargs (/api/jobs): arrencar, seguir el progres, cancel·lar i demanar dies. */

async function http(url, options = {}) {
  const r = await fetch(url, options);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
  return data;
}

const JSON_HEADERS = { 'Content-Type': 'application/json' };

export const startJob = (payload) => http('/api/jobs', { method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(payload) });
export const jobStatus = (id) => http(`/api/jobs/${id}`);
export const jobResult = (id) => http(`/api/jobs/${id}/result`);
export const cancelJob = (id) => http(`/api/jobs/${id}`, { method: 'DELETE' }).catch(() => null);
export const jobDay = (id, date, controller) => http(`/api/jobs/${id}/day?date=${encodeURIComponent(date)}&controller=${encodeURIComponent(controller)}`);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Consulta l'estat fins que el treball acaba; crida onStatus a cada pas. */
export async function waitForJob(id, onStatus, shouldStop = () => false) {
  for (;;) {
    const st = await jobStatus(id);
    onStatus(st);
    if (['done', 'error', 'cancelled'].includes(st.state) || shouldStop()) return st;
    await sleep(700);
  }
}
