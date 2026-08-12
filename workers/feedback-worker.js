const REPO_OWNER = 'bxs1024';
const REPO_NAME = 'weekly-report';
const DEFAULT_ALLOWED_ORIGINS = ['https://bxs1024.github.io'];
const MAX_BODY_BYTES = 8192;
const MAX_PER_HOUR = 5;

function parseOrigins(envValue) {
  const raw = String(envValue || '').trim();
  if (!raw) return DEFAULT_ALLOWED_ORIGINS;
  return raw.split(',').map((s) => s.trim()).filter(Boolean);
}

function jsonResponse(body, status = 200, origin = '') {
  const headers = {
    'content-type': 'application/json; charset=utf-8',
    'access-control-allow-methods': 'POST, OPTIONS',
    'access-control-allow-headers': 'content-type',
  };
  if (origin) {
    headers['access-control-allow-origin'] = origin;
    headers['vary'] = 'Origin';
  }
  return new Response(JSON.stringify(body), { status, headers });
}

function allowedOrigin(request, allowed) {
  const origin = request.headers.get('Origin');
  if (origin) return allowed.includes(origin) ? origin : null;
  const referer = request.headers.get('Referer') || '';
  return allowed.some((o) => referer.startsWith(o + '/')) ? '' : null;
}

function cleanText(value, maxLength) {
  return String(value || '').trim().slice(0, maxLength);
}

function buildIssueBody(item) {
  return [
    '## ' + item.title,
    '',
    '- 类型：' + item.type,
    '- 优先级：' + item.priority,
    '- 页面：' + item.page,
    '- 时间：' + item.createdAt,
    item.contact ? '- 联系方式：' + item.contact : '',
    '',
    '### 详情',
    item.detail,
  ].filter(Boolean).join('\n');
}

async function rateLimitCheck(request, env) {
  if (!env.RATE_KV) return null;
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
  const hour = Math.floor(Date.now() / 3600000);
  const key = `feedback:${ip}:${hour}`;
  const count = (parseInt(await env.RATE_KV.get(key), 10) || 0) + 1;
  await env.RATE_KV.put(key, String(count), { expirationTtl: 7200 });
  if (count > MAX_PER_HOUR) {
    return jsonResponse({ ok: false, error: '提交过于频繁，请稍后再试' }, 429, '');
  }
  return null;
}

export default {
  async fetch(request, env) {
    const allowed = parseOrigins(env.ALLOWED_ORIGINS);
    const origin = allowedOrigin(request, allowed);

    if (request.method === 'OPTIONS') {
      return origin === null
        ? new Response(null, { status: 403 })
        : jsonResponse({ ok: true }, 200, origin);
    }
    if (request.method !== 'POST') {
      return jsonResponse({ ok: false, error: 'Method not allowed' }, 405, origin || '');
    }

    // 拒绝非浏览器流量（无 Origin 且无本站 Referer），挡普通脚本滥发
    if (origin === null) {
      return jsonResponse({ ok: false, error: 'Forbidden' }, 403, '');
    }

    if (!env.GITHUB_TOKEN) {
      return jsonResponse({ ok: false, error: 'Feedback backend is not configured' }, 500, origin);
    }

    if (request.headers.get('Content-Length')) {
      const length = parseInt(request.headers.get('Content-Length'), 10);
      if (length > MAX_BODY_BYTES) {
        return jsonResponse({ ok: false, error: 'Payload too large' }, 413, origin);
      }
    }

    let payload;
    try {
      const text = await request.text();
      if (text.length > MAX_BODY_BYTES) {
        return jsonResponse({ ok: false, error: 'Payload too large' }, 413, origin);
      }
      payload = JSON.parse(text);
    } catch (err) {
      return jsonResponse({ ok: false, error: 'Invalid JSON' }, 400, origin);
    }

    const limited = await rateLimitCheck(request, env);
    if (limited) return limited;

    const item = {
      title: cleanText(payload.title, 80),
      detail: cleanText(payload.detail, 4000),
      type: cleanText(payload.type, 40) || '反馈',
      priority: cleanText(payload.priority, 20) || 'P2',
      contact: cleanText(payload.contact, 120),
      page: cleanText(payload.page, 500),
      createdAt: cleanText(payload.createdAt, 80) || new Date().toISOString(),
    };

    if (!item.title || !item.detail) {
      return jsonResponse({ ok: false, error: 'Missing title or detail' }, 400, origin);
    }

    const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/issues`, {
      method: 'POST',
      headers: {
        'authorization': `Bearer ${env.GITHUB_TOKEN}`,
        'accept': 'application/vnd.github+json',
        'content-type': 'application/json',
        'user-agent': 'weekly-report-feedback-worker',
        'x-github-api-version': '2022-11-28',
      },
      body: JSON.stringify({
        title: `[反馈] ${item.title}`,
        body: buildIssueBody(item),
        labels: ['feedback'],
      }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return jsonResponse({ ok: false, error: data.message || 'Failed to create feedback record' }, 502, origin);
    }

    return jsonResponse({
      ok: true,
      number: data.number,
      id: data.id,
      url: data.html_url,
    }, 200, origin);
  },
};
