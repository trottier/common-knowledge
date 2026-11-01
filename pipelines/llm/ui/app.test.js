import { afterEach, expect, test } from 'bun:test';

class Element {
  children = [];
  events = {};
  value = '';
  disabled = false;
  textContent = '';
  append(...children) { this.children.push(...children); }
  replaceChildren() { this.children = []; }
  addEventListener(name, callback) { this.events[name] = callback; }
  set innerHTML(_) { throw new Error('Untrusted HTML must never be interpreted.'); }
}

const originalFetch = globalThis.fetch;
const originalDocument = globalThis.document;
afterEach(() => {
  globalThis.fetch = originalFetch;
  globalThis.document = originalDocument;
});

let instance = 0;
async function setup(answer, systemText) {
  const elements = Object.fromEntries([
    'conversation', 'language', 'warning', 'grounding', 'start-source', 'question', 'status', 'send', 'cancel', 'reset', 'chat',
  ].map(id => [id, new Element()]));
  elements.language.value = 'en';
  globalThis.document = {
    getElementById: id => elements[id],
    createElement: () => new Element(),
  };
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    if (url === 'settings.json') return Response.json({
      model: 'fixture', warning: 'Experimental fixture', warning_es: 'Prueba experimental',
      max_question_chars: 2000, max_output_tokens: 512, temperature: 0.2,
      context_tokens: 32768, context_reserve_tokens: 4096, message_reserve_tokens: 128,
      grounding: { en: { notice: 'Full START supplied' }, es: { notice: 'Solo títulos' } },
    });
    if (url === 'system-en.txt' || url === 'system-es.txt') return new Response(systemText ?? `START ${url}`);
    if (url !== '/v1/chat/completions') throw new Error(`Unexpected network request: ${url}`);
    return answer(options);
  };
  await import(`./app.js?test=${++instance}`);
  const ask = async question => {
    elements.question.value = question;
    await elements.chat.events.submit({ preventDefault() {} });
  };
  return { elements, calls, ask };
}

test('renders model text safely and retains START with each local request', async () => {
  const malicious = '<img src="https://example.invalid/track" onerror="alert(1)">';
  const { elements, calls, ask } = await setup(() => Response.json({
    choices: [{ message: { content: malicious } }],
  }));
  await ask('Where is START?');
  await ask('Explain that.');
  const requests = calls.filter(call => call.url === '/v1/chat/completions');
  const first = JSON.parse(requests[0].options.body);
  const second = JSON.parse(requests[1].options.body);
  expect(first.messages[0]).toEqual({ role: 'system', content: 'START system-en.txt' });
  expect(second.messages[0]).toEqual(first.messages[0]);
  expect(second.messages.map(message => message.role)).toEqual(['system', 'user', 'assistant', 'user']);
  expect(elements.conversation.children[1].children[1].textContent).toBe(malicious);
  expect(elements.conversation.children[1].children[1].children).toEqual([]);
  expect(requests.every(call => call.options.credentials === 'omit')).toBe(true);
});

test('a failed request does not insert a phantom turn; changing language resets history', async () => {
  let attempt = 0;
  const { elements, calls, ask } = await setup(() => ++attempt === 1
    ? new Response('', { status: 503 })
    : Response.json({ choices: [{ message: { content: 'Read START.' } }] }));
  await ask('First question');
  expect(elements.conversation.children).toEqual([]);
  expect(elements.send.disabled).toBe(false);
  await ask('Retry question');
  const requests = calls.filter(call => call.url === '/v1/chat/completions');
  expect(JSON.parse(requests[1].options.body).messages.map(message => message.content))
    .toEqual(['START system-en.txt', 'Retry question']);
  elements.language.value = 'es';
  elements.language.events.change();
  await ask('Otra pregunta');
  const last = calls.filter(call => call.url === '/v1/chat/completions').at(-1);
  expect(JSON.parse(last.options.body).messages.map(message => message.content))
    .toEqual(['START system-es.txt', 'Otra pregunta']);
  expect(elements.warning.textContent).toBe('Prueba experimental');
  expect(elements.grounding.textContent).toBe('Solo títulos');
  expect(elements['start-source'].href).toBe('start-es.txt');
});

test('bounds UTF-8 conversation bytes before inference without losing the draft question', async () => {
  const { elements, calls, ask } = await setup(() => {
    throw new Error('An oversized request must never reach inference.');
  }, 'é'.repeat(14000));
  const question = 'á'.repeat(300);
  await ask(question);
  expect(calls.some(call => call.url === '/v1/chat/completions')).toBe(false);
  expect(elements.status.textContent).toContain('conversation is too long');
  expect(elements.question.value).toBe(question);
  expect(elements.conversation.children).toEqual([]);
  expect(elements.send.disabled).toBe(false);
});

test('cancel aborts inference and restores the controls without committing a turn', async () => {
  let started;
  const ready = new Promise(resolve => { started = resolve; });
  const { elements, ask } = await setup(options => new Promise((_, reject) => {
    options.signal.addEventListener('abort', () => reject(new DOMException('Canceled', 'AbortError')));
    started();
  }));
  const pending = ask('A question');
  await ready;
  expect(elements.send.disabled).toBe(true);
  elements.cancel.events.click();
  await pending;
  expect(elements.status.textContent).toBe('Canceled.');
  expect(elements.send.disabled).toBe(false);
  expect(elements.cancel.disabled).toBe(true);
  expect(elements.language.disabled).toBe(false);
  expect(elements.conversation.children).toEqual([]);
});
