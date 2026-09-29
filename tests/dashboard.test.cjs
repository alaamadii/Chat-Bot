const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

test('dashboard escapes queue and message data and updates the status element', async () => {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {innerHTML: '', textContent: '', classList: {add() {}, remove() {}}});
    return elements.get(id);
  };
  const attack = '<img src=x onerror=alert(1)>';
  const conversation = {id: 'safe-id', user_id: attack, channel: attack, assigned_agent: attack, status: attack};
  const sandbox = {
    document: {getElementById: element}, localStorage: {}, setInterval() {},
    // window.status is a string, even when there is an element with id=status.
    status: '',
    fetch: async url => ({json: async () => url.endsWith('/messages')
      ? [{role: attack, text: attack}] : [conversation]}),
  };
  for (const id of ['rows', 'empty', 'panel', 'title', 'meta', 'msgs']) sandbox[id] = element(id);
  vm.createContext(sandbox);
  const html = fs.readFileSync(path.join(__dirname, '../dashboard/index.html'), 'utf8');
  vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], sandbox);
  await vm.runInContext("openConversation('safe-id')", sandbox);
  assert.equal(element('status').textContent, attack);
  assert.equal(element('title').textContent, attack);
  for (const id of ['rows', 'msgs']) {
    assert.ok(!element(id).innerHTML.includes('<img'));
    assert.ok(element(id).innerHTML.includes('&lt;img'));
  }
});
