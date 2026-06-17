{% extends "owner/_layout.html" %}
{% set active = "campaigns" %}
{% block title %}Рассылки — AutoService AI{% endblock %}
{% block content %}
<div class="flex items-center justify-between mb-6">
  <h1 class="text-2xl font-bold text-gray-900">Рассылки</h1>
  <button onclick="document.getElementById('newCampaignModal').classList.remove('hidden')"
    class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors flex items-center gap-2">
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
    Создать рассылку
  </button>
</div>

<div class="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-5 text-sm text-amber-800">
  📢 Рассылки доступны на тарифе <strong>BUSINESS</strong> и выше. Сообщения отправляются только клиентам с Telegram.
</div>

<div class="space-y-4">
  {% for campaign in campaigns %}
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
    <div class="flex items-start justify-between">
      <div class="flex-1">
        <div class="flex items-center gap-3 mb-1">
          <h3 class="font-semibold text-gray-900">{{ campaign.name }}</h3>
          <span class="px-2 py-0.5 text-xs rounded-full font-medium
            {% if campaign.status.value == 'draft' %}bg-gray-100 text-gray-600
            {% elif campaign.status.value == 'sending' %}bg-blue-100 text-blue-700
            {% elif campaign.status.value == 'sent' %}bg-green-100 text-green-700
            {% elif campaign.status.value == 'cancelled' %}bg-red-100 text-red-700
            {% else %}bg-yellow-100 text-yellow-700{% endif %}">
            {{ {'draft':'Черновик','scheduled':'Запланирована','sending':'Отправляется',
               'sent':'Отправлена','cancelled':'Отменена'}.get(campaign.status.value,'—') }}
          </span>
        </div>
        <p class="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 mt-2">{{ campaign.text }}</p>
        <div class="flex gap-4 mt-3 text-xs text-gray-500">
          {% if campaign.sent_count %}
          <span>📨 Отправлено: <strong>{{ campaign.sent_count }}</strong></span>
          {% endif %}
          {% if campaign.sent_at %}
          <span>📅 {{ campaign.sent_at.strftime('%d.%m.%Y %H:%M') }}</span>
          {% endif %}
          <span>Создана: {{ campaign.created_at.strftime('%d.%m.%Y') }}</span>
        </div>
      </div>
      {% if campaign.status.value == 'draft' %}
      <button onclick="sendCampaign('{{ campaign.id }}')"
        class="ml-4 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors flex-shrink-0">
        🚀 Отправить
      </button>
      {% endif %}
    </div>
  </div>
  {% else %}
  <div class="bg-white rounded-xl p-12 text-center text-gray-400 border border-gray-100">
    <p class="text-4xl mb-3">📢</p>
    <p class="font-medium">Рассылок пока нет</p>
    <p class="text-sm mt-1">Создайте первую акцию или спецпредложение</p>
  </div>
  {% endfor %}
</div>

<!-- New Campaign Modal -->
<div id="newCampaignModal" class="hidden fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
  <div class="bg-white rounded-2xl w-full max-w-lg shadow-2xl">
    <div class="flex items-center justify-between px-6 py-4 border-b">
      <h3 class="font-semibold text-gray-900">Создать рассылку</h3>
      <button onclick="document.getElementById('newCampaignModal').classList.add('hidden')" class="text-gray-400 hover:text-gray-600">✕</button>
    </div>
    <div class="p-6 space-y-4">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Название кампании *</label>
        <input id="campName" type="text" placeholder="Летняя акция 2024" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Текст сообщения *</label>
        <textarea id="campText" rows="5" placeholder="🔥 Только в июле — скидка 20% на замену масла! Запишитесь прямо сейчас..."
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"></textarea>
        <p class="text-xs text-gray-400 mt-1">Поддерживается Markdown (жирный, курсив)</p>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">Сегмент клиентов</label>
        <div class="space-y-2">
          <label class="flex items-center gap-2 text-sm text-gray-700">
            <input type="radio" name="segment" value="all" checked class="text-blue-600">
            Все клиенты
          </label>
          <label class="flex items-center gap-2 text-sm text-gray-700">
            <input type="radio" name="segment" value="returning" class="text-blue-600">
            Постоянные (2+ визита)
          </label>
          <label class="flex items-center gap-2 text-sm text-gray-700">
            <input type="radio" name="segment" value="inactive" class="text-blue-600">
            Не приходили 6+ месяцев
          </label>
        </div>
      </div>
    </div>
    <div class="px-6 pb-6 flex gap-3">
      <button onclick="createCampaign()" class="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-lg text-sm transition-colors">Создать черновик</button>
      <button onclick="document.getElementById('newCampaignModal').classList.add('hidden')" class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 rounded-lg text-sm transition-colors">Отмена</button>
    </div>
  </div>
</div>

<script>
const token = () => document.cookie.split(';').find(c=>c.trim().startsWith('access_token='))?.split('=')[1];
const companyId = '{{ user.company_id }}';

async function createCampaign() {
  const segment = document.querySelector('input[name="segment"]:checked').value;
  const segmentFilter = segment === 'returning' ? {min_visits: 2} : segment === 'inactive' ? {last_visit_days: 180} : {};
  const data = { name: document.getElementById('campName').value, text: document.getElementById('campText').value, segment_filter: segmentFilter };
  const r = await fetch(`/api/v1/campaigns/${companyId}`, {
    method:'POST', headers:{'Content-Type':'application/json','Authorization':`Bearer ${token()}`},
    body: JSON.stringify(data)
  });
  if(r.ok) location.reload(); else { const e = await r.json(); alert(e.detail || 'Ошибка'); }
}

async function sendCampaign(id) {
  if(!confirm('Отправить рассылку всем клиентам в выбранном сегменте?')) return;
  const r = await fetch(`/api/v1/campaigns/${id}/send`, {
    method:'POST', headers:{'Authorization':`Bearer ${token()}`}
  });
  if(r.ok) { alert('Рассылка запущена!'); location.reload(); }
  else { const e = await r.json(); alert(e.detail || 'Ошибка'); }
}
</script>
{% endblock %}
