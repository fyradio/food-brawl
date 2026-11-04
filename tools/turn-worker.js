// 食物大亂鬥 中繼伺服器通行證（Cloudflare Worker）
// 需要兩個變數：TURN_KEY_ID（一般文字）、TURN_KEY_API_TOKEN（加密 Secret）
const ALLOW = ['https://fyradio.github.io'];
export default {
  async fetch(req, env) {
    const origin = req.headers.get('Origin') || '';
    const ok = ALLOW.includes(origin) || origin.startsWith('http://localhost');
    const cors = { 'Access-Control-Allow-Origin': ok ? origin : ALLOW[0], 'Vary': 'Origin', 'Cache-Control': 'no-store' };
    if (req.method === 'OPTIONS') return new Response(null, { headers: { ...cors, 'Access-Control-Allow-Methods': 'GET', 'Access-Control-Max-Age': '86400' } });
    if (!ok) return new Response('forbidden', { status: 403, headers: cors });
    if (!env.TURN_KEY_ID || !env.TURN_KEY_API_TOKEN) return json({ error: 'missing TURN_KEY_ID / TURN_KEY_API_TOKEN' }, 500, cors);
    const r = await fetch(`https://rtc.live.cloudflare.com/v1/turn/keys/${env.TURN_KEY_ID}/credentials/generate-ice-servers`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${env.TURN_KEY_API_TOKEN}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ ttl: 21600 })
    });
    if (!r.ok) return json({ error: 'cloudflare ' + r.status }, 502, cors);
    const j = await r.json();
    // 瀏覽器會擋 53 埠，拿掉免得等逾時
    const iceServers = (j.iceServers || []).map(s => ({ ...s, urls: [].concat(s.urls).filter(u => !/:53(\?|$)/.test(u)) })).filter(s => s.urls.length);
    return json({ iceServers }, 200, cors);
  }
};
function json(o, status, cors) { return new Response(JSON.stringify(o), { status, headers: { ...cors, 'Content-Type': 'application/json' } }); }
