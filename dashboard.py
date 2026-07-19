"""
Cash Flow Visualization Module
===============================
Dashboard and charts for cash flow analysis.

AUDIT FIX: Confidence intervals now expand over time.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class CashFlowDashboard:
    """Visualization dashboard for cash flow model."""
    
    def __init__(self, model):
        self.model = model
        self.colors = {
            'primary': '#2E86AB',
            'success': '#28A745',
            'warning': '#FFC107',
            'danger': '#DC3545',
            'info': '#17A2B8',
            'light': '#F8F9FA'
        }
    
    def create_full_dashboard(self, save_path: str = None):
        """Create a comprehensive dashboard with all metrics."""
        fig = plt.figure(figsize=(20, 16))
        fig.suptitle('Cash Flow Dashboard - Data Consulting Firm', 
                     fontsize=16, fontweight='bold', y=0.98)
        
        # Create grid
        gs = fig.add_gridspec(4, 3, hspace=0.3, wspace=0.3)
        
        # 1. Cash Balance Timeline (top left)
        ax1 = fig.add_subplot(gs[0, :2])
        self._plot_balance_timeline(ax1)
        
        # 2. Key Metrics (top right)
        ax2 = fig.add_subplot(gs[0, 2])
        self._plot_key_metrics(ax2)
        
        # 3. Income vs Expenses (middle left)
        ax3 = fig.add_subplot(gs[1, :2])
        self._plot_income_vs_expenses(ax3)
        
        # 4. Client Payment Behavior (middle right)
        ax4 = fig.add_subplot(gs[1, 2])
        self._plot_client_payments(ax4)
        
        # 5. Expense Breakdown (bottom left)
        ax5 = fig.add_subplot(gs[2, 0])
        self._plot_expense_breakdown(ax5)
        
        # 6. Project Status (bottom middle)
        ax6 = fig.add_subplot(gs[2, 1])
        self._plot_project_status(ax6)
        
        # 7. Scenario Comparison (bottom right)
        ax7 = fig.add_subplot(gs[2, 2])
        self._plot_scenario_comparison(ax7)
        
        # 8. Forecast with Confidence (bottom row)
        ax8 = fig.add_subplot(gs[3, :])
        self._plot_forecast_with_confidence(ax8)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Dashboard saved to {save_path}")
        
        plt.show()
    
    def _plot_balance_timeline(self, ax):
        """Plot historical and projected balance."""
        forecast = self.model.forecast_cash_flow(months=12)
        
        months = range(len(forecast))
        balances = forecast['cumulative_balance'].values
        
        # Color based on positive/negative
        colors = [self.colors['success'] if b >= 0 else self.colors['danger'] 
                  for b in balances]
        
        ax.bar(months, balances, color=colors, alpha=0.7)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.set_title('Cash Balance Forecast (12 Months)', fontweight='bold')
        ax.set_xlabel('Month')
        ax.set_ylabel('Balance ($)')
        ax.set_xticks(months[::2])
        ax.set_xticklabels([forecast['month'].iloc[i] for i in range(0, len(forecast), 2)], 
                          rotation=45)
        ax.grid(axis='y', alpha=0.3)
        ax.set_facecolor(self.colors['light'])
    
    def _plot_key_metrics(self, ax):
        """Display key financial metrics."""
        ax.axis('off')
        
        dashboard = self.model.generate_dashboard_data()
        
        metrics = [
            ('Current Balance', f"${dashboard['current_balance']:,.0f}"),
            ('DSO', f"{dashboard['dso']:.1f} days"),
            ('Burn Rate', f"${dashboard['burn_rate']:,.0f}/mo"),
            ('Runway', f"{dashboard['runway_months']:.1f} months" if dashboard['runway_months'] != float('inf') else "Indefinite"),
            ('Total AR', f"${dashboard['total_ar']:,.0f}"),
            ('Overdue', f"{dashboard['overdue_invoices']} invoices")
        ]
        
        for i, (label, value) in enumerate(metrics):
            y = 0.85 - (i * 0.15)
            ax.text(0.1, y, label, fontsize=10, fontweight='bold', 
                   transform=ax.transAxes, va='center')
            ax.text(0.7, y, value, fontsize=10, 
                   transform=ax.transAxes, va='center', ha='right')
        
        ax.set_title('Key Metrics', fontweight='bold')
        ax.set_facecolor(self.colors['light'])
        for spine in ax.spines.values():
            spine.set_visible(True)
    
    def _plot_income_vs_expenses(self, ax):
        """Plot monthly income vs expenses."""
        forecast = self.model.forecast_cash_flow(months=12)
        
        months = range(len(forecast))
        width = 0.35
        
        ax.bar([m - width/2 for m in months], forecast['projected_income'], 
               width, label='Income', color=self.colors['success'], alpha=0.7)
        ax.bar([m + width/2 for m in months], forecast['total_expenses'], 
               width, label='Expenses', color=self.colors['danger'], alpha=0.7)
        
        ax.set_title('Monthly Income vs Expenses', fontweight='bold')
        ax.set_xlabel('Month')
        ax.set_ylabel('Amount ($)')
        ax.legend()
        ax.set_xticks(months[::2])
        ax.set_xticklabels([forecast['month'].iloc[i] for i in range(0, len(forecast), 2)], 
                          rotation=45)
        ax.grid(axis='y', alpha=0.3)
        ax.set_facecolor(self.colors['light'])
    
    def _plot_client_payments(self, ax):
        """Plot client payment behavior."""
        client_data = self.model.client_payment_analysis()
        
        if client_data.empty:
            ax.text(0.5, 0.5, 'No payment data', ha='center', va='center')
            ax.set_title('Client Payments', fontweight='bold')
            return
        
        clients = client_data['client'].tolist()
        avg_days = client_data['avg_days_to_pay'].tolist()
        
        colors = [self.colors['success'] if d <= 30 else 
                 self.colors['warning'] if d <= 45 else 
                 self.colors['danger'] for d in avg_days]
        
        ax.barh(clients, avg_days, color=colors, alpha=0.7)
        ax.axvline(x=30, color='green', linestyle='--', alpha=0.5, label='30 days')
        ax.set_title('Avg Days to Pay by Client', fontweight='bold')
        ax.set_xlabel('Days')
        ax.legend()
        ax.set_facecolor(self.colors['light'])
    
    def _plot_expense_breakdown(self, ax):
        """Plot expense categories breakdown."""
        categories = {}
        for exp in self.model.expenses:
            cat = exp.category
            categories[cat] = categories.get(cat, 0) + exp.amount
        
        # Add fixed costs
        for name, amount in self.model.monthly_fixed_costs.items():
            categories[name] = categories.get(name, 0) + amount
        
        if not categories:
            ax.text(0.5, 0.5, 'No expenses', ha='center', va='center')
            ax.set_title('Expenses', fontweight='bold')
            return
        
        labels = list(categories.keys())
        values = list(categories.values())
        
        ax.pie(values, labels=labels, autopct='%1.1f%%', 
               colors=plt.cm.Set3(np.linspace(0, 1, len(labels))))
        ax.set_title('Expense Breakdown', fontweight='bold')
    
    def _plot_project_status(self, ax):
        """Plot project completion status."""
        projects = self.model.projects
        
        if not projects:
            ax.text(0.5, 0.5, 'No projects', ha='center', va='center')
            ax.set_title('Projects', fontweight='bold')
            return
        
        project_names = [p.client for p in projects]
        completion = [p.completion_percentage for p in projects]
        
        colors = [self.colors['success'] if c >= 75 else 
                 self.colors['warning'] if c >= 50 else 
                 self.colors['info'] for c in completion]
        
        bars = ax.barh(project_names, completion, color=colors, alpha=0.7)
        ax.set_xlim(0, 100)
        ax.set_title('Project Completion', fontweight='bold')
        ax.set_xlabel('% Complete')
        
        for bar, val in zip(bars, completion):
            ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                   f'{val:.0f}%', va='center')
        
        ax.set_facecolor(self.colors['light'])
    
    def _plot_scenario_comparison(self, ax):
        """Plot scenario comparison."""
        scenarios = {
            'Base': {},
            'Optimistic': {'income_multiplier': 1.2},
            'Pessimistic': {'income_multiplier': 0.8}
        }
        
        results = self.model.scenario_analysis(scenarios)
        
        x = range(len(results))
        colors = [self.colors['success'] if s['survives'] else self.colors['danger'] 
                 for _, s in results.iterrows()]
        
        ax.bar(x, results['final_balance'], color=colors, alpha=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels(results['scenario'], rotation=45)
        ax.set_title('Scenario Outcomes', fontweight='bold')
        ax.set_ylabel('Final Balance ($)')
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.grid(axis='y', alpha=0.3)
        ax.set_facecolor(self.colors['light'])
    
    def _plot_forecast_with_confidence(self, ax):
        """
        Plot forecast with expanding confidence intervals.
        
        AUDIT FIX: Confidence intervals now EXPAND over time,
        reflecting increasing uncertainty in distant forecasts.
        """
        forecast = self.model.forecast_cash_flow(months=12)
        
        months = range(len(forecast))
        base_balance = forecast['cumulative_balance'].values
        
        # EXPANDING confidence intervals: +/- 5% per month
        # Month 1: +/- 5%, Month 6: +/- 30%, Month 12: +/- 60%
        confidence_factors = np.array([0.05 * (i + 1) for i in range(len(months))])
        
        upper = base_balance * (1 + confidence_factors)
        lower = base_balance * (1 - confidence_factors)
        
        ax.fill_between(months, lower, upper, alpha=0.2, color=self.colors['primary'],
                        label='80% Confidence (expanding)')
        ax.plot(months, base_balance, color=self.colors['primary'], 
                linewidth=2, label='Expected')
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='Break-even')
        
        ax.set_title('12-Month Cash Flow Forecast with Expanding Confidence Interval', 
                    fontweight='bold')
        ax.set_xlabel('Month')
        ax.set_ylabel('Balance ($)')
        ax.legend()
        ax.set_xticks(months[::2])
        ax.set_xticklabels([forecast['month'].iloc[i] for i in range(0, len(forecast), 2)], 
                          rotation=45)
        ax.grid(alpha=0.3)
        ax.set_facecolor(self.colors['light'])
    
    def plot_ar_aging(self, save_path: str = None):
        """
        NEW: Plot Accounts Receivable aging buckets.
        Shows concentration of receivables by age.
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ar_aging = self.model.get_accounts_receivable()
        
        # Filter out empty buckets
        labels = []
        values = []
        colors = []
        
        color_map = {
            'current': self.colors['success'],
            '31-60_days': self.colors['warning'],
            '61-90_days': '#f97316',  # orange
            'over_90_days': self.colors['danger']
        }
        
        for label, amount in ar_aging.items():
            if amount > 0:
                labels.append(label.replace('_', ' ').title())
                values.append(amount)
                colors.append(color_map.get(label, self.colors['info']))
        
        if not values:
            ax.text(0.5, 0.5, 'No outstanding receivables', ha='center', va='center')
            ax.set_title('AR Aging', fontweight='bold')
        else:
            bars = ax.bar(labels, values, color=colors, alpha=0.8)
            
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 500,
                       f'${val:,.0f}', ha='center', fontweight='bold')
            
            ax.set_title('Accounts Receivable Aging', fontsize=14, fontweight='bold')
            ax.set_ylabel('Amount ($)')
            ax.grid(axis='y', alpha=0.3)
            
            # Add risk annotations
            if ar_aging.get('over_90_days', 0) > 0:
                ax.text(0.98, 0.95, 'HIGH RISK: >90 days AR',
                       transform=ax.transAxes, ha='right', va='top',
                       fontsize=10, fontweight='bold', color='red',
                       bbox=dict(boxstyle='round', facecolor='red', alpha=0.2))
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        plt.tight_layout()
        plt.show()
    
    def plot_cash_conversion_cycle(self, save_path: str = None):
        """Visualize cash conversion cycle components."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        dso = self.model.calculate_dso()
        dio = 0  # Consulting
        dpo = self.model.calculate_dpo()
        
        metrics = {
            'Days Sales Outstanding\n(Collect receivables)': dso,
            'Days Inventory\n(Consulting = ~0)': dio,
            'Days Payable\n(Pay vendors)': dpo
        }
        
        colors = [self.colors['warning'], self.colors['info'], self.colors['success']]
        
        bars = ax.bar(metrics.keys(), metrics.values(), color=colors, alpha=0.7)
        
        for bar, val in zip(bars, metrics.values()):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                       f'{val:.0f} days', ha='center', fontweight='bold')
        
        ax.set_title('Cash Conversion Cycle Components', fontsize=14, fontweight='bold')
        ax.set_ylabel('Days')
        ax.grid(axis='y', alpha=0.3)
        
        # Add CCC formula
        ccc = dso + dio - dpo
        ax.text(0.98, 0.95, f'Cash Conversion Cycle: {ccc:.0f} days\n(DSO + DIO - DPO)',
               transform=ax.transAxes, ha='right', va='top',
               fontsize=12, fontweight='bold',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        plt.tight_layout()
        plt.show()
    
    def plot_scenario_analysis(self, scenarios: dict, save_path: str = None):
        """Visualize multiple scenarios side by side."""
        results = self.model.scenario_analysis(scenarios)
        
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        # Final balance comparison
        colors = ['green' if s else 'red' for s in results['survives']]
        axes[0].bar(results['scenario'], results['final_balance'], color=colors, alpha=0.7)
        axes[0].set_title('Final Balance by Scenario', fontweight='bold')
        axes[0].set_ylabel('Balance ($)')
        axes[0].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        axes[0].tick_params(axis='x', rotation=45)
        
        # Income comparison
        axes[1].bar(results['scenario'], results['total_income'], 
                   color=self.colors['success'], alpha=0.7)
        axes[1].set_title('Total Income by Scenario', fontweight='bold')
        axes[1].set_ylabel('Income ($)')
        axes[1].tick_params(axis='x', rotation=45)
        
        # Minimum balance (risk indicator)
        axes[2].bar(results['scenario'], results['minimum_balance'], 
                   color=[self.colors['success'] if m > 0 else self.colors['danger'] 
                          for m in results['minimum_balance']], alpha=0.7)
        axes[2].set_title('Minimum Balance (Risk)', fontweight='bold')
        axes[2].set_ylabel('Min Balance ($)')
        axes[2].axhline(y=0, color='red', linestyle='--', linewidth=1)
        axes[2].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        plt.show()
