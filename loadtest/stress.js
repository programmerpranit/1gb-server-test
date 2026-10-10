// k6 stress test — identical for every implementation (see CLAUDE.md "Load test protocol").
//
//   k6 run -e BASE_URL=http://<ip>:3000 -e VUS=500 -e OUT_DIR=results/<tag>/vus-500 loadtest/stress.js
//
// Profile: ramp 0 -> VUS over RAMP_S seconds, then hold VUS for HOLD_S seconds.
// Each VU is one "user" (fixed X-User-Id) doing a weighted mix of actions with think time.
// Requests are tagged phase=ramp|steady so steady-state numbers can be reported separately.

import http from 'k6/http';
import { check, sleep } from 'k6';
import exec from 'k6/execution';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.2/index.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';
const VUS = parseInt(__ENV.VUS || '100', 10);
const RAMP_S = parseInt(__ENV.RAMP_S || '60', 10);
const HOLD_S = parseInt(__ENV.HOLD_S || '60', 10);
const OUT_DIR = __ENV.OUT_DIR || '.';
const THINK_MIN = parseFloat(__ENV.THINK_MIN || '1');
const THINK_MAX = parseFloat(__ENV.THINK_MAX || '3');
const PAGE_SIZE = 20;
const TIMEOUT = __ENV.TIMEOUT || '10s';

// From data/meta.json (scripts/xlsx_to_csv.py). Users 1..AUTHOR_COUNT have at least one post.
const USER_COUNT = parseInt(__ENV.USER_COUNT || '99260', 10);
const AUTHOR_COUNT = parseInt(__ENV.AUTHOR_COUNT || '33213', 10);
const POST_COUNT = parseInt(__ENV.POST_COUNT || '100000', 10);

// Action mix (weights sum to 100). Read-heavy like a real social feed: ~77% reads, ~23% writes.
const ACTIONS = [
  ['globalFeed', 40],
  ['viewPost', 15],
  ['userPosts', 15],
  ['myPosts', 7],
  ['like', 12],
  ['unlike', 2],
  ['comment', 4],
  ['createPost', 5],
];

export const options = {
  scenarios: {
    users: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: `${RAMP_S}s`, target: VUS },
        { duration: `${HOLD_S}s`, target: VUS },
      ],
      gracefulRampDown: '5s',
      gracefulStop: '5s',
    },
  },
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
  // Thresholds double as "please track these sub-metrics" so handleSummary sees them.
  // They are deliberately loose: a run is never aborted, results are judged afterwards.
  thresholds: {
    http_req_failed: ['rate<1'],
    'http_req_failed{phase:steady}': ['rate<1'],
    'http_req_duration{phase:steady}': ['max>=0'],
    'http_req_duration{phase:ramp}': ['max>=0'],
    'http_reqs{phase:steady}': ['count>=0'],
    'http_reqs{phase:ramp}': ['count>=0'],
    ...Object.fromEntries(
      ['GET /posts', 'GET /posts/:id', 'GET /users/:id/posts', 'GET /me/posts',
       'POST /posts/:id/like', 'DELETE /posts/:id/like', 'POST /posts/:id/comments', 'POST /posts']
        .map((n) => [`http_req_duration{name:${n}}`, ['max>=0']]),
    ),
  },
};

const TOTAL_WEIGHT = ACTIONS.reduce((s, [, w]) => s + w, 0);
const randInt = (min, max) => min + Math.floor(Math.random() * (max - min + 1));
const pickAction = () => {
  let r = Math.random() * TOTAL_WEIGHT;
  for (const [name, w] of ACTIONS) { if ((r -= w) < 0) return name; }
  return ACTIONS[0][0];
};

// Per-VU state (each VU is a separate JS runtime).
let me = null;          // this VU's user id
let seenPosts = [];     // ids from the last feed page, so likes/comments hit posts the user "saw"
let liked = [];

function params(name, extraHeaders = {}) {
  return {
    headers: { 'X-User-Id': String(me), 'Content-Type': 'application/json', ...extraHeaders },
    tags: { name },
    timeout: TIMEOUT,
  };
}

function ok(res, name) {
  return check(res, { [`${name} 2xx`]: (r) => r.status >= 200 && r.status < 300 });
}

function rememberPosts(res) {
  if (res.status !== 200) return;
  try {
    const body = res.json();
    if (Array.isArray(body.posts) && body.posts.length) seenPosts = body.posts.map((p) => p.id);
    return body.next_before;
  } catch (_) { return undefined; }
}

function somePost() {
  return seenPosts.length && Math.random() < 0.8
    ? seenPosts[randInt(0, seenPosts.length - 1)]
    : randInt(1, POST_COUNT);
}

const actions = {
  globalFeed() {
    let res = http.get(`${BASE_URL}/posts?limit=${PAGE_SIZE}`, params('GET /posts'));
    ok(res, 'GET /posts');
    const next = rememberPosts(res);
    if (next && Math.random() < 0.3) {          // scroll one more page
      sleep(0.5);
      res = http.get(`${BASE_URL}/posts?limit=${PAGE_SIZE}&before=${next}`, params('GET /posts'));
      ok(res, 'GET /posts');
      rememberPosts(res);
    }
  },
  viewPost() {
    const res = http.get(`${BASE_URL}/posts/${somePost()}`, params('GET /posts/:id'));
    ok(res, 'GET /posts/:id');
  },
  userPosts() {
    const uid = randInt(1, AUTHOR_COUNT);
    const res = http.get(`${BASE_URL}/users/${uid}/posts?limit=${PAGE_SIZE}`, params('GET /users/:id/posts'));
    ok(res, 'GET /users/:id/posts');
    rememberPosts(res);
  },
  myPosts() {
    const res = http.get(`${BASE_URL}/me/posts?limit=${PAGE_SIZE}`, params('GET /me/posts'));
    ok(res, 'GET /me/posts');
  },
  like() {
    const pid = somePost();
    const res = http.post(`${BASE_URL}/posts/${pid}/like`, null, params('POST /posts/:id/like'));
    if (ok(res, 'POST /posts/:id/like')) liked.push(pid);
  },
  unlike() {
    if (!liked.length) return actions.like();
    const pid = liked.pop();
    const res = http.del(`${BASE_URL}/posts/${pid}/like`, null, params('DELETE /posts/:id/like'));
    ok(res, 'DELETE /posts/:id/like');
  },
  comment() {
    const pid = somePost();
    const body = JSON.stringify({ text: `Load test comment from user ${me} at ${Date.now()}` });
    const res = http.post(`${BASE_URL}/posts/${pid}/comments`, body, params('POST /posts/:id/comments'));
    ok(res, 'POST /posts/:id/comments');
  },
  createPost() {
    const body = JSON.stringify({
      text: `Load test post from user ${me} at ${new Date().toISOString()} #benchmark`,
      is_public: Math.random() >= 0.1,
    });
    const res = http.post(`${BASE_URL}/posts`, body, params('POST /posts'));
    ok(res, 'POST /posts');
  },
};

export function setup() {
  const res = http.get(`${BASE_URL}/health`, { timeout: '5s' });
  if (res.status !== 200) throw new Error(`health check failed: ${res.status} ${res.body}`);
  return { startedAt: Date.now() };
}

export default function (data) {
  if (me === null) me = randInt(1, USER_COUNT);
  exec.vu.metrics.tags.phase = (Date.now() - data.startedAt) < RAMP_S * 1000 ? 'ramp' : 'steady';

  actions[pickAction()]();
  sleep(THINK_MIN + Math.random() * (THINK_MAX - THINK_MIN));
}

export function handleSummary(data) {
  return {
    [`${OUT_DIR}/k6_summary.json`]: JSON.stringify(data, null, 2),
    // Exact test start (epoch ms) so summarize.py can align server samples with the steady phase.
    [`${OUT_DIR}/k6_start.json`]: JSON.stringify({ started_at_ms: (data.setup_data || {}).startedAt || null }),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}
