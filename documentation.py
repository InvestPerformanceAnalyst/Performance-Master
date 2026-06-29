# =====================================================================
# MODULE 4: SPREADSHEET AUTOMATION & COMPILER LAYER
# =====================================================================
import pandas as pd

def export_to_excel(excel_io, master_df, active_days_df, trailing_irr_df, trailing_pivot, ent_pivot, final_breakdowns, final_entity_breakdowns, abs_df, alpha_df, prop_analysis_df):
    """Compiles internal active tables into structured, custom-styled Excel Workbook tabs."""
    with pd.ExcelWriter(excel_io, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Presentation Alignment Palettes
        f_header = workbook.add_format({'bold': True, 'bg_color': '#366092', 'font_color': 'white', 'border': 1, 'align': 'center'})
        f_pct = workbook.add_format({'num_format': '0.00%', 'align': 'right'})
        f_money = workbook.add_format({'num_format': '$#,##0', 'align': 'right'})
        f_mult = workbook.add_format({'num_format': '0.00"x"', 'align': 'center'})
        f_date = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'center'})
        f_val_green = workbook.add_format({'num_format': '0.00%', 'align': 'right', 'font_color': '#00B050', 'bold': True})
        f_val_red = workbook.add_format({'num_format': '0.00%', 'align': 'right', 'font_color': '#C0504D', 'bold': True})

        # Tab 1: Fund Allocation Summary
        ws_sum = workbook.add_worksheet('Performance Summary')
        for c, col in enumerate(master_df.columns): ws_sum.write(0, c, col, f_header)
        for r, row in master_df.iterrows():
            for c, col in enumerate(master_df.columns):
                val = row[col]
                fmt = None
                if any(x in col for x in ['TWR', 'XIRR', 'Return', 'Months', 'Drawdown', 'Volatility']): fmt = f_pct
                elif any(x in col for x in ['Multiple', 'DPI', 'RVPI', 'TVPI']): fmt = f_mult
                elif any(x in col for x in ['Contributions', 'Distributions', 'NAV', 'Fee']): fmt = f_money
                ws_sum.write(r+1, c, "" if pd.isna(val) else val, fmt)
        ws_sum.set_column('A:A', 35); ws_sum.set_column('B:ZZ', 14)

        # Tab 2: Property Operations Mapping (Optional Sub-tab)
        if not prop_analysis_df.empty:
            ws_prop = workbook.add_worksheet('Property Analysis')
            headers = list(prop_analysis_df.columns)
            for c, h in enumerate(headers): ws_prop.write(0, c, h, f_header)
            for r, row in prop_analysis_df.iterrows():
                ws_prop.write(r+1, 0, row['Date'], f_date)
                ws_prop.write(r+1, 1, row['Property Name'])
                ws_prop.write(r+1, 2, row['Type'])
                ws_prop.write(r+1, 3, row['Region'])
                ws_prop.write(r+1, 4, row['Benchmark'])
                ws_prop.write(r+1, 5, row['Property NOI Return'], f_pct)
                ws_prop.write(r+1, 6, row['Benchmark NOI Return'], f_pct)
                ws_prop.write(r+1, 7, row['NOI Value Add'], f_val_green if row['NOI Value Add'] >= 0 else f_val_red)
                ws_prop.write(r+1, 8, row['Property App Return'], f_pct)
                ws_prop.write(r+1, 9, row['Benchmark App Return'], f_pct)
                ws_prop.write(r+1, 10, row['App Value Add'], f_val_green if row['App Value Add'] >= 0 else f_val_red)
            ws_prop.set_column('A:B', 25); ws_prop.set_column('C:E', 15); ws_prop.set_column('F:K', 18)

        # Tab 3 & 4: Attribution Support Worksheets
        if not abs_df.empty: abs_df.to_excel(writer, sheet_name='Absolute Contributors', index=False)
        if not alpha_df.empty: alpha_df.to_excel(writer, sheet_name='Alpha Movers', index=False)
        if not trailing_pivot.empty: trailing_pivot.to_excel(writer, sheet_name='Trailing IRR Data', index=False)