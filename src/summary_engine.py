# =====================================================================
# MODULE 2: PRIMARY COMPOSITE SUMMARY AGGREGATION CORE
# =====================================================================
import pandas as pd
import numpy as np
from src.math_core import xirr_custom, get_period_twr, annualize_return_exact_days, calc_6_components, chain_link

def build_performance_summary(cf_df, twr_df, bm_df, config_df, investor_name, error_log, REPORTING_DATE, sec_bm=pd.DataFrame()):
    rf_cols = [c for c in config_df.columns if str(c).strip().lower() == 'risk free rate']
    annual_rf_rate = float(config_df[rf_cols[0]].dropna().iloc[0]) if rf_cols and not config_df[rf_cols[0]].dropna().empty else 0.04
    RISK_FREE_RATE_QTR = annual_rf_rate / 4.0

    if 'Entity Name' in config_df.columns and 'Entity' not in config_df.columns:
        config_df.rename(columns={'Entity Name': 'Entity'}, inplace=True)
    elif 'Entity' not in config_df.columns:
        error_log.append({'Module': 'Configuration', 'Entity/Group': 'Global', 'Error Details': "Missing Entity/Entity Name key allocations."})
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), []

    all_entities = config_df['Entity'].dropna().unique().tolist()
    portfolio_sections = [("ALL INVESTMENTS", all_entities)]

    for group_name, group_data in config_df.groupby('Composite Grouping'):
        portfolio_sections.append((str(group_name).replace(" COMPOSITE", "").strip(), group_data['Entity'].tolist()))

    if 'propType' in config_df.columns:
        config_df['propType_clean'] = config_df['propType'].fillna('Other').replace('Land', 'Other')
        for sector_name, sector_data in config_df.groupby('propType_clean'):
            portfolio_sections.append((f"{str(sector_name).upper()} SECTOR", sector_data['Entity'].tolist()))

    if not sec_bm.empty and 'Date' not in sec_bm.columns:
        try:
            sec_bm['Date'] = sec_bm['yyq'].apply(lambda yyq: pd.to_datetime(f"{int(str(yyq)[:4])}-{int(str(yyq)[4])*3}-01") + pd.offsets.MonthEnd(0))
            sec_bm['GrossTotalReturn'] = sec_bm['tret'] - 1.0
        except Exception: pass

    indiv_twr = twr_df.groupby(['Entity Name', 'Date']).agg({
        'Gross Investment Income Minus Fees': 'sum', 'Total Gross Appreciation': 'sum',
        'Net Investment Income': 'sum', 'Net Appreciation': 'sum', 'Denominator': 'sum'
    }).reset_index().sort_values(['Entity Name', 'Date'])
    indiv_twr = calc_6_components(indiv_twr)

    composite_twr_dfs = []
    for title, assets in portfolio_sections:
        comp = twr_df[twr_df['Entity Name'].isin(assets)].groupby('Date').agg({
            'Gross Investment Income Minus Fees': 'sum', 'Total Gross Appreciation': 'sum',
            'Net Investment Income': 'sum', 'Net Appreciation': 'sum', 'Denominator': 'sum'
        }).reset_index().sort_values('Date')
        if not comp.empty:
            comp['Entity Name'] = f'TOTAL {title} COMPOSITE'
            composite_twr_dfs.append(calc_6_components(comp))

    composite_twr_df = pd.concat(composite_twr_dfs, ignore_index=True) if composite_twr_dfs else pd.DataFrame()
    twr_aggregate_df = pd.concat([indiv_twr, composite_twr_df], ignore_index=True)

    active_days_list, irr_validation_list, report_data = [], [], []
    processed_entities_for_logs = set()

    def get_bm_row(slice_bm, bm_name, start_date, days_active, date_col, ret_col, net_col):
        slice_bm = slice_bm[(slice_bm[date_col] >= start_date) & (slice_bm[date_col] <= REPORTING_DATE)].sort_values(date_col)
        bm_q_curr = slice_bm[slice_bm[date_col] == REPORTING_DATE]
        bm_drawdowns = (1 + slice_bm[ret_col]).cumprod() / (1 + slice_bm[ret_col]).cumprod().cummax() - 1

        if not slice_bm.empty and slice_bm[ret_col].notna().any():
            bm_best_q_idx = slice_bm[ret_col].idxmax()
            b_date_bm = slice_bm.loc[bm_best_q_idx, date_col]
            bm_best_q_date, bm_best_q_ret = f"{b_date_bm.year}-Q{b_date_bm.quarter}", slice_bm.loc[bm_best_q_idx, ret_col]

            bm_worst_q_idx = slice_bm[ret_col].idxmin()
            w_date_bm = slice_bm.loc[bm_worst_q_idx, date_col]
            bm_worst_q_date, bm_worst_q_ret = f"{w_date_bm.year}-Q{w_date_bm.quarter}", slice_bm.loc[bm_worst_q_idx, ret_col]

            if len(slice_bm) >= 4:
                bm_roll = slice_bm[ret_col].rolling(window=4).apply(lambda x: np.prod(1+x)-1, raw=False)
                bm_best_1yr, bm_worst_1yr = bm_roll.max(), bm_roll.min()
            else: bm_best_1yr, bm_worst_1yr = np.nan, np.nan
        else:
            bm_best_q_date, bm_best_q_ret, bm_worst_q_date, bm_worst_q_ret, bm_best_1yr, bm_worst_1yr = None, np.nan, None, np.nan, np.nan, np.nan

        bm_sharpe = ( (slice_bm[ret_col] - RISK_FREE_RATE_QTR).mean() / (slice_bm[ret_col] - RISK_FREE_RATE_QTR).std() ) * np.sqrt(4) if len(slice_bm) > 1 and (slice_bm[ret_col] - RISK_FREE_RATE_QTR).std() != 0 else np.nan

        return {
            'Asset Name': bm_name, 'Investor': '',
            'Quarterly Gross TWR': bm_q_curr.iloc[0][ret_col] if not bm_q_curr.empty else np.nan,
            'YTD Gross TWR': get_period_twr(slice_bm, ret_col, REPORTING_DATE, date_col=date_col, ytd=True),
            '1-year Gross TWR': get_period_twr(slice_bm, ret_col, REPORTING_DATE, date_col=date_col, years=1),
            '3-year Gross TWR': get_period_twr(slice_bm, ret_col, REPORTING_DATE, date_col=date_col, years=3),
            '5-year Gross TWR': get_period_twr(slice_bm, ret_col, REPORTING_DATE, date_col=date_col, years=5),
            'Since Inception Gross TWR': annualize_return_exact_days(chain_link(slice_bm[ret_col]), days_active),
            'Quarterly Net TWR': bm_q_curr.iloc[0][net_col] if not bm_q_curr.empty else np.nan,
            'YTD Net TWR': get_period_twr(slice_bm, net_col, REPORTING_DATE, date_col=date_col, ytd=True),
            '1-year Net TWR': get_period_twr(slice_bm, net_col, REPORTING_DATE, date_col=date_col, years=1),
            '3-year Net TWR': get_period_twr(slice_bm, net_col, REPORTING_DATE, date_col=date_col, years=3),
            '5-year Net TWR': get_period_twr(slice_bm, net_col, REPORTING_DATE, date_col=date_col, years=5),
            'Since Inception Net TWR': annualize_return_exact_days(chain_link(slice_bm[net_col]), days_active),
            'Best Quarter': bm_best_q_date, 'Best Quarter Return': bm_best_q_ret,
            'Worst Quarter': bm_worst_q_date, 'Worst Quarter Return': bm_worst_q_ret,
            'Best 12 Months': bm_best_1yr, 'Worst 12 Months': bm_worst_1yr,
            'Max Drawdown': bm_drawdowns.min() if not bm_drawdowns.empty else np.nan,
            'Longest Recovery (Qtrs)': ((bm_drawdowns < 0).astype(int).groupby((bm_drawdowns == 0).astype(int).cumsum()).sum()).max() if not bm_drawdowns.empty else 0,
            'Annualized Volatility': slice_bm[ret_col].std() * np.sqrt(4) if len(slice_bm) > 1 else np.nan,
            'Beta': 1.00, 'Correlation (r)': 1.00, 'R-Squared': 1.00,
            'Sharpe Ratio': bm_sharpe, 'Information Ratio': np.nan,
            'Downside Capture': 1.0, 'Up Capture Ratio': 1.0
        }

    def get_performance_row(entities, name, is_composite=False):
        try:
            sub_cf = cf_df[cf_df['Entity Name'].isin(entities)].copy()
            q_data = composite_twr_df[composite_twr_df['Entity Name'] == name].copy() if is_composite else indiv_twr[indiv_twr['Entity Name'] == name].copy()
            if sub_cf.empty or q_data.empty: return None

            min_date, max_date = sub_cf['Effective Date'].min(), sub_cf['Effective Date'].max()
            days_active = (max_date - min_date).days + 1

            irr_mask = ~((sub_cf['Ending NAV'] > 0) & (sub_cf['Effective Date'] != max_date))
            irr_data = sub_cf[irr_mask].groupby('Effective Date').agg({'Gross Cash Flow': 'sum', 'Net Cash Flow': 'sum'}).reset_index()
            g_irr = xirr_custom(irr_data['Effective Date'].tolist(), irr_data['Gross Cash Flow'].tolist(), guess=0.01)
            n_irr = xirr_custom(irr_data['Effective Date'].tolist(), irr_data['Net Cash Flow'].tolist(), guess=0.01)

            if name not in processed_entities_for_logs:
                active_days_list.append({'Entity Name': name, 'First Active Date': min_date.date() if pd.notnull(min_date) else None, 'Last Active Date': max_date.date() if pd.notnull(max_date) else None, 'Total Active Days': days_active})
                audit_df = irr_data[['Effective Date', 'Gross Cash Flow', 'Net Cash Flow']].copy()
                audit_df.insert(0, 'Asset / Composite Name', name)
                irr_validation_list.append(audit_df)
                processed_entities_for_logs.add(name)

            contribs, distros = sub_cf['Contributions'].sum(), sub_cf['Distributions'].sum()
            math_nav = sub_cf[sub_cf['Effective Date'] == max_date]['Ending NAV'].sum()
            display_nav = math_nav if max_date == REPORTING_DATE else np.nan

            dpi = distros / contribs if contribs > 0 else np.nan
            rvpi = math_nav / contribs if contribs > 0 else np.nan
            tvpi = (distros + math_nav) / contribs if contribs > 0 else np.nan

            q_curr = q_data[q_data['Date'] == REPORTING_DATE]
            cum_rets = (1 + q_data['Gross Total Return']).cumprod()
            drawdowns = cum_rets / cum_rets.cummax() - 1

            bm_slice = bm_df[(bm_df['Period'] >= q_data['Date'].min()) & (bm_df['Period'] <= REPORTING_DATE)]
            merged_rets = pd.merge(q_data[['Date', 'Gross Total Return']], bm_slice[['Period', 'GrossTotalReturn']], left_on='Date', right_on='Period')
            dn_p, up_p = merged_rets[merged_rets['GrossTotalReturn'] < 0], merged_rets[merged_rets['GrossTotalReturn'] > 0]

            if not q_data.empty and q_data['Gross Total Return'].notna().any():
                best_q_idx = q_data['Gross Total Return'].idxmax()
                b_date = q_data.loc[best_q_idx, 'Date']
                best_q_date, best_q_ret = f"{b_date.year}-Q{b_date.quarter}", q_data.loc[best_q_idx, 'Gross Total Return']

                worst_q_idx = q_data['Gross Total Return'].idxmin()
                w_date = q_data.loc[worst_q_idx, 'Date']
                worst_q_date, worst_q_ret = f"{w_date.year}-Q{w_date.quarter}", q_data.loc[worst_q_idx, 'Gross Total Return']

                if len(q_data) >= 4:
                    rolling_1yr = q_data['Gross Total Return'].rolling(window=4).apply(lambda x: np.prod(1+x)-1, raw=False)
                    best_1yr, worst_1yr = rolling_1yr.max(), rolling_1yr.min()
                else: best_1yr, worst_1yr = np.nan, np.nan
            else:
                best_q_date, best_q_ret, worst_q_date, worst_q_ret, best_1yr, worst_1yr = None, np.nan, None, np.nan, np.nan, np.nan

            if len(merged_rets) > 1:
                cov = merged_rets['Gross Total Return'].cov(merged_rets['GrossTotalReturn'])
                bm_var = merged_rets['GrossTotalReturn'].var()
                beta = cov / bm_var if pd.notna(cov) and bm_var != 0 else np.nan
                corr = merged_rets['Gross Total Return'].corr(merged_rets['GrossTotalReturn'])
                r_squared = corr ** 2 if pd.notna(corr) else np.nan
                excess_ret = merged_rets['Gross Total Return'] - RISK_FREE_RATE_QTR
                sharpe_ratio = (excess_ret.mean() / excess_ret.std()) * np.sqrt(4) if excess_ret.std() != 0 else np.nan
                active_ret = merged_rets['Gross Total Return'] - merged_rets['GrossTotalReturn']
                info_ratio = (active_ret.mean() / active_ret.std()) * np.sqrt(4) if active_ret.std() != 0 else np.nan
            else:
                beta, corr, r_squared, sharpe_ratio, info_ratio = np.nan, np.nan, np.nan, np.nan, np.nan

            return {
                'Asset Name': name, 'Investor': investor_name,
                'Contributions': contribs, 'Distributions': distros,
                'Advisory Fee': sub_cf['Advisory Fee'].sum(), 'Unrealized Incentive Fee': sub_cf['Unrealized Incentive Fee'].sum(),
                'Realized Incentive Fee': sub_cf['Realized Incentive Fee'].sum(), 'Ending NAV': display_nav,
                'Gross XIRR': g_irr, 'Net XIRR': n_irr, 'DPI': dpi, 'RVPI': rvpi, 'TVPI': tvpi, 'Gross Multiple': tvpi,
                'Quarterly Gross TWR': q_curr.iloc[0]['Gross Total Return'] if not q_curr.empty else np.nan,
                'YTD Gross TWR': get_period_twr(q_data, 'Gross Total Return', REPORTING_DATE, ytd=True),
                '1-year Gross TWR': get_period_twr(q_data, 'Gross Total Return', REPORTING_DATE, years=1),
                '3-year Gross TWR': get_period_twr(q_data, 'Gross Total Return', REPORTING_DATE, years=3),
                '5-year Gross TWR': get_period_twr(q_data, 'Gross Total Return', REPORTING_DATE, years=5),
                'Since Inception Gross TWR': annualize_return_exact_days(chain_link(q_data['Gross Total Return']), days_active),
                'Quarterly Net TWR': q_curr.iloc[0]['Net Total Return'] if not q_curr.empty else np.nan,
                'YTD Net TWR': get_period_twr(q_data, 'Net Total Return', REPORTING_DATE, ytd=True),
                '1-year Net TWR': get_period_twr(q_data, 'Net Total Return', REPORTING_DATE, years=1),
                '3-year Net TWR': get_period_twr(q_data, 'Net Total Return', REPORTING_DATE, years=3),
                '5-year Net TWR': get_period_twr(q_data, 'Net Total Return', REPORTING_DATE, years=5),
                'Since Inception Net TWR': annualize_return_exact_days(chain_link(q_data['Net Total Return']), days_active),
                'Best Quarter': best_q_date, 'Best Quarter Return': best_q_ret,
                'Worst Quarter': worst_q_date, 'Worst Quarter Return': worst_q_ret,
                'Best 12 Months': best_1yr, 'Worst 12 Months': worst_1yr,
                'Max Drawdown': drawdowns.min() if not drawdowns.empty else np.nan,
                'Longest Recovery (Qtrs)': ((drawdowns < 0).astype(int).groupby((drawdowns == 0).astype(int).cumsum()).sum()).max() if not drawdowns.empty else 0,
                'Annualized Volatility': q_data['Gross Total Return'].std() * np.sqrt(4) if len(q_data) > 1 else np.nan,
                'Beta': beta, 'Correlation (r)': corr, 'R-Squared': r_squared,
                'Sharpe Ratio': sharpe_ratio, 'Information Ratio': info_ratio,
                'Downside Capture': chain_link(dn_p['Gross Total Return']) / chain_link(dn_p['GrossTotalReturn']) if not dn_p.empty and chain_link(dn_p['GrossTotalReturn']) != 0 else np.nan,
                'Up Capture Ratio': chain_link(up_p['Gross Total Return']) / chain_link(up_p['GrossTotalReturn']) if not up_p.empty and chain_link(up_p['GrossTotalReturn']) != 0 else np.nan,
                '_start': q_data['Date'].min() if not q_data.empty else None, '_days_active': days_active
            }
        except Exception as e:
            error_log.append({'Module': 'Performance Summary', 'Entity/Group': name, 'Error Details': str(e)})
            return None

    for title, assets in portfolio_sections:
        report_data.append({'Asset Name': f'--- {title} ---'})
        for a in assets:
            row = get_performance_row([a], a, is_composite=False)
            if row: report_data.append(row)

        comp = get_performance_row(assets, f'TOTAL {title} COMPOSITE', is_composite=True)
        if comp:
            try:
                start_date, days_active = comp['_start'], comp['_days_active']
                is_sector = title.endswith("SECTOR")
                if is_sector and not sec_bm.empty:
                    sec_name = title.replace(" SECTOR", "").strip()
                    sector_mapping = {
                        'HOTEL': 'CO_T_Hotel', 'INDUSTRIAL': 'CO_T_Industrial', 'OFFICE': 'CO_T_Office',
                        'RESIDENTIAL': 'CO_T_Residential', 'RETAIL': 'CO_T_Retail', 'SELF STORAGE': 'CO_T_Self Storage',
                        'OTHER': 'CO_T_Other'
                    }
                    bm_iname = sector_mapping.get(sec_name, 'CO_T_Other')
                    slice_bm = sec_bm[sec_bm['iname'] == bm_iname].copy()
                    bm_name = f"NCREIF {sec_name.title()} Benchmark"
                    bm_row = get_bm_row(slice_bm, bm_name, start_date, days_active, date_col='Date', ret_col='GrossTotalReturn', net_col='GrossTotalReturn')
                else:
                    slice_bm = bm_df.copy()
                    bm_name = "NFI-ODCE Benchmark"
                    bm_row = get_bm_row(slice_bm, bm_name, start_date, days_active, date_col='Period', ret_col='GrossTotalReturn', net_col='NetTotalReturn')

                rel_row = {'Asset Name': f'+/- Relative to {bm_name}', 'Investor': ''}
                for k in [col for col in bm_row.keys() if col not in ['Asset Name', 'Investor']]:
                    c_val = comp.get(k, np.nan)
                    b_val = bm_row.get(k, np.nan)
                    rel_row[k] = "" if (isinstance(c_val, str) or isinstance(b_val, str)) else (c_val - b_val if not (pd.isna(c_val) or pd.isna(b_val)) else np.nan)

                rel_row['Information Ratio'] = comp.get('Information Ratio', np.nan)
                report_data.extend([comp, bm_row, rel_row, {'Asset Name': ''}])
            except Exception as e:
                error_log.append({'Module': 'Benchmark Mapping', 'Entity/Group': title, 'Error Details': str(e)})

    master_df = pd.DataFrame(report_data).drop(columns=['_start', '_days_active'], errors='ignore')
    active_days_df = pd.DataFrame(active_days_list)
    irr_val_df = pd.concat(irr_validation_list, ignore_index=True) if irr_validation_list else pd.DataFrame()

    return master_df, active_days_df, irr_val_df, twr_aggregate_df, composite_twr_df, indiv_twr, portfolio_sections
