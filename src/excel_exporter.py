# =====================================================================
# MODULE 4: EXCEL EXPORT ENGINE WITH IN-MEMORY BYTES WRITER REDIRECTION
# =====================================================================
import math
import pandas as pd
import numpy as np

def export_to_excel(excel_io, master_df, active_days_df, irr_val_df, twr_aggregate_df, composite_twr_df, trailing_irr_df, trailing_pivot, ent_pivot, final_breakdowns, final_entity_breakdowns, final_return_distributions, j_curve_export, abs_df, alpha_df, corr_matrices, rolling_corr_df, error_log, disclosure_df, portfolio_sections, brinson_df=pd.DataFrame(), aum_pivot=pd.DataFrame(), decay_df=pd.DataFrame(), prop_analysis_df=pd.DataFrame()):
    def get_aligned_bounds(df, pos_cols, neg_cols, sec_cols=None):
        if sec_cols is None: sec_cols = []
        pos_stack = df[pos_cols].clip(lower=0).sum(axis=1) if pos_cols else pd.Series([0])
        neg_stack = df[neg_cols].clip(upper=0).sum(axis=1) if neg_cols else pd.Series([0])
        p_max_data, p_min_data = max(pos_stack.max(), 1e-5), min(neg_stack.min(), -1e-5)
        s_max_data = max(df[sec_cols].max().max(), 1000 + 1e-5) if sec_cols else 1001
        s_min_data = min(df[sec_cols].min().min(), 1000 - 1e-5) if sec_cols else 999

        def get_nice_tick(val):
            if val <= 0: return 1.0
            mag = 10 ** math.floor(math.log10(val))
            resid = val / mag
            if resid <= 1: return 1.0 * mag
            elif resid <= 2: return 2.0 * mag
            elif resid <= 5: return 5.0 * mag
            else: return 10.0 * mag

        best_waste, best_N_top, best_N_bot, best_p_unit, best_s_unit = float('inf'), 5, 2, 0, 0
        for N_top in range(1, 8):
            for N_bot in range(1, 8):
                p_u = get_nice_tick(max(p_max_data / N_top, abs(p_min_data) / N_bot))
                s_u = get_nice_tick(max((s_max_data - 1000) / N_top, (1000 - s_min_data) / N_bot))
                waste = ((p_u * N_top - p_max_data) + (p_u * N_bot - abs(p_min_data))) / (p_max_data + abs(p_min_data))
                if sec_cols: waste += ((s_u * N_top - (s_max_data - 1000)) + (s_u * N_bot - (1000 - s_min_data))) / ((s_max_data - 1000) + (1000 - s_min_data))
                if waste < best_waste:
                    best_waste, best_N_top, best_N_bot, best_p_unit, best_s_unit = waste, N_top, N_bot, p_u, s_u
        return best_p_unit * best_N_top, -best_p_unit * best_N_bot, best_p_unit, 1000 + best_s_unit * best_N_top, 1000 - best_s_unit * best_N_bot, best_s_unit

    # MODIFIED: Target abstract in-memory byte streams natively
    with pd.ExcelWriter(excel_io, engine='xlsxwriter', engine_kwargs={'options': {'nan_inf_to_errors': True}}) as writer:
        workbook = writer.book

        fmt_super = workbook.add_format({'bold': True, 'bg_color': '#366092', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        fmt_header = workbook.add_format({'bold': True, 'bg_color': '#BFBFBF', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        fmt_bd_title = workbook.add_format({'bold': True, 'font_size': 12})
        fmt_bd_header = workbook.add_format({'bold': True, 'bg_color': '#366092', 'font_color': 'white', 'border': 1, 'align': 'center'})
        fmt_title_period = workbook.add_format({'bold': True, 'bg_color': '#E26B0A', 'font_color': 'white', 'font_size': 12, 'align': 'left', 'valign': 'vcenter'})

        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'center'})
        money_round_fmt = workbook.add_format({'num_format': '$#,##0', 'align': 'right'})
        pct_raw_format = workbook.add_format({'num_format': '0.00%', 'align': 'right'})
        f_val_green = workbook.add_format({'num_format': '0.00%', 'align': 'right', 'font_color': '#00B050', 'bold': True})
        f_val_red = workbook.add_format({'num_format': '0.00%', 'align': 'right', 'font_color': '#C0504D', 'bold': True})

        fmt_str, fmt_acc, fmt_pct, fmt_mult, fmt_int, fmt_num = '', '_($* #,##0_);_($* (#,##0);_($* "-"_);_(@_)', '0.00%', '0.00"x"', '0', '0.00'

        format_cache = {}
        def get_format(bg, fc, bld, nf, wrap=False, align='center'):
            key = (bg, fc, bld, nf, wrap, align)
            if key not in format_cache: format_cache[key] = workbook.add_format({'bg_color': bg, 'font_color': fc, 'bold': bld, 'num_format': nf, 'valign': 'vcenter', 'text_wrap': wrap, 'align': align})
            return format_cache[key]

        # 1. PERFORMANCE SUMMARY
        worksheet_main = workbook.add_worksheet('Performance Summary')
        cols = list(master_df.columns)
        twr_cols = [i for i, c in enumerate(cols) if 'TWR' in c]
        risk_cols = [i for i, c in enumerate(cols) if c in ['Best Quarter', 'Best Quarter Return', 'Worst Quarter', 'Worst Quarter Return', 'Best 12 Months', 'Worst 12 Months', 'Max Drawdown', 'Longest Recovery (Qtrs)', 'Annualized Volatility', 'Beta', 'Correlation (r)', 'R-Squared', 'Sharpe Ratio', 'Information Ratio', 'Downside Capture', 'Up Capture Ratio']]

        if twr_cols: worksheet_main.merge_range(0, 0, 0, twr_cols[0]-1, 'Investment Details & Cash Flow Returns', fmt_super); worksheet_main.merge_range(0, twr_cols[0], 0, twr_cols[-1], 'TWR Metrics', fmt_super)
        if risk_cols: worksheet_main.merge_range(0, risk_cols[0], 0, risk_cols[-1], 'Risk and Resiliency Metrics', fmt_super)

        for col_num, col_name in enumerate(cols): worksheet_main.write(1, col_num, col_name, fmt_header)

        for row_num, row_data in master_df.iterrows():
            asset = str(row_data['Asset Name'])
            bg_color, font_color, is_bold = '#FFFFFF', '#000000', False
            if asset.startswith('---'): bg_color, font_color, is_bold = '#E26B0A', '#FFFFFF', True
            elif 'COMPOSITE' in asset or 'Benchmark' in asset or 'Relative' in asset: bg_color, font_color, is_bold = '#D9D9D9', '#000000', ('COMPOSITE' in asset)

            for col_num, col_name in enumerate(cols):
                val = row_data[col_name]
                nf = fmt_str
                if any(x in col_name for x in ['TWR', 'XIRR', 'Drawdown', 'Volatility', 'Capture', 'Best Quarter Return', 'Worst Quarter Return', 'Best 12 Months', 'Worst 12 Months']): nf = fmt_pct
                elif col_name in ['DPI', 'RVPI', 'TVPI', 'Gross Multiple']: nf = fmt_mult
                elif col_name in ['Sharpe Ratio', 'Information Ratio', 'Beta', 'Correlation (r)', 'R-Squared']: nf = fmt_num
                elif col_name in ['Contributions', 'Distributions', 'Advisory Fee', 'Unrealized Incentive Fee', 'Realized Incentive Fee', 'Ending NAV']: nf = fmt_acc
                elif col_name == 'Longest Recovery (Qtrs)': nf = fmt_int

                cell_fmt = get_format(bg_color, font_color, is_bold, nf)
                if pd.isna(val) or val == "" or (isinstance(val, float) and np.isinf(val)): worksheet_main.write(row_num + 2, col_num, "", cell_fmt)
                else: worksheet_main.write(row_num + 2, col_num, val, cell_fmt)
        worksheet_main.set_column('A:B', 30); worksheet_main.set_column('C:H', 15); worksheet_main.set_column('I:ZZ', 12)

        period_order = ['Quarterly', 'YTD', '1-Year', '3-Year', '5-Year', '10-Year', 'Since Inception']

        # 2. TOP ABSOLUTE MOVERS
        if not abs_df.empty:
            ws_abs = workbook.add_worksheet('Top Absolute Movers')
            ws_abs.set_column('A:A', 40); ws_abs.set_column('B:D', 20)
            r = 0
            for p in period_order:
                sub = abs_df[abs_df['Period'] == p].sort_values('Net Total Contribution', ascending=False)
                if sub.empty: continue
                ws_abs.merge_range(r, 0, r, 3, f"Period: {p} (Sorted Top to Bottom)", fmt_title_period); r += 1
                for c, h in enumerate(['Entity Name', 'Net Income Contribution', 'Net Appreciation Contribution', 'Net Total Contribution']): ws_abs.write(r, c, h, fmt_bd_header)
                r += 1
                for _, row in sub.iterrows():
                    ws_abs.write(r, 0, row['Entity Name'], get_format('#FFFFFF', '#000000', False, fmt_str))
                    ws_abs.write(r, 1, row['Net Income Contribution'], get_format('#FFFFFF', '#000000', False, fmt_pct))
                    ws_abs.write(r, 2, row['Net Appreciation Contribution'], get_format('#FFFFFF', '#000000', False, fmt_pct))
                    ws_abs.write(r, 3, row['Net Total Contribution'], get_format('#FFFFFF', '#000000', True, fmt_pct))
                    r += 1
                r += 2

        # 3. TOP ALPHA MOVERS
        if not alpha_df.empty:
            ws_alpha = workbook.add_worksheet('Top Alpha Movers')
            ws_alpha.set_column('A:A', 40); ws_alpha.set_column('B:D', 20)
            r = 0
            for p in period_order:
                sub = alpha_df[alpha_df['Period'] == p].sort_values('Contribution to Alpha', ascending=False)
                if sub.empty: continue
                ws_alpha.merge_range(r, 0, r, 3, f"Period: {p} (Sorted Top to Bottom)", fmt_title_period); r += 1
                for c, h in enumerate(['Entity Name', 'Entity Contribution to Return', 'Benchmark Equivalent Contribution', 'Contribution to Alpha']): ws_alpha.write(r, c, h, fmt_bd_header)
                r += 1
                for _, row in sub.iterrows():
                    ws_alpha.write(r, 0, row['Entity Name'], get_format('#FFFFFF', '#000000', False, fmt_str))
                    ws_alpha.write(r, 1, row['Entity Contribution to Return'], get_format('#FFFFFF', '#000000', False, fmt_pct))
                    ws_alpha.write(r, 2, row['Benchmark Equivalent Contribution'], get_format('#FFFFFF', '#000000', False, fmt_pct))
                    ws_alpha.write(r, 3, row['Contribution to Alpha'], get_format('#FFFFFF', '#000000', True, fmt_pct))
                    r += 1
                r += 2

        # 4. RETURN BREAKDOWN
        if final_breakdowns:
            ws_bd = workbook.add_worksheet('Return Breakdown')
            ws_bd.set_column('A:A', 15); ws_bd.set_column('B:F', 20)
            r = 0
            for bkdn in final_breakdowns:
                try:
                    p_max, p_min, p_unit, s_max, s_min, s_unit = get_aligned_bounds(bkdn, pos_cols=['Net Investment Income', 'Net Appreciation'], neg_cols=['Net Investment Income', 'Net Appreciation', 'Total Fees'], sec_cols=['Growth of $1,000', 'Benchmark Growth of $1,000'])
                    bm_name = bkdn['Benchmark Name'].iloc[0]
                    is_sector = "SECTOR COMPOSITE" in bkdn['Composite Name'].iloc[0]
                    col_inc, col_app, col_fee = ('#8064A2', '#4BACC6', '#A5A5A5') if is_sector else ('#4F81BD', '#F79646', '#A5A5A5')
                    col_port_line, col_bm_line = ('#B3A2C7', '#31859B') if is_sector else ('#FFC000', '#00B050')

                    ws_bd.write(r, 0, bkdn['Composite Name'].iloc[0], fmt_bd_title); r += 1
                    for c, h in enumerate(['Date', 'Net Investment Income', 'Net Appreciation', 'Total Fees', 'Growth of $1,000', f'{bm_name} Growth']): ws_bd.write(r, c, h, fmt_bd_header)
                    r += 1; d_start = r
                    for _, row in bkdn.iterrows():
                        ws_bd.write(r, 0, row['Date'], date_format); ws_bd.write(r, 1, row['Net Investment Income'], money_round_fmt); ws_bd.write(r, 2, row['Net Appreciation'], money_round_fmt); ws_bd.write(r, 3, row['Total Fees'], money_round_fmt); ws_bd.write(r, 4, row['Growth of $1,000'], money_round_fmt); ws_bd.write(r, 5, row['Benchmark Growth of $1,000'], money_round_fmt); r += 1

                    cc = workbook.add_chart({'type': 'column', 'subtype': 'stacked'}); cl = workbook.add_chart({'type': 'line'})
                    cc.add_series({'name': ['Return Breakdown', d_start - 1, 1], 'categories': ['Return Breakdown', d_start, 0, r - 1, 0], 'values': ['Return Breakdown', d_start, 1, r - 1, 1], 'fill': {'color': col_inc}, 'gap': 40})
                    cc.add_series({'name': ['Return Breakdown', d_start - 1, 2], 'categories': ['Return Breakdown', d_start, 0, r - 1, 0], 'values': ['Return Breakdown', d_start, 2, r - 1, 2], 'fill': {'color': col_app}})
                    cc.add_series({'name': ['Return Breakdown', d_start - 1, 3], 'categories': ['Return Breakdown', d_start, 0, r - 1, 0], 'values': ['Return Breakdown', d_start, 3, r - 1, 3], 'fill': {'color': col_fee}})
                    cl.add_series({'name': ['Return Breakdown', d_start - 1, 4], 'categories': ['Return Breakdown', d_start, 0, r - 1, 0], 'values': ['Return Breakdown', d_start, 4, r - 1, 4], 'line': {'color': col_port_line, 'width': 2.5}, 'y2_axis': True})
                    cl.add_series({'name': ['Return Breakdown', d_start - 1, 5], 'categories': ['Return Breakdown', d_start, 0, r - 1, 0], 'values': ['Return Breakdown', d_start, 5, r - 1, 5], 'line': {'color': col_bm_line, 'width': 2.25, 'dash_type': 'dash'}, 'y2_axis': True})

                    cc.combine(cl); cc.set_title({'name': f"{bkdn['Composite Name'].iloc[0]}\nReturn Component Breakdown ($)", 'name_font': {'size': 12, 'bold': True}}); cc.set_x_axis({'name': 'Quarter', 'date_axis': True})
                    cc.set_y_axis({'name': 'Amount ($)', 'min': p_min, 'max': p_max, 'major_unit': p_unit, 'major_gridlines': {'visible': True, 'line': {'color': '#D9D9D9', 'dash_type': 'dash'}}})
                    cc.set_y2_axis({'name': 'Growth of $1,000', 'min': s_min, 'max': s_max, 'major_unit': s_unit, 'crossing': s_min})
                    cc.set_size({'width': 750, 'height': 400}); cc.set_legend({'position': 'bottom'})
                    ws_bd.insert_chart(d_start - 2, 7, cc); r += 3
                except Exception: pass

        # 5. ENTITY BREAKDOWN
        if final_entity_breakdowns:
            ws_eb = workbook.add_worksheet('Entity Breakdown')
            ws_eb.set_column('A:A', 15); ws_eb.set_column('B:Z', 18)
            r = 0
            fund_colors = ['#4F81BD', '#F79646', '#9BBB59', '#C0504D', '#D99694', '#95B3D7', '#E26B0A', '#8064A2', '#4BACC6']
            sector_colors = ['#8064A2', '#4BACC6', '#B3A2C7', '#31859B', '#7030A0', '#0070C0', '#4F81BD', '#F79646', '#9BBB59']

            for eb in final_entity_breakdowns:
                try:
                    df_eb, ents = eb['Data'], eb['Entities']
                    p_max, p_min, p_unit, s_max, s_min, s_unit = get_aligned_bounds(df_eb, pos_cols=ents, neg_cols=ents, sec_cols=['Growth of $1,000', 'Benchmark Growth of $1,000'])
                    bm_name = eb['Benchmark Name']
                    is_sector = "SECTOR COMPOSITE" in eb['Composite Name']
                    colors = sector_colors if is_sector else fund_colors
                    col_port_line, col_bm_line = ('#B3A2C7', '#31859B') if is_sector else ('#FFC000', '#00B050')

                    ws_eb.write(r, 0, eb['Composite Name'], fmt_bd_title); r += 1
                    for c, h in enumerate(['Date'] + ents + ['Growth of $1,000', f'{bm_name} Growth']): ws_eb.write(r, c, h, fmt_bd_header)
                    r += 1; d_start = r
                    for _, row in df_eb.iterrows():
                        ws_eb.write(r, 0, row['Date'], date_format)
                        for c, e in enumerate(ents): ws_eb.write(r, c + 1, row[e], money_round_fmt)
                        ws_eb.write(r, len(ents) + 1, row['Growth of $1,000'], money_round_fmt); ws_eb.write(r, len(ents) + 2, row['Benchmark Growth of $1,000'], money_round_fmt); r += 1

                    ce = workbook.add_chart({'type': 'column', 'subtype': 'stacked'}); cle = workbook.add_chart({'type': 'line'})
                    for i, e in enumerate(ents):
                        series_dict = {'name': ['Entity Breakdown', d_start - 1, i + 1], 'categories': ['Entity Breakdown', d_start, 0, r - 1, 0], 'values': ['Entity Breakdown', d_start, i + 1, r - 1, i + 1], 'fill': {'color': colors[i % len(colors)]}}
                        if i == 0: series_dict['gap'] = 40
                        ce.add_series(series_dict)

                    cle.add_series({'name': ['Entity Breakdown', d_start - 1, len(ents) + 1], 'categories': ['Entity Breakdown', d_start, 0, r - 1, 0], 'values': ['Entity Breakdown', d_start, len(ents) + 1, r - 1, len(ents) + 1], 'line': {'color': col_port_line, 'width': 2.5}, 'y2_axis': True})
                    cle.add_series({'name': ['Entity Breakdown', d_start - 1, len(ents) + 2], 'categories': ['Entity Breakdown', d_start, 0, r - 1, 0], 'values': ['Entity Breakdown', d_start, len(ents) + 2, r - 1, len(ents) + 2], 'line': {'color': col_bm_line, 'width': 2.25, 'dash_type': 'dash'}, 'y2_axis': True})

                    ce.combine(cle); ce.set_title({'name': f"{eb['Composite Name']}\nEntity Net Return Attribution ($)", 'name_font': {'size': 12, 'bold': True}}); ce.set_x_axis({'name': 'Quarter', 'date_axis': True})
                    ce.set_y_axis({'name': 'Net Return ($)', 'min': p_min, 'max': p_max, 'major_unit': p_unit, 'major_gridlines': {'visible': True, 'line': {'color': '#D9D9D9', 'dash_type': 'dash'}}})
                    ce.set_y2_axis({'name': 'Growth of $1,000', 'min': s_min, 'max': s_max, 'major_unit': s_unit, 'crossing': s_min})
                    ce.set_size({'width': 750, 'height': 400}); ce.set_legend({'position': 'bottom'})
                    ws_eb.insert_chart(d_start - 2, len(ents) + 4, ce); r += 3
                except Exception: pass

        # 6. QUARTERLY RETURN COMPONENTS (DISTRIBUTION)
        if final_return_distributions:
            ws_rd = workbook.add_worksheet('Quarterly Return Components')
            ws_rd.set_column('A:A', 15); ws_rd.set_column('B:E', 20)
            r = 0
            for rd in final_return_distributions:
                try:
                    comp_name, bm_name = rd['Composite Name'].iloc[0], rd['Benchmark Name'].iloc[0]
                    col_comp_inc, col_comp_app, col_bm = '#4F81BD', '#F79646', '#A5A5A5'

                    ws_rd.write(r, 0, f"{comp_name} - Income & Appreciation vs Benchmark", fmt_bd_title); r += 1
                    for c, h in enumerate(['Date', 'Composite Income', f'{bm_name} Income', 'Composite Appreciation', f'{bm_name} Appreciation']): ws_rd.write(r, c, h, fmt_bd_header)
                    r += 1; d_start = r

                    for _, row in rd.iterrows():
                        ws_rd.write(r, 0, row['Date'], date_format); ws_rd.write(r, 1, row['Gross Income Return'], pct_raw_format); ws_rd.write(r, 2, row['BM_Inc_Ret'], pct_raw_format); ws_rd.write(r, 3, row['Gross Appreciation Return'], pct_raw_format); ws_rd.write(r, 4, row['BM_App_Ret'], pct_raw_format); r += 1

                    c_inc = workbook.add_chart({'type': 'column'})
                    c_inc.add_series({'name': ['Quarterly Return Components', d_start - 1, 1], 'categories': ['Quarterly Return Components', d_start, 0, r - 1, 0], 'values': ['Quarterly Return Components', d_start, 1, r - 1, 1], 'fill': {'color': col_comp_inc}, 'gap': 30})
                    c_inc.add_series({'name': ['Quarterly Return Components', d_start - 1, 2], 'categories': ['Quarterly Return Components', d_start, 0, r - 1, 0], 'values': ['Quarterly Return Components', d_start, 2, r - 1, 2], 'fill': {'color': col_bm}})
                    c_inc.set_title({'name': f'{comp_name}\nIncome Return vs Benchmark'}); c_inc.set_x_axis({'date_axis': True}); c_inc.set_y_axis({'num_format': '0.00%'})

                    c_app = workbook.add_chart({'type': 'column'})
                    c_app.add_series({'name': ['Quarterly Return Components', d_start - 1, 3], 'categories': ['Quarterly Return Components', d_start, 0, r - 1, 0], 'values': ['Quarterly Return Components', d_start, 3, r - 1, 3], 'fill': {'color': col_comp_app}, 'gap': 30})
                    c_app.add_series({'name': ['Quarterly Return Components', d_start - 1, 4], 'categories': ['Quarterly Return Components', d_start, 0, r - 1, 0], 'values': ['Quarterly Return Components', d_start, 4, r - 1, 4], 'fill': {'color': col_bm}})
                    c_app.set_title({'name': f'{comp_name}\nAppreciation Return vs Benchmark'}); c_app.set_x_axis({'date_axis': True}); c_app.set_y_axis({'num_format': '0.00%'})

                    ws_rd.insert_chart(d_start - 2, 6, c_inc); ws_rd.insert_chart(d_start - 2, 14, c_app); r += 3
                except Exception: pass

        # 7. RISK & CORRELATION
        if not rolling_corr_df.empty:
            rolling_corr_df.to_excel(writer, sheet_name='Rolling Corr Data', index=False)
            writer.sheets['Rolling Corr Data'].set_column('A:A', 15, date_format)

        rr_df = pd.DataFrame()
        if 'Annualized Volatility' in master_df.columns and 'Gross XIRR' in master_df.columns:
            rr_df = master_df[['Asset Name', 'Annualized Volatility', 'Gross XIRR']].copy()
            rr_df = rr_df[~rr_df['Asset Name'].astype(str).str.startswith('---')].dropna(subset=['Annualized Volatility', 'Gross XIRR'])
            if not active_days_df.empty and 'Total Active Days' in active_days_df.columns:
                rr_df['Active Days'] = rr_df['Asset Name'].map(active_days_df.set_index('Entity Name')['Total Active Days'].to_dict())
                rr_df = rr_df[(rr_df['Active Days'] >= 365) | (rr_df['Active Days'].isna())]

        if corr_matrices or not rr_df.empty:
            ws_rc = workbook.add_worksheet('Risk & Correlation')
            ws_rc.set_column('A:A', 35); ws_rc.set_column('B:ZZ', 15)
            r = 0

            if not rr_df.empty:
                ws_rr_data = workbook.add_worksheet('Risk Return Data')
                ws_rr_data.hide()
                ws_rr_data.write(0, 0, 'Asset Name'); ws_rr_data.write(0, 1, 'Volatility'); ws_rr_data.write(0, 2, 'Gross IRR')
                for idx, row in enumerate(rr_df.itertuples()):
                    ws_rr_data.write(idx + 1, 0, str(row[1])); ws_rr_data.write(idx + 1, 1, float(row[2])); ws_rr_data.write(idx + 1, 2, float(row[3]))

                chart_rr = workbook.add_chart({'type': 'scatter'})
                for idx in range(len(rr_df)):
                    chart_rr.add_series({'name': ['Risk Return Data', idx + 1, 0, idx + 1, 0], 'categories': ['Risk Return Data', idx + 1, 1, idx + 1, 1], 'values': ['Risk Return Data', idx + 1, 2, idx + 1, 2], 'marker': {'type': 'circle', 'size': 7}, 'data_labels': {'series_name': True, 'position': 'right', 'font': {'size': 9}}})
                chart_rr.set_x_axis({'num_format': '0.00%'}); chart_rr.set_y_axis({'num_format': '0.00%'})
                ws_rc.insert_chart(r, 0, chart_rr); r += 26

            for cm in corr_matrices:
                try:
                    c_name, mat, bm_name = cm['Composite Name'], cm['Matrix'], cm['Benchmark Name']
                    ws_rc.write(r, 0, f"{c_name} - Cross-Correlation Matrix", fmt_bd_title); r += 1
                    for c, h in enumerate(['Entity'] + list(mat.columns)): ws_rc.write(r, c, h, fmt_bd_header)
                    r += 1; start_r = r
                    for idx, row in mat.iterrows():
                        ws_rc.write(r, 0, str(idx), get_format('#FFFFFF', '#000000', True, fmt_str, align='left'))
                        for c, val in enumerate(row): ws_rc.write(r, c + 1, "" if pd.isna(val) or np.isinf(val) else float(val), get_format('#FFFFFF', '#000000', False, fmt_num))
                        r += 1
                    ws_rc.conditional_format(start_r, 1, r - 1, len(mat.columns), {'type': '3_color_scale', 'min_color': '#FF0000', 'mid_color': '#FFFFFF', 'max_color': '#00B050'})
                    r += 2
                except Exception: pass

        # 8. TRAILING IRR CHART
        if not trailing_pivot.empty:
            trailing_pivot.to_excel(writer, sheet_name='Trailing IRR Chart', index=False)
            ws_tc = writer.sheets['Trailing IRR Chart']
            ws_tc.set_column('A:A', 15, date_format); ws_tc.set_column('B:Z', 25, pct_raw_format)
            chart_tc = workbook.add_chart({'type': 'line'})
            for i, c in enumerate(trailing_pivot.columns[1:], start=1): chart_tc.add_series({'name': ['Trailing IRR Chart', 0, i], 'categories': ['Trailing IRR Chart', 1, 0, len(trailing_pivot), 0], 'values': ['Trailing IRR Chart', 1, i, len(trailing_pivot), i]})
            ws_tc.insert_chart('I2', chart_tc)

        # 9. ENTITY TRAILING IRR
        if not ent_pivot.empty:
            ent_pivot.to_excel(writer, sheet_name='Entity Trailing IRR', index=False)
            ws_ec = writer.sheets['Entity Trailing IRR']
            ws_ec.set_column('A:A', 15, date_format); ws_ec.set_column('B:Z', 25, pct_raw_format)

        # 10. J CURVE
        if not j_curve_export.empty:
            j_curve_export.to_excel(writer, sheet_name='J Curve', index=False)
            ws_j = writer.sheets['J Curve']
            ws_j.set_column('A:A', 12, date_format); ws_j.set_column('B:G', 18, money_round_fmt)

        # 11. AUM GROWTH
        if not aum_pivot.empty:
            ws_aum = workbook.add_worksheet('AUM Growth')
            ws_aum.set_column('A:A', 15, date_format); ws_aum.set_column('B:Z', 20, money_round_fmt)
            headers = ['Date'] + [c for c in aum_pivot.columns if c != 'Date']
            for c, h in enumerate(headers): ws_aum.write(0, c, h, fmt_bd_header)
            r = 1
            for _, row in aum_pivot.iterrows():
                ws_aum.write(r, 0, row['Date'], date_format)
                for c_idx, col_name in enumerate(headers[1:], start=1): ws_aum.write(r, c_idx, row[col_name], money_round_fmt)
                r += 1

        # 12. BRINSON ATTRIBUTION
        if not brinson_df.empty:
            ws_brin = workbook.add_worksheet('Sector Attribution')
            ws_brin.set_column('A:A', 25); ws_brin.set_column('B:H', 18)
            r = 0
            for p in ['QTD', 'YTD', '1-Year']:
                sub = brinson_df[brinson_df['Period'] == p]
                if sub.empty: continue
                ws_brin.merge_range(r, 0, r, 7, f"Period: {p}", fmt_title_period); r += 1
                for c, h in enumerate(['Sector', 'Portfolio Weight', 'Benchmark Weight', 'Portfolio Return', 'Benchmark Return', 'Allocation Effect', 'Selection Effect', 'Total Value Add']): ws_brin.write(r, c, h, fmt_bd_header)
                r += 1
                for _, row in sub.iterrows():
                    ws_brin.write(r, 0, row['Sector'], get_format('#FFFFFF', '#000000', True, fmt_str, align='left'))
                    ws_brin.write(r, 1, row['Port Weight'], get_format('#FFFFFF', '#000000', False, fmt_pct))
                    ws_brin.write(r, 2, row['BM Weight'], get_format('#FFFFFF', '#000000', False, fmt_pct))
                    ws_brin.write(r, 3, row['Port Return'], get_format('#FFFFFF', '#000000', False, fmt_pct))
                    ws_brin.write(r, 4, row['BM Return'], get_format('#FFFFFF', '#000000', False, fmt_pct))
                    ws_brin.write(r, 5, row['Allocation Effect'], get_format('#FFFFFF', '#000000', False, fmt_pct))
                    ws_brin.write(r, 6, row['Selection Effect'], get_format('#FFFFFF', '#000000', False, fmt_pct))
                    ws_brin.write(r, 7, row['Total Value Add'], get_format('#FFFFFF', '#000000', True, fmt_pct))
                    r += 1
                r += 3

        # 13. DUAL IRR DECAY MATRIX
        if not decay_df.empty:
            ws_decay = workbook.add_worksheet('IRR Decay Analysis')
            ws_decay.set_column('A:A', 35); ws_decay.set_column('B:K', 15); ws_decay.set_column('M:M', 35); ws_decay.set_column('N:U', 20)
            r = 0
            ws_decay.merge_range(r, 0, r, 10, "IRR DECAY ANALYSIS (Assuming Flat NAV)", fmt_bd_title)
            ws_decay.merge_range(r, 12, r, 20, "REQUIRED VALUE CREATION TO MAINTAIN IRR ($)", fmt_bd_title)
            r += 2
            
            headers_1 = ['Asset Name', 'Current NAV', 'Current Gross IRR', '+1 Qtr Hold', '+1 Year Hold', '+2 Year Hold', '+3 Year Hold', '+5 Year Hold', '+10 Year Hold', '+15 Year Hold']
            for c, h in enumerate(headers_1): ws_decay.write(r, c, h, fmt_bd_header)
            headers_2 = ['Asset Name', 'Req Value (+1 Qtr)', 'Req Value (+1 Year)', 'Req Value (+2 Year)', 'Req Value (+3 Year)', 'Req Value (+5 Year)', 'Req Value (+10 Year)', 'Req Value (+15 Year)']
            for c, h in enumerate(headers_2): ws_decay.write(r, c + 12, h, fmt_bd_header)
            r += 1; start_data_row = r + 1

            for _, row in decay_df.iterrows():
                asset = str(row['Asset Name'])
                bg_color, font_color, is_bold = ('#D9D9D9', '#000000', True) if 'COMPOSITE' in asset else ('#FFFFFF', '#000000', False)
                ws_decay.write(r, 0, asset, get_format(bg_color, font_color, is_bold, fmt_str, align='left'))
                
                def write_safe(col_idx, val, fmt):
                    ws_decay.write(r, col_idx, "" if (pd.isna(val) or np.isinf(val)) else val, get_format(bg_color, font_color, is_bold, fmt))

                write_safe(1, row.get('Current NAV'), fmt_acc); write_safe(2, row.get('Current Gross IRR'), fmt_pct)
                write_safe(3, row.get('+1 Quarter Hold'), fmt_pct); write_safe(4, row.get('+1 Year Hold'), fmt_pct)
                write_safe(5, row.get('+2 Year Hold'), fmt_pct); write_safe(6, row.get('+3 Year Hold'), fmt_pct)
                write_safe(7, row.get('+5 Year Hold'), fmt_pct); write_safe(8, row.get('+10 Year Hold'), fmt_pct)
                write_safe(9, row.get('+15 Year Hold'), fmt_pct)

                ws_decay.write(r, 12, asset, get_format(bg_color, font_color, is_bold, fmt_str, align='left'))
                write_safe(13, row.get('Req Value (+1 Qtr)'), fmt_acc); write_safe(14, row.get('Req Value (+1 Year)'), fmt_acc)
                write_safe(15, row.get('Req Value (+2 Year)'), fmt_acc); write_safe(16, row.get('Req Value (+3 Year)'), fmt_acc)
                write_safe(17, row.get('Req Value (+5 Year)'), fmt_acc); write_safe(18, row.get('Req Value (+10 Year)'), fmt_acc)
                write_safe(19, row.get('Req Value (+15 Year)'), fmt_acc)
                r += 1
            ws_decay.conditional_format(start_data_row-1, 2, r-1, 9, {'type': '3_color_scale', 'min_color': '#FFC7CE', 'mid_color': '#FFEB9C', 'max_color': '#C6EFCE'})

        # --- 14. PROPERTY LEVEL COMPONENT DIAGNOSTICS TAB ---
        if not prop_analysis_df.empty:
            ws_prop = workbook.add_worksheet('Property Analysis')
            headers = list(prop_analysis_df.columns)
            for c, h in enumerate(headers): ws_prop.write(0, c, h, fmt_bd_header)
            for r_p, row in prop_analysis_df.iterrows():
                ws_prop.write(r_p+1, 0, row['Date'], date_format); ws_prop.write(r_p+1, 1, row['Property Name'])
                ws_prop.write(r_p+1, 2, row['Type']); ws_prop.write(r_p+1, 3, row['Region']); ws_prop.write(r_p+1, 4, row['Benchmark'])
                ws_prop.write(r_p+1, 5, row['Property NOI Return'], fmt_pct); ws_prop.write(r_p+1, 6, row['Benchmark NOI Return'], fmt_pct)
                ws_prop.write(r_p+1, 7, row['NOI Value Add'], f_val_green if row['NOI Value Add'] >= 0 else f_val_red)
                ws_prop.write(r_p+1, 8, row['Property App Return'], fmt_pct); ws_prop.write(r_p+1, 9, row['Benchmark App Return'], fmt_pct)
                ws_prop.write(r_p+1, 10, row['App Value Add'], f_val_green if row['App Value Add'] >= 0 else f_val_red)
            ws_prop.set_column('A:B', 25); ws_prop.set_column('C:E', 15); ws_prop.set_column('F:K', 18)

        # 15. SUPPORT RECORDS & LOGS
        if not irr_val_df.empty: irr_val_df.to_excel(writer, sheet_name='IRR Validation', index=False)
        if not active_days_df.empty: active_days_df.to_excel(writer, sheet_name='Active Days', index=False)
        if not error_log:
            pd.DataFrame([{'Status': 'All modules executed successfully.'}]).to_excel(writer, sheet_name='Error Log', index=False)

        if not disclosure_df.empty:
            ws_disc = workbook.add_worksheet('Disclosures')
            ws_disc.set_column('A:A', 40); ws_disc.set_column('B:B', 120)
            for r_d, row in disclosure_df.iterrows():
                ws_disc.write(r_d, 0, row['Topic'], fmt_bd_header if row['Description'] else fmt_bd_title)
                if row['Description']: ws_disc.write(r_d, 1, row['Description'], get_format('#FFFFFF', '#000000', False, fmt_str, wrap=True, align='left'))

        # Set Tab Colors
        green_tabs = ['Performance Summary', 'Top Absolute Movers', 'Top Alpha Movers', 'Return Breakdown', 'Entity Breakdown', 'Quarterly Return Components', 'Risk & Correlation', 'Trailing IRR Chart', 'Property Analysis', 'Sector Attribution', 'IRR Decay Analysis']
        for name, sheet in writer.sheets.items():
            if name in green_tabs: sheet.set_tab_color('#00B050')
            elif name == 'Error Log': sheet.set_tab_color('#FF0000')
            elif name == 'Disclosures': sheet.set_tab_color('#808080')
