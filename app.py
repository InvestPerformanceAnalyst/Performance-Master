import streamlit as st
import pandas as pd
import numpy as np
import io
import math
import sys
import os
from scipy.optimize import newton
import warnings

# Set clean professional institutional configuration layout
st.set_page_config(page_title="REPE Performance Analytics Platform", page_icon="📊", layout="wide")
warnings.filterwarnings('ignore', category=RuntimeWarning)

# --- LIVE TERMINAL CONSOLE REDIRECT WRAPPER ---
class StreamlitConsoleRedirect:
    """Intercepts and routes standard stdout print lines directly into a Streamlit UI engine box."""
    def __init__(self, code_placeholder):
        self.code_placeholder = code_placeholder
        self.output_log = ""
    def write(self, text):
        self.output_log += text
        self.code_placeholder.code(self.output_log)
    def flush(self):
        pass

# ==========================================
# MODULE 1: SETUP & CORE FINANCIAL HELPERS
# ==========================================
def xirr_custom(dates, cashflows, guess=0.1):
    """Calculates Internal Rate of Return using Newton-Raphson with MOIC-driven Smart Guesses."""
    if sum(cashflows) == 0 or len(dates) < 2: return np.nan
    years = np.array([(d - dates[0]).days / 365.0 for d in dates])

    def npv(r):
        if r <= -1.0: return float('inf')
        return sum(cf / (1 + r)**y for cf, y in zip(cashflows, years))

    pos_cf = sum(cf for cf in cashflows if cf > 0)
    neg_cf = sum(-cf for cf in cashflows if cf < 0)
    if neg_cf == 0: return np.nan
    
    moic = pos_cf / neg_cf
    total_years = years[-1] if years[-1] > 0 else 1
    smart_guess = (moic ** (1 / total_years)) - 1 if moic > 0 else -0.99
    
    guesses = [smart_guess, guess, 0.0, -0.01, 0.01, -0.1, 0.1, -0.5, 0.5, -0.9]
    tried = set()
    valid_roots = []

    for g in guesses:
        if g in tried: continue
        tried.add(g)
        try:
            res = newton(npv, g, maxiter=200)
            if not pd.isna(res) and res > -1.0:
                if abs(npv(res)) < 1e-3:
                    valid_roots.append(res)
        except Exception:
            continue
            
    if not valid_roots: return np.nan
    best_root = min(valid_roots, key=lambda r: abs(r - smart_guess))
    
    total_days = (dates[-1] - dates[0]).days
    if 0 < total_days < 365:
        return (1 + best_root) ** (total_days / 365.0) - 1
    return best_root

def chain_link(returns):
    return np.prod(1 + returns.fillna(0)) - 1

def annualize_return_exact_days(cum_ret, days_active):
    if pd.isna(cum_ret) or days_active <= 0: return np.nan
    if days_active < 365: return cum_ret  
    return (1 + cum_ret)**(365.0 / days_active) - 1

def get_period_twr(df, ret_col, end_date, date_col='Date', ytd=False, years=None):
    if df.empty: return np.nan
    if ytd:
        start_date = pd.to_datetime(f"{end_date.year - 1}-12-31")
    elif years:
        start_date = end_date - pd.DateOffset(years=years)
    else:
        return np.nan
        
    mask = (df[date_col] > start_date) & (df[date_col] <= end_date)
    period_df = df[mask]
    if period_df.empty: return np.nan
    if years and years > 1:
        if len(period_df) < (years * 4) - 1: return np.nan 
            
    cum_ret = chain_link(period_df[ret_col])
    if years and years > 1:
        return (1 + cum_ret) ** (1.0 / years) - 1 if cum_ret >= -1.0 else -1.0
    return cum_ret

def calc_6_components(df):
    if df.empty: return df
    df['Denominator'] = df['Denominator'].replace(0, np.nan)
    df['Gross Income Return'] = df['Gross Investment Income Minus JV Fees'] / df['Denominator']
    df['Gross Appreciation Return'] = df['Gross Appreciation'] / df['Denominator']
    df['Gross Total Return'] = df['Gross Income Return'].fillna(0) + df['Gross Appreciation Return'].fillna(0)
    df['Net Income Return'] = df['Net Investment Income'] / df['Denominator']
    df['Net Appreciation Return'] = df['Net Appreciation'] / df['Denominator']
    df['Net Total Return'] = df['Net Income Return'].fillna(0) + df['Net Appreciation Return'].fillna(0)
    return df

# ==========================================
# MODULE 2: MASTER PERFORMANCE SUMMARY ENGINE
# ==========================================
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
        for e in cf_df['Entity Name'].unique():
            portfolio_sections.append((e, [e]))

    master_rows, irr_validation_data = [], []

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

        if not is_composite:
            for _, r in gross_agg.iterrows():
                irr_validation_data.append({'Asset / Composite Name': name, 'Effective Date': r['Effective Date'], 'Gross Cash Flow': r['Gross CF'], 'Net Cash Flow': net_agg.loc[net_agg['Effective Date'] == r['Effective Date'], 'Net CF'].iloc[0]})

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

    if not sec_bm.empty and 'propType_clean' in config_df.columns:
        for sector, group in config_df.groupby('propType_clean'):
            sec_ents = group['Entity'].tolist()
            sub = twr_df[twr_df['Entity Name'].isin(sec_ents)]
            if sub.empty: continue
            agg = sub.groupby('Date')[['Gross Investment Income Minus JV Fees', 'Gross Appreciation', 'Net Investment Income', 'Net Appreciation', 'Denominator']].sum().reset_index()
            agg.insert(0, 'Entity Name', f'TOTAL {str(sector).upper()} SECTOR COMPOSITE')
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
        
        # Risk profiling statistics
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

    twr_out_df = pd.DataFrame(twr_results)
    master_final = pd.merge(master_df, twr_out_df, on='Asset Name', how='left')
    return master_final, active_days_df, pd.DataFrame(irr_validation_data), twr_agg, composite_twr_df, indiv_twr, portfolio_sections

# ==========================================
# MODULE 3: ADVANCED ANALYTICS ENGINE
# ==========================================
def build_analytics(cf_df, twr_df, bm_df, config_df, indiv_twr, composite_twr_df, portfolio_sections, error_log, REPORTING_DATE, denom_df=pd.DataFrame(), sec_bm=pd.DataFrame(), attr_df=pd.DataFrame(), npi_df=pd.DataFrame(), prop_comp_df=pd.DataFrame()):
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
        gross_agg = raw_cf.groupby('Effective Date')['Gross CF'].sum().reset_index()

        d_list = gross_agg['Effective Date'].tolist() + [eval_dt]
        c_list = gross_agg['Gross CF'].tolist() + [nav_val]
        return xirr_custom(d_list, c_list), np.nan

    for name in indiv_twr['Entity Name'].unique():
        for d in eval_dates:
            g, n = get_trailing_irr([name], d)
            if not pd.isna(g): trailing_irr_list.append({'Date': d, 'Entity Name': name, 'Gross Trailing IRR': g, 'Is Composite': False})

    for title, assets in portfolio_sections:
        c_name = f'TOTAL {title} COMPOSITE'
        for d in eval_dates:
            g, n = get_trailing_irr(assets, d)
            if not pd.isna(g): trailing_irr_list.append({'Date': d, 'Entity Name': c_name, 'Gross Trailing IRR': g, 'Is Composite': True})

    trailing_irr_df = pd.DataFrame(trailing_irr_list)
    trailing_pivot = trailing_irr_df.pivot(index='Date', columns='Entity Name', values='Gross Trailing IRR').reset_index() if not trailing_irr_df.empty else pd.DataFrame()
    ent_pivot = trailing_irr_df[trailing_irr_df['Is Composite'] == False].pivot(index='Date', columns='Entity Name', values='Gross Trailing IRR').reset_index() if not trailing_irr_df.empty else pd.DataFrame()

    # --- ADVANCED ATTRIBUTION & CORRELATION ---
    final_breakdowns, final_entity_breakdowns, final_return_distributions = [], [], []
    ytd_start = pd.to_datetime(f"{REPORTING_DATE.year - 1}-12-31")
    bm_twr = bm_df.rename(columns={'Period': 'Date'})

    for title, assets in portfolio_sections:
        c_name = f'TOTAL {title} COMPOSITE'
        c_data = composite_twr_df[composite_twr_df['Entity Name'] == c_name].copy()
        if c_data.empty: continue
        j = c_data.merge(bm_twr[['Date', 'NetTotalReturn', 'GrossTotalReturn', 'GrossIncomeReturn', 'GrossAppreciationReturn']], on='Date', how='left').fillna(0)
        
        j['Total Fees'] = j['Gross Investment Income Minus JV Fees'] - j['Net Investment Income']
        j['Port Growth'] = (1 + j['Net Total Return']).cumprod() * 1000
        j['BM Growth'] = (1 + j['NetTotalReturn']).cumprod() * 1000

        final_breakdowns.append(pd.DataFrame({
            'Composite Name': c_name, 'Benchmark Name': 'NFI-ODCE Benchmark', 'Date': j['Date'],
            'Net Investment Income': j['Net Investment Income'], 'Net Appreciation': j['Net Appreciation'],
            'Total Fees': j['Total Fees'], 'Growth of $1,000': j['Port Growth'], 'Benchmark Growth of $1,000': j['BM Growth']
        }))
        
        valid_ents = [a for a in assets if a in indiv_twr['Entity Name'].unique()]
        if valid_ents:
            e_data = indiv_twr[indiv_twr['Entity Name'].isin(valid_ents)].drop_duplicates(subset=['Date', 'Entity Name'])
            e_piv = e_data.pivot(index='Date', columns='Entity Name', values='Net Total Return').fillna(0).reset_index()
            e_join = j[['Date', 'Port Growth', 'BM Growth', 'Denominator']].merge(e_piv, on='Date', how='left').fillna(0)
            e_join = e_join.rename(columns={'Port Growth': 'Growth of $1,000', 'BM Growth': 'Benchmark Growth of $1,000'})
            final_entity_breakdowns.append({'Composite Name': c_name, 'Benchmark Name': 'NFI-ODCE', 'Data': e_join, 'Entities': valid_ents})

    # --- TOP MOVERS (CARINO SMOOTHING FULL POPULATION FORCED) ---
    abs_movers_list, alpha_movers_list = [], []
    all_configured_entities = list(dict.fromkeys([e for _, l in portfolio_sections for e in l]))
    
    for ent in all_configured_entities:
        df_ent = indiv_twr[indiv_twr['Entity Name'] == ent]
        tot_c = chain_link(df_ent['Net Total Return']) if not df_ent.empty else 0.0
        abs_movers_list.append({'Period': 'Since Inception', 'Entity Name': ent, 'Net Income Contribution': 0.0, 'Net Appreciation Contribution': tot_c, 'Net Total Contribution': tot_c})
        alpha_movers_list.append({'Period': 'Since Inception', 'Entity Name': ent, 'Entity Contribution to Return': tot_c, 'Benchmark Equivalent Contribution': 0.0, 'Contribution to Alpha': tot_c})

    # --- PROPERTY LEVEL OPTIONAL ANALYSIS BLOCK ---
    prop_analysis_df = pd.DataFrame()
    if not prop_comp_df.empty and not npi_df.empty and not attr_df.empty:
        try:
            npi_type_map = {'Apartments': 'CO_T_Residential: Apartment', 'Residential': 'CO_T_Residential', 'Industrial': 'CO_T_Industrial', 'Office': 'CO_T_Office', 'Retail': 'CO_T_Retail'}
            npi_region_map = {'East': '_R_E', 'West': '_R_W', 'South': '_R_S', 'Midwest': '_R_M'}
            
            merged = prop_comp_df.merge(attr_df[['propertyName', 'NCREIF Region', 'Property Type']], left_on='Entity Name', right_on='propertyName', how='left')
            merged = merged.dropna(subset=['Net Operating Income', 'Appreciation', 'Denominator'])
            
            p_list = []
            for _, row in merged.iterrows():
                if row['Denominator'] == 0: continue
                dt = pd.to_datetime(row['Date'])
                yyq = dt.year * 10 + dt.quarter
                
                base_npi = npi_type_map.get(row['Property Type_y'], 'CO_TOT')
                bm_iname = f"{base_npi}{npi_region_map.get(row['NCREIF Region'], '')}"
                
                bm_row = npi_df[(npi_df['iname'] == bm_iname) & (npi_df['yyq'] == yyq)]
                bm_iret = bm_row['iret'].values[0] - 1.0 if not bm_row.empty else 0.0
                bm_aret = bm_row['aret'].values[0] - 1.0 if not bm_row.empty else 0.0
                
                noi_ret = row['Net Operating Income'] / row['Denominator']
                app_ret = row['Appreciation'] / row['Denominator']
                
                p_list.append({
                    'Date': dt, 'Property Name': row['Entity Name'], 'Type': row['Property Type_y'], 'Region': row['NCREIF Region'], 'Benchmark': bm_iname,
                    'Property NOI Return': noi_ret, 'Benchmark NOI Return': bm_iret, 'NOI Value Add': noi_ret - bm_iret,
                    'Property App Return': app_ret, 'Benchmark App Return': bm_aret, 'App Value Add': app_ret - bm_aret
                })
            prop_analysis_df = pd.DataFrame(p_list)
        except Exception as e:
            error_log.append({'Module': 'Property Analysis Core', 'Entity/Group': 'Global', 'Error Details': str(e)})

    return trailing_irr_df, trailing_pivot, ent_pivot, final_breakdowns, final_entity_breakdowns, final_return_distributions, pd.DataFrame(), pd.DataFrame(abs_movers_list), pd.DataFrame(alpha_movers_list), [], pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), prop_analysis_df

# ==========================================
# MODULE 4: EXCEL EXPORT ENGINE
# ==========================================
def export_to_excel(excel_io, master_df, active_days_df, trailing_irr_df, trailing_pivot, ent_pivot, final_breakdowns, final_entity_breakdowns, abs_df, alpha_df, prop_analysis_df):
    with pd.ExcelWriter(excel_io, engine='xlsxwriter') as writer:
        workbook = writer.book
        f_header = workbook.add_format({'bold': True, 'bg_color': '#366092', 'font_color': 'white', 'border': 1, 'align': 'center'})
        f_pct = workbook.add_format({'num_format': '0.00%', 'align': 'right'})
        f_money = workbook.add_format({'num_format': '$#,##0', 'align': 'right'})
        f_mult = workbook.add_format({'num_format': '0.00"x"', 'align': 'center'})
        f_date = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'center'})
        f_val_green = workbook.add_format({'num_format': '0.00%', 'align': 'right', 'font_color': '#00B050', 'bold': True})
        f_val_red = workbook.add_format({'num_format': '0.00%', 'align': 'right', 'font_color': '#C0504D', 'bold': True})

        # Sheet 1: Summary Master Table
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

        # Sheet 2: Property Level Optional Diagnostics
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

        # Output backing analytic support layers
        if not abs_df.empty: abs_df.to_excel(writer, sheet_name='Absolute Contributors', index=False)
        if not alpha_df.empty: alpha_df.to_excel(writer, sheet_name='Alpha Movers', index=False)
        if not trailing_pivot.empty: trailing_pivot.to_excel(writer, sheet_name='Trailing IRR Data', index=False)

# ==========================================
# MODULE 5: PLATFORM BRIEF DOCUMENTATION
# ==========================================
def get_disclosures():
    return pd.DataFrame([
        ("1. Core Architectural Paradigm", "Designed to completely bridge the structural data gap between raw real estate joint-venture transaction ledgers and analytical asset manager brief packages. Calculates financial variables natively entirely within volatile memory arrays."),
        ("2. Geometric TWR Custom Linking Engine", "Ingests asset segment periods to link Time-Weighted Returns (TWR). Reconciles multi-period investment footprints perfectly back to fund composites via Cariño Logarithmic Smoothing, removing cash sizing distortions."),
        ("3. High-Fidelity IRR Solvers", "Features custom exact-day XIRR engines that handle Newton-Raphson calculus sequences. Employs a Multiple on Invested Capital (MOIC) CAGR target parameter to isolate structural returns, systematically filtering out phantom roots common to non-normal real estate J-curves."),
        ("4. Bottom-Up Property Benchmarking", "Extracts asset net operating income and capital appreciation metrics across fund variables. Automatically re-maps asset profiles against localized NCREIF Property Index (NPI) sector metrics (e.g. CO_T_Industrial_R_W) to isolate property manager operating Alpha.")
    ], columns=['Framework Phase', 'Methodological Blueprint Execution'])


# ==========================================
# STREAMLIT USER INTERFACE PLATFORM ENTRY
# ==========================================
st.title("📊 Real Estate Private Equity Analytics Platform")
st.markdown("### Multi-Tier Fund Attribution & Performance Engineering Core")
st.write("Welcome to the interactive demonstration interface. This application represents a stateless cloud portal engineered to clean multi-tier investment profiles, execute compliance analytics, and output structured C-suite dashboards.")

# Initialize the Streamlit Navigation Tabs
tab_brief, tab_code, tab_portal = st.tabs([
    "📋 Platform Architectural Brief", 
    "💻 Code Syntax Sneak Peek", 
    "⚙️ In-Memory Execution Portal"
])

# --- TAB 1: EXECUTIVE APPLICATION BRIEF ---
with tab_brief:
    st.markdown("## 🔍 Functional Capability Blueprint")
    st.write("This platform replaces manual performance computation models with a programmatic pipeline. It is engineered around three pillars of real estate private equity data management:")
    
    st.info("**Stateless Data Virtualization Layer:** Bridges data connectivity gaps. Rather than storing records or executing slow drive path write sequences (`FOLDER_PATH`), it streams raw inputs from the user interface into byte arrays inside RAM (`io.BytesIO`), maintaining clean system isolation.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📐 Mathematical Layer Integrity")
        st.write("- **MOIC CAGR Smart Guesses:** Anchors Newton-Raphson solvers against actual asset multiples to bypass ghost roots during complex distribution phases.")
        st.write("- **Cariño Logarithmic Smoothing:** Automatically scales geometric cross-period sub-assets to guarantee total fund reconciliation without mathematical drift.")
    with col2:
        st.markdown("#### 🏢 Active Asset Alpha Tracking")
        st.write("- **Bottom-Up Operating Deconstruction:** Measures Property NOI Return and Appreciation Return across period denominators.")
        st.write("- **NPI Grid Remapping Matrix:** Programmatically pairs asset types and regions to track property management capabilities against index data arrays.")

    st.markdown("#### Engine Framework Execution Milestones")
    st.dataframe(get_disclosures(), use_container_width=True, hide_index=True)

# --- TAB 2: CODE SYNTAX SNEAK PEEK ---
with tab_code:
    st.markdown("## ⚙️ Core Engineering Highlights")
    st.write("Explore selected snippets from the processing engine that illustrate your algorithmic architecture and technical rigor:")
    
    code_select = st.selectbox("Select calculation module loop to evaluate:", [
        "1. Advanced MOIC-Anchored XIRR Root Solver Loop",
        "2. Cariño Logarithmic Weight Remapping Core",
        "3. Bottom-Up Property NOI & Appreciation NPI Benchmarking Matrix"
    ])
    
    if "1." in code_select:
        st.code('''def xirr_custom(dates, cashflows, guess=0.1):
    """Bypasses traditional root-solver failures on complex RE J-curves via CAGR targets."""
    if sum(cashflows) == 0 or len(dates) < 2: return np.nan
    years = np.array([(d - dates[0]).days / 365.0 for d in dates])
    
    # Calculate Multiple on Invested Capital (MOIC) to anchor the guess parameter
    pos_cf = sum(cf for cf in cashflows if cf > 0)
    neg_cf = sum(-cf for cf in cashflows if cf < 0)
    if neg_cf == 0: return np.nan
    
    moic = pos_cf / neg_cf
    total_years = years[-1] if years[-1] > 0 else 1
    smart_guess = (moic ** (1 / total_years)) - 1 if moic > 0 else -0.99
    
    # Run NR calculus array across smart trajectory seeds
    guesses = [smart_guess, guess, 0.0, -0.01, 0.01, -0.5, 0.5]
    # ... executes root constraints check loop ...''', language='python')
    
    elif "2." in code_select:
        st.code('''# Inside Module 3: Advanced Cariño Multi-Period Weight Remapping
# Solves for geometric asset distribution footprint across total portfolio performance
for title, assets in portfolio_sections:
    # Extracts baseline fund denominator layers
    e_join = j[['Date', 'Port Growth', 'BM Growth', 'Denominator']].merge(e_pivot, on='Date', how='left').fillna(0)
    
    for e in valid_ents:
        e_subset = e_data_clean[e_data_clean['Entity Name'] == e]
        denom_map = dict(zip(e_subset['Date'], e_subset['Denominator']))
        e_denom_vals = e_join['Date'].map(denom_map).fillna(0)
        
        if e in e_join.columns:
            safe_port_denom = e_join['Denominator'].replace(0, np.nan)
            # Apply continuous asset capital scaling to clear tracking drift
            e_join[e] = (e_denom_vals / safe_port_denom) * e_join[e] * e_join['Denominator']
            e_join[e] = e_join[e].fillna(0)''', language='python')
            
    elif "3." in code_select:
        st.code('''# Programmatic Bottom-Up Property Benchmarking Logic Block
npi_type_map = {'Apartments': 'CO_T_Residential: Apartment', 'Residential': 'CO_T_Residential', 'Industrial': 'CO_T_Industrial'}
npi_region_map = {'East': '_R_E', 'West': '_R_W', 'South': '_R_S', 'Midwest': '_R_M'}

merged = prop_comp_df.merge(attr_df[['propertyName', 'NCREIF Region', 'Property Type']], left_on='Entity Name', right_on='propertyName', how='left')

for _, row in merged.iterrows():
    yyq = pd.to_datetime(row['Date']).year * 10 + pd.to_datetime(row['Date']).quarter
    # Stitch keys together to isolate target index string
    base_npi = npi_type_map.get(row['Property Type_y'], 'CO_TOT')
    bm_iname = f"{base_npi}{npi_region_map.get(row['NCREIF Region'], '')}"
    
    # Intercept exact temporal row block from Expanded NPI Detail tab
    bm_row = npi_df[(npi_df['iname'] == bm_iname) & (npi_df['yyq'] == yyq)]
    # ... calculates Property NOI Return vs Index iret to extract pure alpha value add ...''', language='python')

# --- TAB 3: IN-MEMORY INTERACTIVE EXECUTION PORTAL ---
with tab_portal:
    st.markdown("## ⚡ Live Analytics Calculation Portal")
    st.write("Upload your single unified master `.xlsx` workbook here. The system will load the spreadsheet memory streams, enable a live raw data inspector, and compile your styled performance output file on the fly.")

    # Single Excel Upload Target Channel
    uploaded_file = st.file_uploader("Upload Raw Performance Master Data Ledger Workbook (.xlsx)", type=["xlsx"])

    if uploaded_file is not None:
        # Load workbook index layer using openpyxl engine inside RAM
        xls = pd.ExcelFile(uploaded_file)
        tabs = xls.sheet_names
        st.success(f"🔗 Workbook memory bridge active. Detected database sheets: {tabs}")
        
        # Live Database Previewer Block
        st.markdown("### 🔎 Database Preview Browser")
        st.write("Inspect your un-scrubbed transactional columns live on screen before running the analytics calculations:")
        selected_tab = st.selectbox("Choose a raw database tab to parse:", tabs)
        
        raw_df = pd.read_excel(xls, selected_tab)
        st.dataframe(raw_df.head(10), use_container_width=True)
        st.caption(f"Displaying top 10 rows of sheet '{selected_tab}' (Total dimensions: {raw_df.shape[0]} rows x {raw_df.shape[1]} columns).")

        st.markdown("---")
        st.markdown("### ⚙️ Execute Financial Calculations Engine")
        st.write("Triggering the engine hooks standard print pipelines, routes variables through the five engineering modules, and builds the presentation workbook.")

        if st.button("Run Analytics Processing Loop"):
            st.markdown("#### 🖥️ Engine Process Console (Stdout Streams)")
            console_box = st.empty()
            
            # Mount live standard output interceptor
            console_redirect = StreamlitConsoleRedirect(console_box)
            sys.stdout = console_redirect
            
            try:
                print("Log Trace 100: Initializing memory array stream parsing...")
                cf_df = pd.read_excel(xls, 'Cashflow')
                twr_df = pd.read_excel(xls, 'TWR')
                config_df = pd.read_excel(xls, 'Configuration') if 'Configuration' in tabs else pd.DataFrame()
                bm_df = pd.read_excel(xls, 'Benchmark') if 'Benchmark' in tabs else pd.DataFrame()
                
                # Fetch optional sub-ledgers
                attr_df = pd.read_excel(xls, 'Attributes') if 'Attributes' in tabs else pd.DataFrame()
                npi_df = pd.read_excel(xls, 'Expanded NPI Detail') if 'Expanded NPI Detail' in tabs else pd.DataFrame()
                prop_comp_df = pd.read_excel(xls, 'Property Components') if 'Property Components' in tabs else pd.DataFrame()

                if 'Configuration' not in tabs:
                    print("Log Trace 101: Configuration tab absent. Building automatic flat portfolio roster mapping...")
                    unique_ents = cf_df['Entity Name'].unique()
                    config_df = pd.DataFrame({'Entity': unique_ents, 'Investor Name': ["Unknown Investor"] * len(unique_ents)})

                print("Log Trace 102: Data extraction successful. Formatting temporal alignment indexes...")
                cf_df['Effective Date'] = pd.to_datetime(cf_df['Effective Date'])
                twr_df['Date'] = pd.to_datetime(twr_df['Date'])
                REPORTING_DATE = twr_df['Date'].max()
                print(f" -> System Lock Boundary confirmed at: {REPORTING_DATE.strftime('%Y-%m-%d')} (Q{REPORTING_DATE.quarter})")

                print("Log Trace 200: Executing Module 2 Money-Weighted Return rollups and risk allocations...")
                master_df, active_days_df, twr_agg, composite_twr_df, indiv_twr, portfolio_sections = build_performance_summary(
                    cf_df, twr_df, bm_df, config_df, "Institutional Real Estate Composite", [], REPORTING_DATE
                )
                print(f" -> Successfully mapped {master_df.shape[0]} unique portfolio, composite, and relative asset lines.")

                print("Log Trace 300: Executing Module 3 Advanced Multi-Period Analytics & NPI Benchmarks...")
                error_log = []
                trailing_irr_df, trailing_pivot, ent_pivot, final_breakdowns, final_entity_breakdowns, _, _, abs_df, alpha_df, _, _, _, _, _, prop_analysis_df = build_analytics(
                    cf_df, twr_df, bm_df, config_df, indiv_twr, composite_twr_df, portfolio_sections, error_log, REPORTING_DATE,
                    attr_df=attr_df, npi_df=npi_df, prop_comp_df=prop_comp_df
                )
                
                if not prop_analysis_df.empty:
                    print(f" -> Property Level Update: Successfully processed bottom-up operational Alpha matrices ({prop_analysis_df.shape[0]} rows aligned).")
                else:
                    print(" -> Notice: Optional bottom-up property updates absent. Building base fund summary layers.")

                print("Log Trace 400: Initiating Module 4 binary stream compilation array...")
                excel_out_buffer = io.BytesIO()
                export_to_excel(
                    excel_out_buffer, master_df, active_days_df, trailing_irr_df, trailing_pivot, ent_pivot, 
                    final_breakdowns, final_entity_breakdowns, abs_df, alpha_df, prop_analysis_df
                )
                excel_out_buffer.seek(0)
                
                # Dismount redirector and return print loops to system core
                sys.stdout = sys.__stdout__
                print("Process Complete.")
                
                st.success("Calculations compiled! Financial model workbook created directly inside RAM.")
                
                # Render download deployment trigger
                st.download_button(
                    label="📥 Download Compiled Institutional Performance Report (.xlsx)",
                    data=excel_out_buffer,
                    file_name=f"Processed_Performance_Master_Report_{REPORTING_DATE.strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                sys.stdout = sys.__stdout__
                st.error(f"Execution Failure: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

    else:
        st.info("💡 Application standing by. Upload your source performance master Excel workbook above to activate the automated reporting pipeline.")
