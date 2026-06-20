{% extends "base.html" %}
{% block title %}Admin — AutoService AI{% endblock %}
{% block body %}
<div class="flex h-screen overflow-hidden">
  <aside class="w-64 bg-gray-900 flex flex-col flex-shrink-0">
    <div class="p-5 border-b border-gray-700">
      <p class="text-white font-bold">⚙️ Admin Panel</p>
      <p class="text-gray-400 text-xs mt-0.5">AutoService AI</p>
    </div>
    <nav class="flex-1 p-3 space-y-1">
      <a href="/admin" class="sidebar-link active">📊 Dashboard</a>
      <a href="/admin/companies" class="sidebar-link">🏢 Компании</a>
    </nav>
    <div class="p-3 border-t border-gray-700">
      <a href="/logout" class="sidebar-link text-red-400 hover:text-red-300 hover:bg-gray-800">🚪 Выйти</a>
    </div>
  </aside>
  <main class="flex-1 overflow-y-auto p-6">
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Платформа AutoService AI</h1>

    <!-- MRR / ARR banner -->
    <div class="bg-gradient-to-r from-indigo-600 to-blue-600 rounded-2xl p-6 mb-6 text-white">
      <div class="grid grid-cols-2 gap-6">
        <div>
          <p class="text-indigo-200 text-sm font-medium">MRR</p>
          <p class="text-4xl font-bold mt-1">{{ '{:,.0f}'.format(mrr).replace(',', ' ') }} ₽</p>
          <p class="text-indigo-200 text-xs mt-1">Monthly Recurring Revenue</p>
        </div>
        <div>
          <p class="text-indigo-200 text-sm font-medium">ARR</p>
          <p class="text-4xl font-bold mt-1">{{ '{:,.0f}'.format(arr).replace(',', ' ') }} ₽</p>
          <p class="text-indigo-200 text-xs mt-1">Annual Recurring Revenue</p>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <p class="text-xs font-medium text-gray-500 uppercase">Компаний</p>
        <p class="text-3xl font-bold text-gray-900 mt-1">{{ total_companies }}</p>
      </div>
      <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <p class="text-xs font-medium text-gray-500 uppercase">Активных</p>
        <p class="text-3xl font-bold text-green-700 mt-1">{{ active_subscriptions }}</p>
      </div>
      <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <p class="text-xs font-medium text-gray-500 uppercase">Пробных</p>
        <p class="text-3xl font-bold text-yellow-600 mt-1">{{ trial_subscriptions }}</p>
      </div>
      <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <p class="text-xs font-medium text-gray-500 uppercase">Отток (30д)</p>
        <p class="text-3xl font-bold text-red-600 mt-1">{{ churned }}</p>
      </div>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-100">
      <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <h2 class="font-semibold text-gray-900">Последние регистрации</h2>
        <a href="/admin/companies" class="text-xs text-blue-600 hover:underline">Все компании →</a>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-gray-50 border-b border-gray-100">
              <th class="text-left px-4 py-3 font-medium text-gray-500">Компания</th>
              <th class="text-left px-4 py-3 font-medium text-gray-500">Тариф</th>
              <th class="text-left px-4 py-3 font-medium text-gray-500">Статус</th>
              <th class="text-left px-4 py-3 font-medium text-gray-500">Создана</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            {% for company in recent_companies %}
            <tr class="hover:bg-gray-50">
              <td class="px-4 py-3">
                <p class="font-medium text-gray-900">{{ company.name }}</p>
                <p class="text-xs text-gray-400">{{ company.slug }}</p>
              </td>
              <td class="px-4 py-3 text-gray-600">
                {{ company.subscription.plan.display_name if company.subscription and company.subscription.plan else '—' }}
              </td>
              <td class="px-4 py-3">
                {% if company.subscription %}
                <span class="px-2 py-0.5 text-xs rounded-full font-medium
                  {% if company.subscription.status.value == 'active' %}bg-green-100 text-green-700
                  {% elif company.subscription.status.value == 'trial' %}bg-yellow-100 text-yellow-700
                  {% elif company.subscription.status.value == 'past_due' %}bg-red-100 text-red-700
                  {% else %}bg-gray-100 text-gray-500{% endif %}">
                  {{ {'trial':'Триал','active':'Активна','past_due':'Просрочена',
                     'cancelled':'Отменена','expired':'Истекла'}.get(company.subscription.status.value,'—') }}
                </span>
                {% else %}—{% endif %}
              </td>
              <td class="px-4 py-3 text-gray-500 text-xs">{{ company.created_at.strftime('%d.%m.%Y') }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </main>
</div>
{% endblock %}
