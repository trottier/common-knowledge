const byId = id => document.getElementById(id);
let settings;
let messages = [];
let controller;

function show(role, text) {
  const article = document.createElement('article');
  const label = document.createElement('strong');
  const content = document.createElement('p');
  label.textContent = role === 'user' ? 'You' : 'Experimental local LLM';
  content.textContent = text;
  article.append(label, content);
  byId('conversation').append(article);
}

function reset() {
  if (controller) controller.abort();
  messages = [];
  byId('conversation').replaceChildren();
  byId('warning').textContent = byId('language').value === 'es' ? settings.warning_es : settings.warning;
  const language = byId('language').value;
  byId('grounding').textContent = settings.grounding[language].notice;
  byId('start-source').href = `start-${language}.txt`;
  byId('start-source').textContent = language === 'es' ? 'Leer el texto de START' : 'Read START text';
}

async function ask(event) {
  event.preventDefault();
  const question = byId('question').value.trim();
  if (!question || controller) return;
  if (question.length > settings.max_question_chars) {
    byId('status').textContent = 'Please shorten the question.';
    return;
  }
  controller = new AbortController();
  byId('send').disabled = true;
  byId('cancel').disabled = false;
  byId('language').disabled = true;
  byId('reset').disabled = true;
  byId('status').textContent = 'Reading the local instructions…';
  try {
    const source = await fetch(`system-${byId('language').value}.txt`, {
      cache: 'no-store', signal: controller.signal,
    });
    if (!source.ok) throw new Error('The local instructions could not be opened.');
    const system = await source.text();
    const pending = [...messages, { role: 'user', content: question }];
    const request = [{ role: 'system', content: system }, ...pending];
    const inputBytes = request.reduce((total, message) =>
      total + new TextEncoder().encode(message.content).length, 0);
    if (inputBytes + request.length * settings.message_reserve_tokens + settings.max_output_tokens + settings.context_reserve_tokens > settings.context_tokens) {
      throw new Error('This conversation is too long. Start a new conversation or shorten the question.');
    }
    byId('status').textContent = 'Working locally…';
    const response = await fetch('/v1/chat/completions', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      signal: controller.signal, credentials: 'omit', cache: 'no-store',
      body: JSON.stringify({ model: settings.model, messages: request,
        stream: false, max_tokens: settings.max_output_tokens, temperature: settings.temperature }),
    });
    if (!response.ok) throw new Error('The answer could not be generated. Start a new conversation if it is too long.');
    const data = await response.json();
    const answer = data.choices?.[0]?.message?.content;
    if (typeof answer !== 'string' || !answer.trim()) throw new Error('The model returned no answer.');
    messages = [...pending, { role: 'assistant', content: answer }];
    show('user', question);
    show('assistant', answer);
    byId('question').value = '';
    byId('status').textContent = 'Read the START section before acting.';
  } catch (error) {
    byId('status').textContent = error.name === 'AbortError' ? 'Canceled.' : error.message;
  } finally {
    controller = undefined;
    byId('send').disabled = false;
    byId('cancel').disabled = true;
    byId('language').disabled = false;
    byId('reset').disabled = false;
  }
}

try {
  const response = await fetch('settings.json', { cache: 'no-store' });
  if (!response.ok) throw new Error('Settings could not be opened.');
  settings = await response.json();
  byId('question').maxLength = settings.max_question_chars;
  reset();
  byId('send').disabled = false;
  byId('status').textContent = 'Ready. Nothing is sent to the internet.';
  byId('chat').addEventListener('submit', ask);
  byId('reset').addEventListener('click', reset);
  byId('language').addEventListener('change', reset);
  byId('cancel').addEventListener('click', () => controller?.abort());
} catch (error) {
  byId('status').textContent = error.message;
}
