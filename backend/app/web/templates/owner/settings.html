{% extends "owner/_layout.html" %}
{% set active = "settings" %}
{% block title %}Настройки — AutoService AI{% endblock %}
{% block content %}
<h1 class="text-2xl font-bold text-gray-900 mb-6">Настройки</h1>

<div class="grid gap-6 max-w-2xl">
  <!-- Company info -->
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
    <h2 class="font-semibold text-gray-900 mb-4">Информация о сервисе</h2>
    <div class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Название</label>
        <input id="compName" type="text" value="{{ company.name if company else '' }}" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Телефон</label>
        <input id="compPhone" type="tel" value="{{ company.phone or '' }}" placeholder="+7 (999) 123-45-67" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Адрес</label>
        <input id="compAddress" type="text" value="{{ company.address or '' }}" placeholder="г. Москва, ул. Примерная, 1" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Описание сервиса</label>
        <textarea id="compDesc" rows="3" placeholder="Профессиональный автосервис..." class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none">{{ company.description or '' }}</textarea>
      </div>
      <button onclick="saveCompany()" class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-6 py-2 rounded-lg transition-colors">Сохранить</button>
    </div>
  </div>

  <!-- Telegram bot -->
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
    <h2 class="font-semibold text-gray-900 mb-1">Telegram бот</h2>
    <p class="text-sm text-gray-500 mb-4">Создайте бота через <a href="https://t.me/BotFather" target="_blank" class="text-blue-600 hover:underline">@BotFather</a> и вставьте токен сюда.</p>
    {% if company and company.telegram_bot_token %}
    <div class="flex items-center gap-2 bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
      <span class="text-green-600">✅</span>
      <span class="text-sm text-green-800 font-medium">Бот подключён</span>
      <span class="text-xs text-green-600 ml-auto font-mono">{{ company.telegram_bot_token[:10] }}...</span>
    </div>
    {% endif %}
    <div class="flex gap-3">
      <input id="botToken" type="text" placeholder="1234567890:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono">
      <button onclick="saveBotToken()" class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors whitespace-nowrap">Сохранить токен</button>
    </div>
    <div class="mt-3">
      <label class="block text-sm font-medium text-gray-700 mb-1">Ваш Telegram ID для уведомлений</label>
      <div class="flex gap-3">
        <input id="chatId" type="text" value="{{ company.telegram_chat_id or '' }}" placeholder="Узнайте через @userinfobot" class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
        <button onclick="saveChatId()" class="bg-gray-600 hover:bg-gray-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">Сохранить</button>
      </div>
    </div>
  </div>

  <!-- Working hours -->
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
    <h2 class="font-semibold text-gray-900 mb-4">Рабочие часы</h2>
    <div class="space-y-3" id="workingHoursForm">
      {% set day_names = ['Понедельник','Вторник','Среда','Четверг','Пятница','Суббота','Воскресенье'] %}
      {% for i in range(7) %}
      {% set wh = working_hours.get(i) %}
      <div class="flex items-center gap-3">
        <span class="w-28 text-sm text-gray-700 font-medium">{{ day_names[i] }}</span>
        <label class="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" class="wh-active rounded" data-day="{{ i }}"
            {% if wh and wh.is_working %}checked{% endif %} onchange="toggleDayInputs({{ i }}, this.checked)">
          <span class="text-xs text-gray-500">Рабочий</span>
        </label>
        <div class="flex items-center gap-2 day-times-{{ i }} {% if not wh or not wh.is_working %}opacity-30 pointer-events-none{% endif %}">
          <input type="time" class="wh-open border border-gray-300 rounded px-2 py-1 text-xs" data-day="{{ i }}"
            value="{{ wh.open_time.strftime('%H:%M') if wh and wh.open_time else '09:00' }}">
          <span class="text-gray-400 text-xs">—</span>
          <input type="time" class="wh-close border border-gray-300 rounded px-2 py-1 text-xs" data-day="{{ i }}"
            value="{{ wh.close_time.strftime('%H:%M') if wh and wh.close_time else '19:00' }}">
        </div>
      </div>
      {% endfor %}
    </div>
    <button onclick="saveWorkingHours()" class="mt-4 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-6 py-2 rounded-lg transition-colors">Сохранить расписание</button>
  </div>

  <!-- AI Prompt -->
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
    <h2 class="font-semibold text-gray-900 mb-1">Настройка ИИ-ассистента</h2>
    <p class="text-sm text-gray-500 mb-4">Дополнительные инструкции для AI. Например: особенности сервиса, приветствие.</p>
    <textarea id="aiPrompt" rows="4" placeholder="Наш сервис специализируется на японских автомобилях. Всегда предлагай записаться на диагностику..." class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none">{{ company.ai_system_prompt or '' }}</textarea>
    <button onclick="saveAiPrompt()" class="mt-3 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium px-6 py-2 rounded-lg transition-colors">Сохранить</button>
  </div>
</div>

<div id="toast" class="hidden fixed bottom-4 right-4 bg-green-600 text-white px-4 py-3 rounded-xl shadow-lg text-sm font-medium z-50">✓ Сохранено</div>

<script>
const token = () => document.cookie.split(';').find(c=>c.trim().startsWith('access_token='))?.split('=')[1];
const headers = () => ({'Content-Type':'application/json','Authorization':`Bearer ${token()}`});
const toast = () => { const t = document.getElementById('toast'); t.classList.remove('hidden'); setTimeout(()=>t.classList.add('hidden'),2000); };

function toggleDayInputs(day, checked) {
  document.querySelectorAll(`.day-times-${day}`).forEach(el => {
    el.classList.toggle('opacity-30', !checked);
    el.classList.toggle('pointer-events-none', !checked);
  });
}

async function saveCompany() {
  const r = await fetch('/api/v1/company/me', {
    method:'PATCH', headers: headers(),
    body: JSON.stringify({
      name: document.getElementById('compName').value,
      phone: document.getElementById('compPhone').value || null,
      address: document.getElementById('compAddress').value || null,
      description: document.getElementById('compDesc').value || null,
    })
  });
  if(r.ok) toast(); else alert('Ошибка');
}

async function saveBotToken() {
  const t = document.getElementById('botToken').value.trim();
  if(!t) return;
  const r = await fetch(`/api/v1/company/me/bot-token?token=${encodeURIComponent(t)}`, {
    method:'POST', headers: {'Authorization':`Bearer ${token()}`}
  });
  if(r.ok) { toast(); setTimeout(()=>location.reload(), 1000); } else alert('Ошибка');
}

async function saveChatId() {
  const r = await fetch('/api/v1/company/me', {
    method:'PATCH', headers: headers(),
    body: JSON.stringify({ telegram_chat_id: document.getElementById('chatId').value || null })
  });
  if(r.ok) toast(); else alert('Ошибка');
}

async function saveAiPrompt() {
  const r = await fetch('/api/v1/company/me', {
    method:'PATCH', headers: headers(),
    body: JSON.stringify({ ai_system_prompt: document.getElementById('aiPrompt').value || null })
  });
  if(r.ok) toast(); else alert('Ошибка');
}

async function saveWorkingHours() {
  const hours = [];
  for(let i=0;i<7;i++) {
    const active = document.querySelector(`.wh-active[data-day="${i}"]`)?.checked;
    const open = document.querySelector(`.wh-open[data-day="${i}"]`)?.value;
    const close = document.querySelector(`.wh-close[data-day="${i}"]`)?.value;
    hours.push({ day_of_week:i, is_working:!!active, open_time: active?open:null, close_time: active?close:null });
  }
  const r = await fetch('/api/v1/company/me/working-hours', {
    method:'PUT', headers: headers(), body: JSON.stringify(hours)
  });
  if(r.ok) toast(); else alert('Ошибка');
}
</script>
{% endblock %}
