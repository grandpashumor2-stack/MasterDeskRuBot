{% extends "owner/_layout.html" %}
{% set active = "analytics" %}
{% block title %}Аналитика — AutoService AI{% endblock %}
{% block content %}
<h1 class="text-2xl font-bold text-gray-900 mb-6">Аналитика</h1>

<div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
  <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
    <p class="text-xs font-medium text-gray-500 uppercase tracking-wide">Записей за месяц</p>
    <p class="text-3xl font-bold text-gray-900 mt-1">{{ month_appointments }}</p>
  </div>
  <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
    <p class="text-xs font-medium text-gray-500 uppercase tracking-wide">Всего клиентов</p>
    <p class="text-3xl font-bold text-gray-900 mt-1">{{ total_clients }}</p>
  </div>
  <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
    <p class="text-xs font-medium text-gray-500 uppercase tracking-wide">Постоянных</p>
    <p class="text-3xl font-bold text-gray-900 mt-1">{{ returning_clients }}</p>
    <p class="text-xs text-gray-500 mt-1">≥ 2 визита</p>
  </div>
  <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
    <p class="text-xs font-medium text-gray-500 uppercase tracking-wide">Конверсия</p>
    <p class="text-3xl font-bold {% if conversion_rate >= 20 %}text-green-700{% else %}text-orange-600{% endif %} mt-1">{{ conversion_rate }}%</p>
    <p class="text-xs text-gray-500 mt-1">диалог → запись</p>
  </div>
</div>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <!-- Monthly chart -->
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
    <h2 class="font-semibold text-gray-900 mb-4">Записи по месяцам</h2>
    <canvas id="monthlyChart" height="200"></canvas>
  </div>
  <!-- Top services -->
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
    <h2 class="font-semibold text-gray-900 mb-4">Топ услуг</h2>
    {% if top_services %}
    <div class="space-y-3">
      {% for svc in top_services %}
      {% set max_count = top_services[0].count if top_services[0].count > 0 else 1 %}
      <div>
        <div class="flex items-center justify-between mb-1">
          <span class="text-sm text-gray-700">{{ svc.name }}</span>
          <span class="text-sm font-semibold text-gray-900">{{ svc.count }}</span>
        </div>
        <div class="w-full bg-gray-100 rounded-full h-2">
          <div class="bg-blue-500 h-2 rounded-full" style="width: {{ (svc.count / max_count * 100)|round }}%"></div>
        </div>
      </div>
      {% endfor %}
    </div>
    {% else %}
    <p class="text-gray-400 text-sm">Нет данных</p>
    {% endif %}
  </div>
</div>

<script>
const ctx = document.getElementById('monthlyChart').getContext('2d');
new Chart(ctx, {
  type: 'bar',
  data: {
    labels: {{ monthly_data | map(attribute='month') | list | tojson }},
    datasets: [{
      label: 'Записей',
      data: {{ monthly_data | map(attribute='count') | list | tojson }},
      backgroundColor: 'rgba(59,130,246,0.7)',
      borderRadius: 6,
    }]
  },
  options: {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
  }
});
</script>
{% endblock %}
