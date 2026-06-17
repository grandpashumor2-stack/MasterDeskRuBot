{% extends "base.html" %}
{% block title %}Компании — Admin{% endblock %}
{% block body %}
<div class="flex h-screen overflow-hidden">
  <aside class="w-64 bg-gray-900 flex flex-col flex-shrink-0">
    <div class="p-5 border-b border-gray-700">
      <p class="text-white font-bold">⚙️ Admin Panel</p>
    </div>
    <nav class="flex-1 p-3 space-y-1">
      <a href="/admin" class="sidebar-link">📊 Dashboard</a>
      <a href="/admin/companies" class="sidebar-link active">🏢 Компании</a>
    </nav>
    <div class="p-3 border-t border-gray-700">
      <a href="/logout" class="sidebar-link text-red-400 hover:text-red-300 hover:bg-gray-800">🚪 Выйти</a>
    </div>
  </aside>
  <main class="flex-1 overflow-y-auto p-6">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Компании ({{ companies|length }})</h1>
    </div>
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="p-4 border-b">
        <input type="text" id="search" onkeyup="filterTable()" placeholder="🔍 Поиск..." class="border border-gray-300 rounded-lg px-3 py-2 text-sm w-72 focus:outline-none focus:ring-2 focus:ring-blue-500">
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm" id="companiesTable">
          <thead>
            <tr class="bg-gray-50 border-b border-gray-100">
              <th class="text-left px-4 py-3 font-medium text-gray-500">Компания</th>
              <th class="text-left px-4 py-3 font-medium text-gray-500">Тариф</th>
              <th class="text-left px-4 py-3 font-medium text-gray-500">Статус</th>
              <th class="text-left px-4 py-3 font-medium text-gray-500">Диалогов</th>
              <th class="text-left px-4 py-3 font-medium text-gray-500">Создана</th>
              <th class="text-left px-4 py-3 font-medium text-gray-500">Действия</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            {% for c in companies %}
            <tr class="hover:bg-gray-50 company-row">
              <td class="px-4 py-3">
                <p class="font-medium text-gray-900">{{ c.name }}</p>
                <p class="text-xs text-gray-400 font-mono">{{ c.slug }}</p>
                {% if c.phone %}<p class="text-xs text-gray-500">{{ c.phone }}</p>{% endif %}
              </td>
              <td class="px-4 py-3">
                {{ c.subscription.plan.display_name if c.subscription and c.subscription.plan else '—' }}
              </td>
              <td class="px-4 py-3">
                {% if c.subscription %}
                <span class="px-2 py-0.5 text-xs rounded-full font-medium
                  {% if c.subscription.status.value == 'active' %}bg-green-100 text-green-700
                  {% elif c.subscription.status.value == 'trial' %}bg-yellow-100 text-yellow-700
                  {% elif c.subscription.status.value == 'past_due' %}bg-red-100 text-red-700
                  {% else %}bg-gray-100 text-gray-500{% endif %}">
                  {{ c.subscription.status.value }}
                </span>
                {% else %}—{% endif %}
              </td>
              <td class="px-4 py-3 text-gray-600">
                {% if c.subscription and c.subscription.plan %}
                  {{ c.subscription.dialogs_used }}/{{ c.subscription.plan.limits.get('max_dialogs',-1) if c.subscription.plan.limits else '?' }}
                {% else %}—{% endif %}
              </td>
              <td class="px-4 py-3 text-gray-500 text-xs">{{ c.created_at.strftime('%d.%m.%Y') }}</td>
              <td class="px-4 py-3">
                <div class="flex gap-2">
                  <select id="plan-{{ c.id }}" class="text-xs border border-gray-300 rounded px-2 py-1">
                    {% for plan in plans %}
                    <option value="{{ plan.name.value }}">{{ plan.display_name }}</option>
                    {% endfor %}
                  </select>
                  <button onclick="activateSub('{{ c.id }}')"
                    class="text-xs bg-green-100 hover:bg-green-200 text-green-800 px-2 py-1 rounded transition-colors">
                    Активировать
                  </button>
                </div>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </main>
</div>
<script>
const token = () => document.cookie.split(';').find(c=>c.trim().startsWith('access_token='))?.split('=')[1];
function filterTable() {
  const q = document.getElementById('search').value.toLowerCase();
  document.querySelectorAll('.company-row').forEach(r => r.style.display = r.textContent.toLowerCase().includes(q)?'':'none');
}
async function activateSub(companyId) {
  const plan = document.getElementById(`plan-${companyId}`).value;
  const r = await fetch(`/api/v1/admin/companies/${companyId}/activate?plan_name=${plan}`, {
    method:'POST', headers:{'Authorization':`Bearer ${token()}`}
  });
  if(r.ok) { alert('Подписка активирована!'); location.reload(); } else alert('Ошибка');
}
</script>
{% endblock %}
