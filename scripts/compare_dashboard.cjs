// Reproduce the original dashboard defects without executing injected HTML.
const fs = require('node:fs');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');

async function inspect(html) {
  const nodes = new Map();
  const get = id => {
    if (!nodes.has(id)) nodes.set(id, {innerHTML: '', textContent: '', classList: {add() {}, remove() {}}});
    return nodes.get(id);
  };
  const sample = {id: 'safe-id', user_id: '<img src=x onerror=alert(1)>', channel: 'web_chat', status: 'WAITING_FOR_AGENT'};
  const context = {document: {getElementById: get}, localStorage: {}, status: '', setInterval() {},
    fetch: async url => ({json: async () => url.endsWith('/messages') ? [] : [sample]}), sample};
  for (const id of ['rows', 'empty', 'panel', 'title', 'meta', 'msgs']) context[id] = get(id);
  vm.createContext(context);
  vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], context);
  vm.runInContext('renderQueue([sample])', context);
  await vm.runInContext("openConversation('safe-id')", context);
  return {queue_contains_raw_html: get('rows').innerHTML.includes('<img'),
    status_element_updated: get('status').textContent === sample.status};
}

(async () => {
  const before = execFileSync('git', ['show', 'c595d48:dashboard/index.html'], {encoding: 'utf8'});
  const after = fs.readFileSync('dashboard/index.html', 'utf8');
  console.log(JSON.stringify({before: await inspect(before), after: await inspect(after)}, null, 2));
})().catch(error => {console.error(error); process.exitCode = 1;});
