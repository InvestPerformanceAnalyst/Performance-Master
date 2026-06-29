# ==========================================
# MODULE 3: ADVANCED ATTRIBUTION & RISK ENGINE
# ==========================================
import pandas as pd
import numpy as np
from src.math_core import xirr_custom, chain_link, annualize_return_exact_days

def build_analytics(cf_df, twr_df, bm_df, config_df, indiv_twr, composite_twr_df, portfolio_sections, error_log, REPORTING_DATE, denom_df=pd.DataFrame(), sec_bm=pd.DataFrame(), attr_df=pd.DataFrame(), npi_df=pd.DataFrame(), prop_comp_df=pd.DataFrame()):
    rf_cols = [c for c in config_df.columns if str(c).strip().lower() == 'risk free rate']
    annual_rf_rate = float(config_df[rf_cols[0]].dropna().iloc[0]) if rf_cols and not config_df[rf_cols[0]].dropna().empty else 0.04
    RISK_FREE_RATE_QTR = annual_rf_rate / 4.0

    trailing_irr_list = []
    earliest_date = indiv_twr['Date'].min() if not indiv_twr.empty else REPORTING_DATE
    eval_dates = pd.date_range(start=earliest_date, end=REPORTING_DATE, freq='QE')

    def get_trailing_irr(entities, eval_dt):
        sub_cf = cf_df[(cf_df['Entity Name'].isin(entities)) & (cf_df['Effective Date'] <= eval_dt)].copy()
        if sub_cf.empty: return np.nan, np.nan

        nav_dt = sub_cf[sub_cf['Effective Date'] <= eval_dt]['Effective Date'].max()
        nav_val = sub_cf[sub_cf['Effective Date'] == nav_dt]['Ending NAV'].sum()

        raw_cf = sub_cf.copy()
        raw_cf['Gross CF'] = raw_cf['Distributions'].fillna(0) - raw_cf['Contributions'].fillna(0) - raw_cf['Advisory Fee'].fillna(0) - raw_cf['Realized Incentive Fee'].fillna(0)
        raw_cf['Net CF'] = raw_cf['Gross CF']

        gross_agg = raw_cf.groupby('Effective Date')['Gross CF'].sum().reset_index()
        net_agg = raw_cf.groupby('Effective Date')['Net CF'].sum().reset_index()

        def calc_irr(agg_df, val_col):
            d_list = agg_df['Effective Date'].tolist() + [eval_dt]
            c_list = agg_df[val_col].tolist() + [nav_val]
            return xirr_custom(d_list, c_list)

        return calc_irr(gross_agg, 'Gross CF'), calc_irr(net_agg, 'Net CF')

    for name in indiv_twr['Entity Name'].unique():
        for d in eval_dates:
            g, n = get_trailing_irr([name], d)
            if not pd.isna(g) or not pd.isna(n): 
                trailing_irr_list.append({'Date': d, 'Entity Name': name, 'Gross Trailing IRR': g, 'Net Trailing IRR': n, 'Is Composite': False})

    for title, assets in portfolio_sections:
        c_name = f'TOTAL {title} COMPOSITE'
        for d in eval_dates:
            g, n = get_trailing_irr(assets, d)
            if not pd.isna(g) or not pd.isna(n): 
                trailing_irr_list.append({'Date': d, 'Entity Name': c_name, 'Gross Trailing IRR': g, 'Net Trailing IRR': n, 'Is Composite': True})

    trailing_irr_df = pd.DataFrame(trailing_irr_list)
    trailing_pivot = pd.DataFrame()
    ent_pivot = pd.DataFrame()
    if not trailing_irr_df.empty:
        comp_df_irr = trailing_irr_df[trailing_irr_df['Is Composite'] == True]
        if not comp_df_irr.empty: trailing_pivot = comp_df_irr.pivot(index='Date', columns='Entity Name', values='Gross Trailing IRR').reset_index()
        ent_df_irr = trailing_irr_df[trailing_irr_df['Is Composite'] == False]
        if not ent_df_irr.empty: ent_pivot = ent_df_irr.pivot(index='Date', columns='Entity Name', values='Gross Trailing IRR').reset_index()

    final_breakdowns, final_entity_breakdowns, final_return_distributions, corr_matrices, rolling_corr_list = [], [], [], [], []
    ytd_start = pd.to_datetime(f"{REPORTING_DATE.year - 1}-12-31")
    bm_twr = bm_df.rename(columns={'Period': 'Date'})

    for title, assets in portfolio_sections:
        c_name = f'TOTAL {title} COMPOSITE'
        c_data = composite_twr_df[composite_twr_df['Entity Name'] == c_name].copy()
        if c_data.empty: continue

        bm_name = "NFI-ODCE Benchmark" if title == "ALL INVESTMENTS" else "Benchmark"
        j = c_data.merge(bm_twr[['Date', 'NetTotalReturn', 'GrossTotalReturn', 'GrossIncomeReturn', 'GrossAppreciationReturn']], on='Date', how='left').fillna(0)
        if j.empty: continue

        j['Total Fees'] = j['Gross Investment Income Minus Fees'] - j['Net Investment Income']
        j['Port Growth'] = (1 + j['Net Total Return']).cumprod() * 1000
        j['BM Growth'] = (1 + j['NetTotalReturn']).cumprod() * 1000

        final_breakdowns.append(pd.DataFrame({
            'Composite Name': c_name, 'Benchmark Name': bm_name, 'Date': j['Date'],
            'Net Investment Income': j['Net Investment Income'], 'Net Appreciation': j['Net Appreciation'],
            'Total Fees': j['Total Fees'], 'Growth of $1,000': j['Port Growth'], 'Benchmark Growth of $1,000': j['BM Growth']
        }))

        dist_df = j[['Date', 'Gross Income Return', 'Gross Appreciation Return', 'GrossIncomeReturn', 'GrossAppreciationReturn']].copy().rename(columns={'GrossIncomeReturn': 'BM_Inc_Ret', 'GrossAppreciationReturn': 'BM_App_Ret'})
        dist_df.insert(0, 'Composite Name', c_name)
        dist_df.insert(1, 'Benchmark Name', bm_name)
        final_return_distributions.append(dist_df)

        valid_ents = [a for a in assets if a in indiv_twr['Entity Name'].unique()]
        if valid_ents:
            e_data = indiv_twr[indiv_twr['Entity Name'].isin(valid_ents)]
            e_pivot = e_data.pivot(index='Date', columns='Entity Name', values='Net Total Return').fillna(0).reset_index()
            e_join = j[['Date', 'Port Growth', 'BM Growth', 'Denominator']].merge(e_pivot, on='Date', how='left').fillna(0)

            for e in valid_ents:
                denom_pivot = e_data[e_data['Entity Name'] == e][['Date', 'Denominator']].rename(columns={'Denominator': f'{e}_denom'})
                e_join = e_join.merge(denom_pivot, on='Date', how='left').fillna(0)
                e_join[e] = (e_join[f'{e}_denom'] / e_join['Denominator']) * e_join[e] * e_join['Denominator']

            final_entity_breakdowns.append({'Composite Name': c_name, 'Benchmark Name': bm_name, 'Data': e_join, 'Entities': valid_ents})

            corr_df = e_pivot.merge(bm_twr[['Date', 'NetTotalReturn']].rename(columns={'NetTotalReturn': bm_name}), on='Date', how='left')
            corr_df = corr_df.merge(j[['Date', 'Net Total Return']].rename(columns={'Net Total Return': c_name}), on='Date', how='left').drop(columns=['Date'])
            if not corr_df.empty and len(corr_df) > 1:
                corr_matrices.append({'Composite Name': c_name, 'Benchmark Name': bm_name, 'Matrix': corr_df.corr()})

            if len(j) >= 12:
                for idx in range(11, len(j)):
                    window = j.iloc[idx-11:idx+1]
                    if window['Gross Total Return'].std() > 0 and window['GrossTotalReturn'].std() > 0:
                        r = window['Gross Total Return'].corr(window['GrossTotalReturn'])
                        rolling_corr_list.append({'Composite Name': c_name, 'Date': window.iloc[-1]['Date'], 'Rolling Correlation': r})

    rolling_corr_df = pd.DataFrame(rolling_corr_list)

    periods = [
        ('Quarterly', REPORTING_DATE - pd.DateOffset(months=3), REPORTING_DATE, 1, 0.25),
        ('YTD', ytd_start, REPORTING_DATE, -1, 1),
        ('1-Year', REPORTING_DATE - pd.DateOffset(years=1), REPORTING_DATE, 4, 1),
        ('3-Year', REPORTING_DATE - pd.DateOffset(years=3), REPORTING_DATE, 12, 3),
        ('5-Year', REPORTING_DATE - pd.DateOffset(years=5), REPORTING_DATE, 20, 5),
        ('10-Year', REPORTING_DATE - pd.DateOffset(years=10), REPORTING_DATE, 40, 10),
        ('Since Inception', pd.to_datetime('1900-01-01'), REPORTING_DATE, 0, 0)
    ]

    abs_movers_list, alpha_movers_list = [], []
    df_port = composite_twr_df[composite_twr_df['Entity Name'] == 'TOTAL ALL INVESTMENTS COMPOSITE'].copy()

    if not denom_df.empty:
        global_denom = denom_df.groupby('Date')['Denominator'].first().reset_index()
        df_port = pd.merge(df_port, global_denom, on='Date', how='left', suffixes=('', '_override'))
        df_port['Denominator'] = np.where(df_port['Denominator_override'].notna(), df_port['Denominator_override'], df_port['Denominator'])
        df_port.drop(columns=['Denominator_override'], inplace=True)

    port_ret_dict = {}
    port_days = (REPORTING_DATE - cf_df['Effective Date'].min()).days + 1

    for p_name, sd, ed, req_q, yrs in periods:
        p_slice = df_port[(df_port['Date'] > sd) & (df_port['Date'] <= ed)]
        if p_slice.empty or (req_q > 0 and len(p_slice) < (req_q - 1)): continue

        R_p_cum = chain_link(p_slice['Net Total Return'])
        if p_name in ['Quarterly', 'YTD', '1-Year']: R_p_ann = R_p_cum
        elif p_name == 'Since Inception': R_p_ann = annualize_return_exact_days(R_p_cum, port_days)
        else: R_p_ann = (1 + R_p_cum)**(1/yrs) - 1 if R_p_cum >= -1 else -1

        port_ret_dict[p_name] = {'slice': p_slice, 'scale': R_p_ann / R_p_cum if R_p_cum != 0 else 1.0}

    def calculate_carino_with_alpha(df_entity, df_port_slice, bm_slice_active, scale_factor):
        e_s, p_s, b_s = df_entity.set_index('Date'), df_port_slice.set_index('Date'), bm_slice_active.set_index('Period')
        if p_s.empty or e_s.empty: return np.nan, np.nan, np.nan, np.nan

        j = p_s[['Net Total Return', 'Denominator']].join(e_s[['Net Investment Income', 'Net Appreciation', 'Denominator']], rsuffix='_e').fillna(0)
        j = j.join(b_s[['NetTotalReturn']]).fillna(0)
        j['Denominator'] = j['Denominator'].replace(0, np.nan)

        inc_c_t = (j['Net Investment Income'] / j['Denominator']).fillna(0)
        app_c_t = (j['Net Appreciation'] / j['Denominator']).fillna(0)
        w_i_t = (j['Denominator_e'] / j['Denominator']).fillna(0)
        bm_c_t = w_i_t * j['NetTotalReturn']

        R_p_t = j['Net Total Return'].fillna(0)
        R_p_cum = chain_link(R_p_t)
        K = np.log1p(R_p_cum) / R_p_cum if R_p_cum != 0 else 1.0
        k_t = np.log1p(R_p_t) / R_p_t
        k_t = k_t.fillna(1.0); k_t[R_p_t == 0] = 1.0
        adj_t = k_t / K

        inc_c = (inc_c_t * adj_t).sum() * scale_factor
        app_c = (app_c_t * adj_t).sum() * scale_factor
        bm_c = (bm_c_t * adj_t).sum() * scale_factor
        return inc_c, app_c, inc_c + app_c, bm_c

    for p_name, sd, ed, req_q, yrs in periods:
        if p_name not in port_ret_dict: continue
        p_info = port_ret_dict[p_name]
        bm_slice_active = bm_df[(bm_df['Period'] > sd) & (bm_df['Period'] <= ed)]

        for ent in indiv_twr['Entity Name'].unique():
            try:
                df_ent = indiv_twr[(indiv_twr['Entity Name'] == ent) & (indiv_twr['Date'] > sd) & (indiv_twr['Date'] <= ed)]
                if df_ent.empty: continue
                inc_c, app_c, tot_c, bm_c = calculate_carino_with_alpha(df_ent, p_info['slice'], bm_slice_active, p_info['scale'])
                if not (pd.isna(tot_c) or tot_c == 0):
                    abs_movers_list.append({'Period': p_name, 'Entity Name': ent, 'Net Income Contribution': inc_c, 'Net Appreciation Contribution': app_c, 'Net Total Contribution': tot_c})
                    alpha_movers_list.append({'Period': p_name, 'Entity Name': ent, 'Entity Contribution to Return': tot_c, 'Benchmark Equivalent Contribution': bm_c, 'Contribution to Alpha': tot_c - bm_c})
            except Exception: continue

    abs_df = pd.DataFrame(abs_movers_list)
    alpha_df = pd.DataFrame(alpha_movers_list)

    brinson_results = []
    if not sec_bm.empty and 'propType_clean' in config_df.columns:
        try:
            sector_mapping = {'Hotel': 'CO_T_Hotel', 'Industrial': 'CO_T_Industrial', 'Office': 'CO_T_Office', 'Residential': 'CO_T_Residential', 'Retail': 'CO_T_Retail', 'Self Storage': 'CO_T_Self Storage', 'Other': 'CO_T_Other'}
            brinson_periods = {'QTD': [REPORTING_DATE], 'YTD': pd.date_range(start=ytd_start, end=REPORTING_DATE, freq='QE').tolist(), '1-Year': pd.date_range(start=REPORTING_DATE - pd.DateOffset(years=1), end=REPORTING_DATE, freq='QE').tolist()}
            for p_name, p_dates in brinson_periods.items():
                period_data = []
                for dt in p_dates:
                    port_q = composite_twr_df[(composite_twr_df['Entity Name'] == 'TOTAL ALL INVESTMENTS COMPOSITE') & (composite_twr_df['Date'] == dt)]
                    tot_bm = sec_bm[(sec_bm['iname'] == 'CO_TOT') & (sec_bm['Date'] == dt)]
                    if port_q.empty or tot_bm.empty: continue
                    total_port_denom = port_q['Denominator'].values[0]
                    total_bm_emv = tot_bm['emv'].values[0]
                    R_B = tot_bm['tret'].values[0] - 1.0

                    for sector, group in config_df.groupby('propType_clean'):
                        comp_name = f"TOTAL {str(sector).upper()} SECTOR COMPOSITE"
                        sec_port = composite_twr_df[(composite_twr_df['Entity Name'] == comp_name) & (composite_twr_df['Date'] == dt)]
                        sec_bm_q = sec_bm[(sec_bm['iname'] == sector_mapping.get(sector, 'CO_T_Other')) & (sec_bm['Date'] == dt)]
                        if sec_port.empty or sec_bm_q.empty: continue

                        w_i = sec_port['Denominator'].values[0] / total_port_denom if total_port_denom != 0 else 0
                        W_i = sec_bm_q['emv'].values[0] / total_bm_emv if total_bm_emv != 0 else 0
                        r_i = sec_port['Gross Total Return'].values[0]
                        R_i = sec_bm_q['tret'].values[0] - 1.0

                        alloc = (w_i - W_i) * (R_i - R_B)
                        select = w_i * (r_i - R_i)
                        period_data.append({'Period': p_name, 'Date': dt, 'Sector': sector, 'Port Weight': w_i, 'BM Weight': W_i, 'Port Return': r_i, 'BM Return': R_i, 'Allocation Effect': alloc, 'Selection Effect': select, 'Total Value Add': alloc + select})

                if period_data:
                    df_p = pd.DataFrame(period_data)
                    agg = df_p.groupby('Sector').agg({'Port Weight': 'mean', 'BM Weight': 'mean', 'Port Return': lambda x: np.prod(1+x)-1, 'BM Return': lambda x: np.prod(1+x)-1, 'Allocation Effect': 'sum', 'Selection Effect': 'sum', 'Total Value Add': 'sum'}).reset_index()
                    agg.insert(0, 'Period', p_name)
                    brinson_results.append(agg)
        except Exception: pass

    brinson_df = pd.concat(brinson_results, ignore_index=True) if brinson_results else pd.DataFrame()

    j_cf = cf_df.copy()
    j_cf['Total Fees'] = j_cf['Advisory Fee'].fillna(0) + j_cf['Realized Incentive Fee'].fillna(0)
    j_cf['Actual_Net_Flow'] = j_cf['Distributions'] - j_cf['Contributions'] + j_cf['Total Fees']
    j_curve_df = j_cf.groupby('Effective Date').agg({'Contributions': 'sum', 'Distributions': 'sum', 'Total Fees': 'sum', 'Actual_Net_Flow': 'sum'}).reset_index().sort_values('Effective Date')
    j_curve_df['Cumulative Net Cash Flow'] = j_curve_df['Actual_Net_Flow'].cumsum()
    nav_df = j_cf[j_cf['Ending NAV'] > 0].groupby('Effective Date')['Ending NAV'].sum().reset_index()
    j_curve_df = pd.merge(j_curve_df, nav_df, on='Effective Date', how='left')
    j_curve_df['Ending NAV'] = j_curve_df['Ending NAV'].ffill().fillna(0)
    j_curve_export = j_curve_df.copy()
    j_curve_export['Total Value'] = j_curve_export['Cumulative Net Cash Flow'] + j_curve_export['Ending NAV']
    j_curve_export = j_curve_export[['Effective Date', 'Contributions', 'Distributions', 'Total Fees', 'Ending NAV', 'Cumulative Net Cash Flow', 'Total Value']]

    aum_data, primary_composites = [], []
    if 'Composite Grouping' in config_df.columns:
        primary_composites = [f'TOTAL {str(group).replace(" COMPOSITE", "").strip()} COMPOSITE' for group in config_df['Composite Grouping'].dropna().unique()]

    for title, assets in portfolio_sections:
        comp_name = f'TOTAL {title} COMPOSITE'
        if comp_name not in primary_composites: continue
        nav_by_date = cf_df[cf_df['Entity Name'].isin(assets) & (cf_df['Ending NAV'] > 0)].groupby('Effective Date')['Ending NAV'].sum().reset_index()
        for _, row in nav_by_date.iterrows():
            aum_data.append({'Date': row['Effective Date'], 'Composite': comp_name, 'AUM': row['Ending NAV']})
    aum_pivot = pd.DataFrame(aum_data).pivot(index='Date', columns='Composite', values='AUM').fillna(0).reset_index() if aum_data else pd.DataFrame()

    decay_data = []
    def calculate_decay(name, entities):
        sub_cf = cf_df[(cf_df['Entity Name'].isin(entities))].copy()
        if sub_cf.empty: return None
        max_date = sub_cf['Effective Date'].max()
        current_nav = sub_cf[sub_cf['Effective Date'] == max_date]['Ending NAV'].sum()
        agg_cf = sub_cf.copy()
        agg_cf['Pure CF'] = agg_cf['Distributions'].fillna(0) - agg_cf['Contributions'].fillna(0)
        agg_cf = agg_cf.groupby('Effective Date')['Pure CF'].sum().reset_index()

        def get_projected_irr(years_added):
            d_list = agg_cf['Effective Date'].tolist() + [max_date + pd.DateOffset(days=int(365.25 * years_added))]
            c_list = agg_cf['Pure CF'].tolist() + [current_nav]
            return xirr_custom(d_list, c_list)

        r_curr = get_projected_irr(0)
        req_nav = lambda y: current_nav * ((1 + r_curr) ** y) - current_nav if (pd.notna(r_curr) and current_nav > 0 and r_curr > -1.0) else np.nan

        return {
            'Asset Name': name, 'Current NAV': current_nav, 'Current Gross IRR': r_curr,
            '+1 Quarter Hold': get_projected_irr(0.25), '+1 Year Hold': get_projected_irr(1), '+2 Year Hold': get_projected_irr(2), '+3 Year Hold': get_projected_irr(3), '+5 Year Hold': get_projected_irr(5), '+10 Year Hold': get_projected_irr(10), '+15 Year Hold': get_projected_irr(15),
            'Req Value (+1 Qtr)': req_nav(0.25), 'Req Value (+1 Year)': req_nav(1), 'Req Value (+2 Year)': req_nav(2), 'Req Value (+3 Year)': req_nav(3), 'Req Value (+5 Year)': req_nav(5), 'Req Value (+10 Year)': req_nav(10), 'Req Value (+15 Year)': req_nav(15)
        }

    for title, assets in portfolio_sections:
        row = calculate_decay(f'TOTAL {title} COMPOSITE', assets)
        if row: decay_data.append(row)
        for a in assets:
            row = calculate_decay(a, [a])
            if row: decay_data.append(row)
    decay_df = pd.DataFrame(decay_data).drop_duplicates(subset=['Asset Name'])

    # --- INCORPORATE SEPARATE BOTTOM-UP PROPERTY ANALYSIS MATRIX MAPPED TO INDIVIDUAL ARRAYS ---
    prop_analysis_df = pd.DataFrame()
    if not prop_comp_df.empty and not npi_df.empty and not attr_df.empty:
        try:
            npi_type_map = {'Apartments': 'CO_T_Residential: Apartment', 'Residential': 'CO_T_Residential', 'Industrial': 'CO_T_Industrial', 'Office': 'CO_T_Office', 'Retail': 'CO_T_Retail'}
            npi_region_map = {'East': '_R_E', 'West': '_R_W', 'South': '_R_S', 'Midwest': '_R_M'}
            merged = prop_comp_df.merge(attr_df[['propertyName', 'NCREIF Region', 'Property Type']], left_on='Entity Name', right_on='propertyName', how='left').dropna(subset=['Net Operating Income', 'Appreciation', 'Denominator'])
            p_list = []
            for _, r in merged.iterrows():
                if r['Denominator'] == 0: continue
                dt = pd.to_datetime(r['Date'])
                bm_row = npi_df[(npi_df['iname'] == f"{npi_type_map.get(r['Property Type_y'], 'CO_TOT')}{npi_region_map.get(r['NCREIF Region'], '')}") & (npi_df['yyq'] == (dt.year * 10 + dt.quarter))]
                bm_i = bm_row['iret'].values[0] - 1.0 if not bm_row.empty else 0.0
                bm_a = bm_row['aret'].values[0] - 1.0 if not bm_row.empty else 0.0
                p_list.append({'Date': dt, 'Property Name': r['Entity Name'], 'Type': r['Property Type_y'], 'Region': r['NCREIF Region'], 'Property NOI Return': r['Net Operating Income'] / r['Denominator'], 'Benchmark NOI Return': bm_i, 'NOI Value Add': (r['Net Operating Income'] / r['Denominator']) - bm_i, 'Property App Return': r['Appreciation'] / r['Denominator'], 'Benchmark App Return': bm_a, 'App Value Add': (r['Appreciation'] / r['Denominator']) - bm_a})
            prop_analysis_df = pd.DataFrame(p_list)
        except Exception as e:
            error_log.append({'Module': 'Property Analysis Core', 'Entity/Group': 'Global', 'Error Details': str(e)})

    return trailing_irr_df, trailing_pivot, ent_pivot, final_breakdowns, final_entity_breakdowns, final_return_distributions, j_curve_export, abs_df, alpha_df, corr_matrices, rolling_corr_df, brinson_df, aum_pivot, decay_df, prop_analysis_df
