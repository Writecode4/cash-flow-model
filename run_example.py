"""
Example: Running the Cash Flow Model
====================================
Run this script to see the model in action.
"""

from sample_data import create_sample_model
from dashboard import CashFlowDashboard


def main():
    print("=" * 70)
    print("CASH FLOW MODEL")
    print("=" * 70)
    
    # Create sample model
    model = create_sample_model()
    
    # === BASIC METRICS ===
    print("\n[FINANCIAL POSITION]")
    print("-" * 40)
    
    dashboard_data = model.generate_dashboard_data()
    
    print(f"  Current Balance:     ${dashboard_data['current_balance']:>12,.2f}")
    print(f"  Pending Invoices:    ${dashboard_data['pending_invoices_total']:>12,.2f}")
    print(f"  DSO (weighted):      {dashboard_data['dso']:>8.1f} days")
    print(f"  DSO (raw):           {dashboard_data['dso_raw']:>8.1f} days")
    print(f"  Weighted AR:         ${dashboard_data['total_weighted_ar']:>12,.2f}")
    print(f"  Monthly Burn Rate:   ${dashboard_data['burn_rate']:>12,.2f}")
    print(f"  Cash Runway:         ", end="")
    if dashboard_data['runway_months'] == float('inf'):
        print(f"{'Indefinite':>8}")
    else:
        print(f"{dashboard_data['runway_months']:>8.1f} months")
    print(f"  Overdue Invoices:    {dashboard_data['overdue_invoices']:>8}")
    print(f"  Active Projects:     {dashboard_data['active_projects']:>8}")
    
    # === CASH CONVERSION CYCLE ===
    print("\n[CASH CONVERSION CYCLE]")
    print("-" * 40)
    
    ccc = model.calculate_cash_conversion_cycle()
    dpo = dashboard_data['dpo']
    print(f"  DSO:  {dashboard_data['dso']:.1f} days")
    print(f"  DIO:  0 days (service business)")
    print(f"  DPO:  {dpo} days")
    print(f"  CCC:  {ccc:.1f} days")
    if ccc < 0:
        print(f"  [OK] Negative CCC: You collect before paying vendors")
    else:
        print(f"  [!] Positive CCC: Try to reduce DSO or extend DPO")
    
    # === AR AGING ===
    print("\n[ACCOUNTS RECEIVABLE AGING]")
    print("-" * 40)
    
    ar = dashboard_data['accounts_receivable']
    weighted = dashboard_data['weighted_ar']
    
    for bucket in ['current', '31-60_days', '61-90_days', 'over_90_days']:
        if ar.get(bucket, 0) > 0:
            w = weighted.get(bucket, 0)
            loss = ar[bucket] - w
            print(f"  {bucket:<15}: ${ar[bucket]:>10,.2f} (expected: ${w:>10,.2f}, risk: ${loss:>8,.2f})")
    
    # === SCENARIO ANALYSIS ===
    print("\n[SCENARIO ANALYSIS] 12-Month Outlook")
    print("-" * 40)
    
    scenarios = {
        'Base Case': {},
        'Win Big Contract (+30% income)': {'income_multiplier': 1.3},
        'Client Defaults (-20% income)': {'income_multiplier': 0.8},
        'Slow Payments (+20 days)': {'payment_delay_days': 20},
        'Hire Employee (+$4k/mo cost)': {'new_monthly_cost': 4000},
        'Best Case': {'income_multiplier': 1.3, 'expense_multiplier': 0.9},
        'Worst Case': {'income_multiplier': 0.7, 'payment_delay_days': 30}
    }
    
    results = model.scenario_analysis(scenarios)
    
    print("\n  Scenario                  | Final Balance | Survives?")
    print("  " + "-" * 55)
    
    for _, row in results.iterrows():
        status = "YES" if row['survives'] else "NO"
        print(f"  {row['scenario']:<26} | ${row['final_balance']:>11,.0f} | {status}")
    
    # === CLIENT ANALYSIS ===
    print("\n[CLIENT PAYMENT BEHAVIOR]")
    print("-" * 40)
    
    client_analysis = model.client_payment_analysis()
    
    if not client_analysis.empty:
        print("\n  Client              | Avg Days to Pay | On-Time Rate")
        print("  " + "-" * 55)
        
        for _, row in client_analysis.iterrows():
            print(f"  {row['client']:<20} | {row['avg_days_to_pay']:>11.0f} days | {row['on_time_payment_rate']:.0f}%")
    
    # === PROJECT STATUS ===
    print("\n[PROJECT STATUS]")
    print("-" * 40)
    
    for project in model.projects:
        remaining = project.remaining_value
        work_pct = project.completion_percentage
        fin_pct = project.financial_completion
        print(f"  {project.client:<20} | Work: {work_pct:>5.0f}% | Billed: {fin_pct:>5.0f}% | ${remaining:>10,.0f} remaining")
    
    # === STRESS TEST ===
    print("\n[STRESS TEST]")
    print("-" * 40)
    
    stress_results = model.stress_test([0.9, 0.7, 0.5])
    
    print("\n  Income Level | Final Balance | Survives?")
    print("  " + "-" * 40)
    
    for _, row in stress_results.iterrows():
        status = "YES" if row['survives'] else "NO"
        print(f"  {row['stress_level']:<13} | ${row['final_balance']:>11,.0f} | {status}")
    
    # === RECOMMENDATIONS ===
    print("\n[KEY INSIGHTS]")
    print("-" * 40)
    
    if dashboard_data['burn_rate'] < 0:
        print(f"  [OK] Cash flow positive: generating ${abs(dashboard_data['burn_rate']):,.0f}/month")
    
    if dashboard_data['dso'] > 45:
        print("  [!] DSO is high (>45 days). Consider:")
        print("     - Offering early payment discounts")
        print("     - Tighter payment terms for new clients")
    
    if dashboard_data['overdue_invoices'] > 0:
        print(f"  [!] {dashboard_data['overdue_invoices']} overdue invoice(s). Action needed:")
        print("     - Follow up with slow-paying clients")
    
    if dashboard_data['runway_months'] < 6 and dashboard_data['runway_months'] != float('inf'):
        print("  [WARNING] RUNWAY WARNING: Less than 6 months of cash reserves")
    elif dashboard_data['runway_months'] >= 12 or dashboard_data['runway_months'] == float('inf'):
        print("  [OK] Healthy runway. Focus on growth and building reserves.")
    
    print("\n" + "=" * 70)
    print("Exporting detailed report to Excel...")
    print("=" * 70)
    
    model.export_to_excel('cash_flow_report.xlsx')
    
    print("\nDone! Check 'cash_flow_report.xlsx' for full details.")
    print("=" * 70)


if __name__ == '__main__':
    main()
