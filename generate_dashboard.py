"""
Generate interactive HTML dashboard for cash flow model.
AUDIT COMPLIANT: All metrics aligned with corrected calculations.
GENERALIZED: Works for any business type.
"""

import json
from datetime import datetime, timedelta
from sample_data import create_sample_model


def generate_html_dashboard():
    model = create_sample_model()
    dashboard_data = model.generate_dashboard_data()
    forecast = model.forecast_cash_flow(months=12)
    client_analysis = model.client_payment_analysis()
    
    scenarios = {
        'Base Case': {},
        'Win Big Contract (+30%)': {'income_multiplier': 1.3},
        'Client Defaults (-20%)': {'income_multiplier': 0.8},
        'Slow Payments (+20 days)': {'payment_delay_days': 20},
        'Hire Employee (+$4k/mo)': {'new_monthly_cost': 4000},
        'Best Case': {'income_multiplier': 1.3, 'expense_multiplier': 0.9},
        'Worst Case': {'income_multiplier': 0.7, 'payment_delay_days': 30}
    }
    scenario_results = model.scenario_analysis(scenarios)
    
    stress_results = model.stress_test([0.9, 0.7, 0.5])
    
    forecast_data = forecast.to_dict('records')
    scenario_data = scenario_results.to_dict('records')
    stress_data = stress_results.to_dict('records')
    client_data = client_analysis.to_dict('records') if not client_analysis.empty else []
    
    projects_data = [{
        'client': p.client,
        'total': p.total_value,
        'received': p.payments_received,
        'remaining': p.remaining_value,
        'work_completion': round(p.work_completion_pct, 1),
        'financial_completion': round(p.financial_completion, 1)
    } for p in model.projects]
    
    expenses_by_category = {}
    for exp in model.expenses:
        cat = exp.category
        expenses_by_category[cat] = expenses_by_category.get(cat, 0) + exp.amount
    for name, amount in model.monthly_fixed_costs.items():
        expenses_by_category[name] = expenses_by_category.get(name, 0) + amount
    
    invoices_data = [{
        'id': inv.invoice_id,
        'client': inv.client,
        'amount': inv.amount,
        'status': inv.status.value,
        'days_outstanding': inv.days_outstanding,
        'days_past_due': inv.days_past_due,
        'collection_probability': round(inv.collection_probability * 100, 0),
        'is_overdue': inv.is_overdue
    } for inv in model.invoices]
    
    ar_aging = dashboard_data.get('accounts_receivable', {})
    weighted_ar = dashboard_data.get('weighted_ar', {})
    
    runway_display = f"{dashboard_data['runway_months']:.1f}" if dashboard_data['runway_months'] != float('inf') else "Indefinite"
    runway_class = 'green' if dashboard_data['runway_months'] >= 6 or dashboard_data['runway_months'] == float('inf') else 'red'
    runway_value_class = 'positive' if dashboard_data['runway_months'] >= 6 or dashboard_data['runway_months'] == float('inf') else 'negative'
    
    dso_class = 'green' if dashboard_data['dso'] <= 30 else 'amber'
    dso_value_class = 'positive' if dashboard_data['dso'] <= 30 else 'warning'
    
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cash Flow Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
        }}
        .header {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border-bottom: 1px solid #334155;
            padding: 24px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(135deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header .date {{
            color: #94a3b8;
            font-size: 14px;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 24px 40px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        .metric-card {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 20px;
            position: relative;
            overflow: hidden;
        }}
        .metric-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
        }}
        .metric-card.blue::before {{ background: linear-gradient(90deg, #3b82f6, #60a5fa); }}
        .metric-card.green::before {{ background: linear-gradient(90deg, #22c55e, #4ade80); }}
        .metric-card.amber::before {{ background: linear-gradient(90deg, #f59e0b, #fbbf24); }}
        .metric-card.red::before {{ background: linear-gradient(90deg, #ef4444, #f87171); }}
        .metric-card.purple::before {{ background: linear-gradient(90deg, #a855f7, #c084fc); }}
        .metric-card.cyan::before {{ background: linear-gradient(90deg, #06b6d4, #22d3ee); }}
        .metric-label {{
            font-size: 12px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        .metric-value {{
            font-size: 28px;
            font-weight: 700;
            color: #f1f5f9;
        }}
        .metric-sub {{
            font-size: 12px;
            color: #64748b;
            margin-top: 4px;
        }}
        .metric-value.positive {{ color: #4ade80; }}
        .metric-value.negative {{ color: #f87171; }}
        .metric-value.warning {{ color: #fbbf24; }}
        
        .grid-2 {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }}
        .grid-3 {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }}
        .card {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 24px;
        }}
        .card-title {{
            font-size: 16px;
            font-weight: 600;
            color: #f1f5f9;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .card-title .icon {{
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
        }}
        .icon.blue {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; }}
        .icon.green {{ background: rgba(34, 197, 94, 0.2); color: #4ade80; }}
        .icon.amber {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; }}
        .icon.red {{ background: rgba(239, 68, 68, 0.2); color: #f87171; }}
        .icon.purple {{ background: rgba(168, 85, 247, 0.2); color: #c084fc; }}
        
        .chart-container {{
            position: relative;
            height: 300px;
        }}
        .chart-container.small {{
            height: 250px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #334155;
        }}
        th {{
            font-size: 12px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }}
        td {{
            font-size: 14px;
            color: #e2e8f0;
        }}
        tr:hover td {{
            background: rgba(59, 130, 246, 0.05);
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge.success {{ background: rgba(34, 197, 94, 0.2); color: #4ade80; }}
        .badge.warning {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; }}
        .badge.danger {{ background: rgba(239, 68, 68, 0.2); color: #f87171; }}
        .badge.info {{ background: rgba(6, 182, 212, 0.2); color: #22d3ee; }}
        
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #334155;
            border-radius: 4px;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }}
        .progress-fill.blue {{ background: linear-gradient(90deg, #3b82f6, #60a5fa); }}
        .progress-fill.green {{ background: linear-gradient(90deg, #22c55e, #4ade80); }}
        .progress-fill.amber {{ background: linear-gradient(90deg, #f59e0b, #fbbf24); }}
        
        .scenario-card {{
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 12px;
            border-left: 4px solid;
        }}
        .scenario-card.survives {{
            background: rgba(34, 197, 94, 0.1);
            border-color: #22c55e;
        }}
        .scenario-card.fails {{
            background: rgba(239, 68, 68, 0.1);
            border-color: #ef4444;
        }}
        .scenario-name {{
            font-weight: 600;
            margin-bottom: 4px;
        }}
        .scenario-value {{
            font-size: 24px;
            font-weight: 700;
        }}
        .scenario-value.positive {{ color: #4ade80; }}
        .scenario-value.negative {{ color: #f87171; }}
        
        .insight-box {{
            padding: 16px 20px;
            border-radius: 8px;
            margin-bottom: 12px;
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }}
        .insight-box.warning {{
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}
        .insight-box.danger {{
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }}
        .insight-box.success {{
            background: rgba(34, 197, 94, 0.1);
            border: 1px solid rgba(34, 197, 94, 0.3);
        }}
        .insight-box.info {{
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
        }}
        .insight-icon {{
            font-size: 20px;
            flex-shrink: 0;
        }}
        .insight-text {{
            font-size: 14px;
            line-height: 1.6;
        }}
        .insight-title {{
            font-weight: 600;
            margin-bottom: 4px;
        }}
        
        .ar-aging {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-top: 16px;
        }}
        .ar-bucket {{
            padding: 12px;
            border-radius: 8px;
            text-align: center;
        }}
        .ar-bucket .label {{
            font-size: 11px;
            color: #94a3b8;
            text-transform: uppercase;
        }}
        .ar-bucket .amount {{
            font-size: 18px;
            font-weight: 700;
            margin-top: 4px;
        }}
        .ar-bucket .weighted {{
            font-size: 11px;
            color: #64748b;
            margin-top: 2px;
        }}
        .ar-bucket.current {{ background: rgba(34, 197, 94, 0.15); }}
        .ar-bucket.current .amount {{ color: #4ade80; }}
        .ar-bucket.moderate {{ background: rgba(245, 158, 11, 0.15); }}
        .ar-bucket.moderate .amount {{ color: #fbbf24; }}
        .ar-bucket.risky {{ background: rgba(249, 115, 22, 0.15); }}
        .ar-bucket.risky .amount {{ color: #f97316; }}
        .ar-bucket.critical {{ background: rgba(239, 68, 68, 0.15); }}
        .ar-bucket.critical .amount {{ color: #f87171; }}
        
        .footer {{
            text-align: center;
            padding: 24px;
            color: #64748b;
            font-size: 12px;
            border-top: 1px solid #334155;
            margin-top: 40px;
        }}
        
        @media (max-width: 1200px) {{
            .metrics-grid {{ grid-template-columns: repeat(3, 1fr); }}
            .grid-2, .grid-3 {{ grid-template-columns: 1fr; }}
            .ar-aging {{ grid-template-columns: repeat(2, 1fr); }}
        }}
        @media (max-width: 768px) {{
            .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .container {{ padding: 16px; }}
            .header {{ padding: 16px; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Cash Flow Dashboard</h1>
        <div class="date">Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}</div>
    </div>
    
    <div class="container">
        <!-- Key Metrics -->
        <div class="metrics-grid">
            <div class="metric-card blue">
                <div class="metric-label">Current Balance</div>
                <div class="metric-value">${dashboard_data['current_balance']:,.0f}</div>
                <div class="metric-sub">Available cash</div>
            </div>
            <div class="metric-card {runway_class}">
                <div class="metric-label">Cash Runway</div>
                <div class="metric-value {runway_value_class}">{runway_display}</div>
                <div class="metric-sub">months at current burn</div>
            </div>
            <div class="metric-card {dso_class}">
                <div class="metric-label">DSO</div>
                <div class="metric-value {dso_value_class}">{dashboard_data['dso']:.1f}</div>
                <div class="metric-sub">days to collect</div>
            </div>
            <div class="metric-card {'green' if dashboard_data['burn_rate'] < 0 else 'amber'}">
                <div class="metric-label">Net Burn Rate</div>
                <div class="metric-value {'positive' if dashboard_data['burn_rate'] < 0 else ''}">${dashboard_data['burn_rate']:,.0f}</div>
                <div class="metric-sub">{'per month (cash positive)' if dashboard_data['burn_rate'] < 0 else 'per month'}</div>
            </div>
            <div class="metric-card purple">
                <div class="metric-label">Weighted AR</div>
                <div class="metric-value">${dashboard_data['total_weighted_ar']:,.0f}</div>
                <div class="metric-sub">expected collections</div>
            </div>
            <div class="metric-card {'red' if dashboard_data['overdue_invoices'] > 0 else 'cyan'}">
                <div class="metric-label">Overdue</div>
                <div class="metric-value {'negative' if dashboard_data['overdue_invoices'] > 0 else ''}">{dashboard_data['overdue_invoices']}</div>
                <div class="metric-sub">${dashboard_data['overdue_amount']:,.0f} outstanding</div>
            </div>
        </div>
        
        <!-- AR Aging -->
        <div class="card" style="margin-bottom: 24px;">
            <div class="card-title">
                <div class="icon amber">A</div>
                Accounts Receivable Aging
            </div>
            <div class="ar-aging">
                <div class="ar-bucket current">
                    <div class="label">0-30 Days</div>
                    <div class="amount">${ar_aging.get('current', 0):,.0f}</div>
                    <div class="weighted">95% likely: ${weighted_ar.get('current', 0):,.0f}</div>
                </div>
                <div class="ar-bucket moderate">
                    <div class="label">31-60 Days</div>
                    <div class="amount">${ar_aging.get('31-60_days', 0):,.0f}</div>
                    <div class="weighted">85% likely: ${weighted_ar.get('31-60_days', 0):,.0f}</div>
                </div>
                <div class="ar-bucket risky">
                    <div class="label">61-90 Days</div>
                    <div class="amount">${ar_aging.get('61-90_days', 0):,.0f}</div>
                    <div class="weighted">65% likely: ${weighted_ar.get('61-90_days', 0):,.0f}</div>
                </div>
                <div class="ar-bucket critical">
                    <div class="label">90+ Days</div>
                    <div class="amount">${ar_aging.get('over_90_days', 0):,.0f}</div>
                    <div class="weighted">40% likely: ${weighted_ar.get('over_90_days', 0):,.0f}</div>
                </div>
            </div>
        </div>
        
        <!-- Main Charts Row -->
        <div class="grid-2">
            <div class="card">
                <div class="card-title">
                    <div class="icon blue">$</div>
                    Cash Flow Forecast (12 Months)
                </div>
                <div class="chart-container">
                    <canvas id="forecastChart"></canvas>
                </div>
            </div>
            <div class="card">
                <div class="card-title">
                    <div class="icon green">%</div>
                    Scenario Outcomes
                </div>
                <div class="chart-container">
                    <canvas id="scenarioChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Second Row -->
        <div class="grid-3">
            <div class="card">
                <div class="card-title">
                    <div class="icon amber">#</div>
                    Income vs Expenses
                </div>
                <div class="chart-container small">
                    <canvas id="incomeExpenseChart"></canvas>
                </div>
            </div>
            <div class="card">
                <div class="card-title">
                    <div class="icon purple">@</div>
                    Expense Breakdown
                </div>
                <div class="chart-container small">
                    <canvas id="expenseChart"></canvas>
                </div>
            </div>
            <div class="card">
                <div class="card-title">
                    <div class="icon red">!</div>
                    Stress Test Results
                </div>
                <div class="chart-container small">
                    <canvas id="stressChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Projects & Clients -->
        <div class="grid-2">
            <div class="card">
                <div class="card-title">
                    <div class="icon blue">P</div>
                    Active Projects
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Client</th>
                            <th>Value</th>
                            <th>Work Done</th>
                            <th>Billed</th>
                            <th>Remaining</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(f'''
                        <tr>
                            <td>{p['client']}</td>
                            <td>${p['total']:,.0f}</td>
                            <td>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div class="progress-bar" style="width: 80px;">
                                        <div class="progress-fill {'green' if p['work_completion'] >= 75 else 'amber' if p['work_completion'] >= 50 else 'blue'}" style="width: {p['work_completion']}%"></div>
                                    </div>
                                    <span style="font-size: 12px; color: #94a3b8;">{p['work_completion']}%</span>
                                </div>
                            </td>
                            <td>{p['financial_completion']}%</td>
                            <td>${p['remaining']:,.0f}</td>
                        </tr>
                        ''' for p in projects_data)}
                    </tbody>
                </table>
            </div>
            <div class="card">
                <div class="card-title">
                    <div class="icon green">C</div>
                    Client Payment Behavior
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Client</th>
                            <th>Avg Days</th>
                            <th>On-Time</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(f'''
                        <tr>
                            <td>{c['client']}</td>
                            <td>{c['avg_days_to_pay']:.0f} days</td>
                            <td>{c['on_time_payment_rate']:.0f}%</td>
                            <td>
                                <span class="badge {'success' if c['on_time_payment_rate'] >= 80 else 'warning' if c['on_time_payment_rate'] >= 50 else 'danger'}">
                                    {'Reliable' if c['on_time_payment_rate'] >= 80 else 'Fair' if c['on_time_payment_rate'] >= 50 else 'Slow'}
                                </span>
                            </td>
                        </tr>
                        ''' for c in client_data)}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Scenario Analysis Detail -->
        <div class="card" style="margin-bottom: 24px;">
            <div class="card-title">
                <div class="icon purple">S</div>
                Scenario Analysis (12-Month Outlook)
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
                {"".join(f'''
                <div class="scenario-card {'survives' if s['survives'] else 'fails'}">
                    <div class="scenario-name">{s['scenario']}</div>
                    <div class="scenario-value {'positive' if s['final_balance'] > 0 else 'negative'}">${s['final_balance']:,.0f}</div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                        {'Survives' if s['survives'] else 'Runs out of cash'}
                    </div>
                </div>
                ''' for s in scenario_data)}
            </div>
        </div>
        
        <!-- Invoices Table -->
        <div class="card" style="margin-bottom: 24px;">
            <div class="card-title">
                <div class="icon amber">I</div>
                Outstanding Invoices
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Invoice ID</th>
                        <th>Client</th>
                        <th>Amount</th>
                        <th>Days Outstanding</th>
                        <th>Days Past Due</th>
                        <th>Collection %</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(f'''
                    <tr>
                        <td>{i['id']}</td>
                        <td>{i['client']}</td>
                        <td>${i['amount']:,.0f}</td>
                        <td>{i['days_outstanding']} days</td>
                        <td>{i['days_past_due']} days</td>
                        <td>{i['collection_probability']:.0f}%</td>
                        <td>
                            <span class="badge {'success' if i['status'] == 'received' else 'warning' if i['status'] == 'pending' else 'danger'}">
                                {i['status'].upper()}
                            </span>
                        </td>
                    </tr>
                    ''' for i in invoices_data)}
                </tbody>
            </table>
        </div>
        
        <!-- Key Insights -->
        <div class="card">
            <div class="card-title">
                <div class="icon red">!</div>
                Key Insights & Recommendations
            </div>
            {"".join(f'''
            <div class="insight-box {insight['type']}">
                <div class="insight-icon">{insight['icon']}</div>
                <div class="insight-text">
                    <div class="insight-title">{insight['title']}</div>
                    {insight['text']}
                </div>
            </div>
            ''' for insight in generate_insights(dashboard_data, scenario_results))}
        </div>
    </div>
    
    <div class="footer">
        Cash Flow Model | Audit Compliant Version
    </div>
    
    <script>
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.borderColor = '#334155';
        
        new Chart(document.getElementById('forecastChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps([f['month'] for f in forecast_data])},
                datasets: [{{
                    label: 'Cumulative Balance',
                    data: {json.dumps([f['cumulative_balance'] for f in forecast_data])},
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }}, {{
                    label: 'Net Cash Flow',
                    data: {json.dumps([f['net_cash_flow'] for f in forecast_data])},
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ position: 'top' }} }},
                scales: {{
                    y: {{ grid: {{ color: 'rgba(51, 65, 85, 0.5)' }}, ticks: {{ callback: v => '$' + v.toLocaleString() }} }},
                    x: {{ grid: {{ display: false }} }}
                }}
            }}
        }});
        
        new Chart(document.getElementById('scenarioChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps([s['scenario'] for s in scenario_data])},
                datasets: [{{
                    label: 'Final Balance',
                    data: {json.dumps([s['final_balance'] for s in scenario_data])},
                    backgroundColor: {json.dumps(['rgba(34, 197, 94, 0.7)' if s['survives'] else 'rgba(239, 68, 68, 0.7)' for s in scenario_data])},
                    borderColor: {json.dumps(['#22c55e' if s['survives'] else '#ef4444' for s in scenario_data])},
                    borderWidth: 2,
                    borderRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    x: {{ grid: {{ color: 'rgba(51, 65, 85, 0.5)' }}, ticks: {{ callback: v => '$' + (v/1000).toFixed(0) + 'k' }} }},
                    y: {{ grid: {{ display: false }} }}
                }}
            }}
        }});
        
        new Chart(document.getElementById('incomeExpenseChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps([f['month'] for f in forecast_data])},
                datasets: [{{
                    label: 'Income',
                    data: {json.dumps([f['projected_income'] for f in forecast_data])},
                    backgroundColor: 'rgba(34, 197, 94, 0.7)',
                    borderRadius: 4
                }}, {{
                    label: 'Expenses',
                    data: {json.dumps([f['total_expenses'] for f in forecast_data])},
                    backgroundColor: 'rgba(239, 68, 68, 0.7)',
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ position: 'top' }} }},
                scales: {{
                    y: {{ grid: {{ color: 'rgba(51, 65, 85, 0.5)' }}, ticks: {{ callback: v => '$' + (v/1000).toFixed(0) + 'k' }} }},
                    x: {{ grid: {{ display: false }}, ticks: {{ maxRotation: 45 }} }}
                }}
            }}
        }});
        
        new Chart(document.getElementById('expenseChart'), {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(list(expenses_by_category.keys()))},
                datasets: [{{
                    data: {json.dumps(list(expenses_by_category.values()))},
                    backgroundColor: ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#a855f7', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ position: 'right', labels: {{ padding: 12, usePointStyle: true }} }} }}
            }}
        }});
        
        new Chart(document.getElementById('stressChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps([s['stress_level'] for s in stress_data])},
                datasets: [{{
                    label: 'Final Balance',
                    data: {json.dumps([s['final_balance'] for s in stress_data])},
                    backgroundColor: {json.dumps(['rgba(34, 197, 94, 0.7)' if s['survives'] else 'rgba(239, 68, 68, 0.7)' for s in stress_data])},
                    borderColor: {json.dumps(['#22c55e' if s['survives'] else '#ef4444' for s in stress_data])},
                    borderWidth: 2,
                    borderRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{ grid: {{ color: 'rgba(51, 65, 85, 0.5)' }}, ticks: {{ callback: v => '$' + (v/1000).toFixed(0) + 'k' }} }},
                    x: {{ grid: {{ display: false }} }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
    
    return html


def generate_insights(dashboard_data, scenario_results):
    """Generate actionable insights based on metrics."""
    insights = []
    
    # DSO Analysis
    if dashboard_data['dso'] > 45:
        insights.append({
            'type': 'warning',
            'icon': '!',
            'title': 'High Days Sales Outstanding (DSO)',
            'text': f'Your DSO is {dashboard_data["dso"]:.1f} days. Target: under 30 days. Consider offering early payment discounts and invoicing immediately upon delivery.'
        })
    elif dashboard_data['dso'] <= 30:
        insights.append({
            'type': 'success',
            'icon': '+',
            'title': 'Healthy Collection Cycle',
            'text': f'Your DSO of {dashboard_data["dso"]:.1f} days is excellent. You are collecting payments efficiently.'
        })
    
    # Runway Analysis
    if dashboard_data['runway_months'] < 6 and dashboard_data['runway_months'] != float('inf'):
        insights.append({
            'type': 'danger',
            'icon': '!!',
            'title': 'Critical Runway Warning',
            'text': f'With only {dashboard_data["runway_months"]:.1f} months of runway, immediate action is required. Accelerate collections, delay non-essential expenses.'
        })
    elif dashboard_data['runway_months'] == float('inf'):
        insights.append({
            'type': 'success',
            'icon': '+',
            'title': 'Indefinite Runway',
            'text': 'Your projected income exceeds expenses. Focus on growth and building reserves.'
        })
    elif dashboard_data['runway_months'] < 12:
        insights.append({
            'type': 'warning',
            'icon': '!',
            'title': 'Runway Needs Improvement',
            'text': f'Your {dashboard_data["runway_months"]:.1f} month runway is below the recommended 12 months. Focus on growing revenue and building reserves.'
        })
    
    # Burn Rate Analysis
    if dashboard_data['burn_rate'] < 0:
        insights.append({
            'type': 'success',
            'icon': '+',
            'title': 'Cash Flow Positive',
            'text': f'Your business generates ${abs(dashboard_data["burn_rate"]):,.0f}/month more than it spends. Excellent financial health.'
        })
    
    # Overdue Analysis
    if dashboard_data['overdue_invoices'] > 0:
        insights.append({
            'type': 'danger',
            'icon': '!!',
            'title': 'Overdue Invoices Detected',
            'text': f'You have {dashboard_data["overdue_invoices"]} overdue invoice(s) totaling ${dashboard_data["overdue_amount"]:,.0f}. Contact these clients immediately.'
        })
    
    # AR Aging - Weighted vs Raw
    ar = dashboard_data.get('accounts_receivable', {})
    weighted = dashboard_data.get('weighted_ar', {})
    if ar.get('over_90_days', 0) > 0:
        loss = ar.get('over_90_days', 0) - weighted.get('over_90_days', 0)
        insights.append({
            'type': 'danger',
            'icon': '!!',
            'title': 'High-Risk Receivables (90+ Days)',
            'text': f'You have ${ar["over_90_days"]:,.0f} in receivables over 90 days. Expected collection: ${weighted.get("over_90_days", 0):,.0f}. Potential loss: ${loss:,.0f}.'
        })
    
    # CCC Analysis
    ccc = dashboard_data.get('cash_conversion_cycle', 0)
    dpo = dashboard_data.get('dpo', 0)
    insights.append({
        'type': 'info',
        'icon': 'i',
        'title': 'Cash Conversion Cycle',
        'text': f'CCC: {ccc:.1f} days (DSO {dashboard_data["dso"]:.1f} + DIO 0 - DPO {dpo}). {"Negative CCC means you collect before paying vendors - excellent!" if ccc < 0 else "Target: reduce DSO or extend DPO to lower CCC."}'
    })
    
    return insights


if __name__ == '__main__':
    html = generate_html_dashboard()
    
    output_path = 'C:/Users/Carlos/Desktop/cash-flow-model/dashboard.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Dashboard generated: {output_path}")
