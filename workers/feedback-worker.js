const REPO_OWNER = 'HuangJun722';
const REPO_NAME = 'weekly-report';

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'access-control-allow-origin': '*',
      'access-control-allow-methods': 'POST, OPTIONS',
      'access-control-allow-headers': 'content-type',
    },
  });
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

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') return jsonResponse({ ok: true });
    if (request.method !== 'POST') return jsonResponse({ ok: false, error: 'Method not allowed' }, 405);

    if (!env.GITHUB_TOKEN) {
      return jsonResponse({ ok: false, error: 'Feedback backend is not configured' }, 500);
    }

    let payload;
    try {
      payload = await request.json();
    } catch (err) {
      return jsonResponse({ ok: false, error: 'Invalid JSON' }, 400);
    }

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
      return jsonResponse({ ok: false, error: 'Missing title or detail' }, 400);
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
      return jsonResponse({ ok: false, error: data.message || 'Failed to create feedback record' }, 502);
    }

    return jsonResponse({
      ok: true,
      number: data.number,
      id: data.id,
      url: data.html_url,
    });
  },
};
