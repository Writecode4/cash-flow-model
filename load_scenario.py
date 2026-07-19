"""
Example: Loading scenarios from different sources.
Demonstrates JSON, CSV, Excel, and interactive input methods.

Usage:
  python load_scenario.py                              # Default sample data
  python load_scenario.py scenario.json                # Load from JSON
  python load_scenario.py scenario.xlsx                # Load from Excel
  python load_scenario.py --csv examples               # Load from CSV directory
  python load_scenario.py --interactive                # Interactive CLI menu
  python load_scenario.py --templates examples         # Generate template files
"""

import sys
from scenario_loader import ScenarioLoader
from generate_dashboard import generate_html_dashboard


def main():
    print("=" * 60)
    print("SCENARIO LOADER - Example")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        # Load from specified source
        source = sys.argv[1]
        
        if source.endswith('.json'):
            print(f"\nLoading from JSON: {source}")
            model = ScenarioLoader.load_from_json(source)
        
        elif source.endswith('.xlsx') or source.endswith('.xls'):
            print(f"\nLoading from Excel: {source}")
            model = ScenarioLoader.load_from_excel(source)
        
        elif source == '--csv':
            # Load from CSV directory
            csv_dir = sys.argv[2] if len(sys.argv) > 2 else 'examples'
            print(f"\nLoading from CSV directory: {csv_dir}")
            model = ScenarioLoader.load_from_csv(
                config_csv=f'{csv_dir}/config_template.csv',
                invoices_csv=f'{csv_dir}/invoices_template.csv',
                expenses_csv=f'{csv_dir}/expenses_template.csv',
                projects_csv=f'{csv_dir}/projects_template.csv'
            )
        
        elif source == '--interactive':
            print("\nStarting interactive mode...")
            model = ScenarioLoader.create_interactive()
        
        elif source == '--templates':
            output_dir = sys.argv[2] if len(sys.argv) > 2 else 'examples'
            ScenarioLoader.generate_templates(output_dir)
            return
        
        else:
            print(f"Unknown source: {source}")
            print("Usage: python load_scenario.py [file.json | file.xlsx | --csv dir | --interactive | --templates dir]")
            return
    
    else:
        # Default: load from sample data
        print("\nNo source specified. Loading default sample data...")
        from sample_data import create_sample_model
        model = create_sample_model()
    
    # Run analysis
    dashboard = model.generate_dashboard_data()
    
    print("\n" + "-" * 60)
    print("ANALYSIS RESULTS")
    print("-" * 60)
    print(f"  Balance:     ${dashboard['current_balance']:>12,.2f}")
    print(f"  DSO:         {dashboard['dso']:>8.1f} days")
    print(f"  Burn Rate:   ${dashboard['burn_rate']:>12,.2f}/month")
    print(f"  Runway:      ", end="")
    if dashboard['runway_months'] == float('inf'):
        print("Indefinite")
    else:
        print(f"{dashboard['runway_months']:.1f} months")
    
    # Export
    model.export_to_excel('scenario_analysis.xlsx')
    print("\nFull report exported to scenario_analysis.xlsx")


if __name__ == '__main__':
    main()
