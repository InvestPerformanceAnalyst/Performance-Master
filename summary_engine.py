# =====================================================================
# MODULE 2: COMPOSITE FUND ROLLUP & POSITION MATRICES CORE
# =====================================================================
import pandas as pd
import numpy as np
from src.math_core import xirr_custom, get_period_twr, annualize_return_exact_days, calc_6_components

def build_performance_summary(cf_df, twr_df, bm_df, config_df, investor_name, error_log, REPORTING_DATE, sec_bm=pd.DataFrame()):
    cf_df['Advisory Fee'] = cf_df.get('Advisory Fee', 0).fillna(0)
    cf_df['Realized Incentive Fee'] = cf_df.get('Realized Incentive Fee', 0).fillna(0)
    cf_df['Unrealized Incentive Fee'] = cf_df.get('Unrealized Incentive Fee', 0).fillna(0)
    cf_df['Gross CF'] = cf_df['Distributions'].fillna(0) - cf_df['Contributions'].fillna(0) - cf_df['Advisory Fee'] - cf_df['Realized Incentive Fee']
    cf_df['Net CF'] = cf_df['Gross CF']

    portfolio_sections = []
    if 'Composite Grouping' in config_df.columns:
        group_map = config_df.groupby('Composite Grouping')['Entity'].apply(list).to_dict()
        all_investments_list = []
        for group_name, entities in group_map.items():
            if pd.isna(group_name): continue
            portfolio_sections.append((str(group_name).replace(" COMPOSITE", "").strip(), entities))
            all_investments_list.extend(entities)
        portfolio_sections.insert(0, ("ALL INVESTMENTS", list(set(all_investments_list))))
    else:
        portfolio_sections.append(("ALL INVESTMENTS", cf_df['Entity Name'].unique().tolist()))

    master_rows = []

    def calculate_entity_metrics(name, is_composite, entities_list):
        row = {'Asset Name': f'TOTAL {name} COMPOSITE' if is_composite else name}
        row['Investor'] = investor_name if is_composite else config_df.loc[config_df['Entity'] == name, 'Investor Name'].fillna("Unknown").iloc[0] if not config_df[config_df['Entity'] == name].empty else "Unknown"
        sub_cf = cf_df[cf_df['Entity Name'].isin(entities_list)].copy()
        if sub_cf.empty: return None

        row['Contributions'] = sub_cf['Contributions'].sum()
        row['Distributions'] = sub_cf['Distributions'].sum()
        row['Advisory Fee'] = sub_cf['Advisory Fee'].sum()
        row['Realized Incentive Fee'] = sub_cf['Realized Incentive Fee'].sum()
        max_date = sub_cf['Effective Date'].max()
        row['Ending NAV'] = sub_cf[sub_cf['Effective Date'] == max_date]['Ending NAV'].sum()
        row['Unrealized Incentive Fee'] = sub_cf[sub_cf['Effective Date'] == max_date]['Unrealized Incentive Fee'].sum()

        gross_agg = sub_cf.groupby('Effective Date')['Gross CF'].sum().reset_index()
        net_agg = sub_cf.groupby('Effective Date')['Net CF'].sum().reset_index()

        def compute_xirr(agg_df, val_col):
            d_list = agg_df['Effective Date'].tolist() + [REPORTING_DATE]
            c_list = agg_df[val_col].tolist() + [row['Ending NAV']]
            return xirr_custom(d_list, c_list)

        row['Gross XIRR'] = compute_xirr(gross_agg, 'Gross CF')
        row['Net XIRR'] = compute_xirr(net_agg, 'Net CF')

        paid_in = row['Contributions'] + row['Advisory Fee'] + row['Realized Incentive Fee']
        row['DPI'] = row['Distributions'] / paid_in if paid_in > 0 else np.nan
        row['RVPI'] = row['Ending NAV'] / paid_in if paid_in > 0 else np.nan
        row['TVPI'] = (row['Distributions'] + row['Ending NAV']) / paid_in if paid_in > 0 else np.nan
        row['Gross Multiple'] = (row['Distributions'] + row['Ending NAV']) / row['Contributions'] if row['Contributions'] > 0 else np.nan
        return row

    for title, assets in portfolio_sections:
        comp_row = calculate_entity_metrics(title, True, assets)
        if comp_row:
            master_rows.append(comp_row)
            for a in assets:
                ent_row = calculate_entity_metrics(a, False, [a])
                if ent_row: master_rows.append(ent_row)

    master_df = pd.DataFrame(master_rows).drop_duplicates(subset=['Asset Name'])
    twr_agg = calc_6_components(twr_df.groupby(['Entity Name', 'Date'])[['Gross Investment Income Minus JV Fees', 'Gross Appreciation', 'Net Investment Income', 'Net Appreciation', 'Denominator']].sum().reset_index())
    indiv_twr = twr_agg.copy()

    comp_twr_rows = []
    for title, assets in portfolio_sections:
        sub = twr_df[twr_df['Entity Name'].isin(assets)]
        if sub.empty: continue
        agg = sub.groupby('Date')[['Gross Investment Income Minus JV Fees', 'Gross Appreciation', 'Net Investment Income', 'Net Appreciation', 'Denominator']].sum().reset_index()
        agg.insert(0, 'Entity Name', f'TOTAL {title} COMPOSITE')
        comp_twr_rows.append(agg)

    composite_twr_df = calc_6_components(pd.concat(comp_twr_rows, ignore_index=True)) if comp_twr_rows else pd.DataFrame()
    all_twr = pd.concat([composite_twr_df, indiv_twr], ignore_index=True) if not composite_twr_df.empty else indiv_twr

    if 'Period' in bm_df.columns:
        bm_df['Period'] = pd.to_datetime(bm_df['Period'])
        bm_twr_metrics = [{'Entity Name': 'NFI-ODCE Benchmark', 'Date': p, 'Gross Total Return': bm_df[bm_df['Period'] == p]['GrossTotalReturn'].iloc[0], 'Net Total Return': bm_df[bm_df['Period'] == p]['NetTotalReturn'].iloc[0]} for p in bm_df['Period'].unique()]
        all_twr = pd.concat([all_twr, pd.DataFrame(bm_twr_metrics)], ignore_index=True)

    active_days_list = []
    for asset in cf_df['Entity Name'].unique():
        sub = cf_df[cf_df['Entity Name'] == asset]
        first, last = sub['Effective Date'].min(), sub['Effective Date'].max()
        if pd.notna(first) and pd.notna(last):
            days = max((last - first).days, 1 if len(sub) > 1 else 0)
            active_days_list.append({'Entity Name': asset, 'First Active Date': first, 'Last Active Date': last, 'Total Active Days': days})
    active_days_df = pd.DataFrame(active_days_list)

    twr_results = []
    for asset in master_df['Asset Name'].unique():
        slice_df = all_twr[all_twr['Entity Name'] == asset].sort_values('Date').reset_index(drop=True)
        if slice_df.empty: continue
        ad_match = active_days_df[active_days_df['Entity Name'] == asset]
        days_active = ad_match['Total Active Days'].iloc[0] if not ad_match.empty else (slice_df['Date'].max() - slice_df['Date'].min()).days

        res = {
            'Asset Name': asset,
            'Quarterly Gross TWR': get_period_twr(slice_df, 'Gross Total Return', REPORTING_DATE, years=0.25),
            'YTD Gross TWR': get_period_twr(slice_df, 'Gross Total Return', REPORTING_DATE, ytd=True),
            '1-year Gross TWR': get_period_twr(slice_df, 'Gross Total Return', REPORTING_DATE, years=1),
            '3-year Gross TWR': get_period_twr(slice_df, 'Gross Total Return', REPORTING_DATE, years=3),
            '5-year Gross TWR': get_period_twr(slice_df, 'Gross Total Return', REPORTING_DATE, years=5),
            '10-year Gross TWR': get_period_twr(slice_df, 'Gross Total Return', REPORTING_DATE, years=10),
            'Since Inception Gross TWR': annualize_return_exact_days(get_period_twr(slice_df, 'Gross Total Return', REPORTING_DATE, years=100), days_active),
            'Quarterly Net TWR': get_period_twr(slice_df, 'Net Total Return', REPORTING_DATE, years=0.25),
            'YTD Net TWR': get_period_twr(slice_df, 'Net Total Return', REPORTING_DATE, ytd=True),
            '1-year Net TWR': get_period_twr(slice_df, 'Net Total Return', REPORTING_DATE, years=1),
            '3-year Net TWR': get_period_twr(slice_df, 'Net Total Return', REPORTING_DATE, years=3),
            '5-year Net TWR': get_period_twr(slice_df, 'Net Total Return', REPORTING_DATE, years=5),
            '10-year Net TWR': get_period_twr(slice_df, 'Net Total Return', REPORTING_DATE, years=10),
            'Since Inception Net TWR': annualize_return_exact_days(get_period_twr(slice_df, 'Net Total Return', REPORTING_DATE, years=100), days_active)
        }
        
        # In-line Risk profile allocations
        ret_col = 'Gross Total Return'
        if not slice_df[ret_col].isna().all() and len(slice_df) > 0:
            best_q_idx = slice_df[ret_col].idxmax()
            worst_q_idx = slice_df[ret_col].idxmin()
            res['Best Quarter'] = f"{slice_df.loc[best_q_idx, 'Date'].year}-Q{slice_df.loc[best_q_idx, 'Date'].quarter}"
            res['Best Quarter Return'] = slice_df.loc[best_q_idx, ret_col]
            res['Worst Quarter'] = f"{slice_df.loc[worst_q_idx, 'Date'].year}-Q{slice_df.loc[worst_q_idx, 'Date'].quarter}"
            res['Worst Quarter Return'] = slice_df.loc[worst_q_idx, ret_col]

            slice_df['Roll_12M'] = slice_df[ret_col].rolling(4).apply(lambda x: np.prod(1+x)-1)
            res['Best 12 Months'] = slice_df['Roll_12M'].max()
            res['Worst 12 Months'] = slice_df['Roll_12M'].min()

            slice_df['Cum_Ret'] = (1 + slice_df[ret_col].fillna(0)).cumprod()
            slice_df['High_Water_Mark'] = slice_df['Cum_Ret'].cummax()
            slice_df['Drawdown'] = (slice_df['Cum_Ret'] / slice_df['High_Water_Mark']) - 1
            res['Max Drawdown'] = slice_df['Drawdown'].min()

            if len(slice_df) >= 4:
                res['Annualized Volatility'] = slice_df[ret_col].std(ddof=1) * np.sqrt(4)
                
            merged_bm = all_twr[all_twr['Entity Name'] == 'NFI-ODCE Benchmark']
            if not merged_bm.empty:
                m_risk = pd.merge(slice_df[['Date', ret_col]], merged_bm[['Date', 'Gross Total Return']], on='Date', suffixes=('_A', '_B')).dropna()
                if len(m_risk) > 1:
                    cov = np.cov(m_risk[f'{ret_col}_A'], m_risk['Gross Total Return_B'])[0, 1]
                    var_b = np.var(m_risk['Gross Total Return_B'], ddof=1)
                    if var_b > 0: res['Beta'] = cov / var_b
                    std_a, std_b = m_risk[f'{ret_col}_A'].std(), m_risk['Gross Total Return_B'].std()
                    if std_a > 0 and std_b > 0:
                        res['Correlation (r)'] = cov / (std_a * std_b)
                        res['R-Squared'] = res['Correlation (r)'] ** 2

        twr_results.append(res)

    master_final = pd.merge(master_df, pd.DataFrame(twr_results), on='Asset Name', how='left')
    return master_final, active_days_df, twr_agg, composite_twr_df, indiv_twr, portfolio_sections