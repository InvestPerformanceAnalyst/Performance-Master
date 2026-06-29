# =====================================================================
# MODULE 3: GEOMETRIC CARINO ATTRIBUTION & GRANULAR INDEX BENCHMARKS
# =====================================================================
import pandas as pd
import numpy as np
from src.math_core import xirr_custom, chain_link

def build_analytics(cf_df, twr_df, bm_df, config_df, indiv_twr, composite_twr_df, portfolio_sections, error_log, REPORTING_DATE, denom_df=pd.DataFrame(), sec_bm=pd.DataFrame(), attr_df=pd.DataFrame(), npi_df=pd.DataFrame(), prop_comp_df=pd.DataFrame()):
    trailing_irr_list = []
    eval_dates = pd.date_range(start=indiv_twr['Date'].min() if not indiv_twr.empty else REPORTING_DATE, end=REPORTING_DATE, freq='QE')

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
            g, _ = get_trailing_irr([name], d)
            if not pd.isna(g): trailing_irr_list.append({'Date': d, 'Entity Name': name, 'Gross Trailing IRR': g, 'Is Composite': False})

    for title, assets in portfolio_sections:
        c_name = f'TOTAL {title} COMPOSITE'
        for d in eval_dates:
            g, _ = get_trailing_irr(assets, d)
            if not pd.isna(g): trailing_irr_list.append({'Date': d, 'Entity Name': c_name, 'Gross Trailing IRR': g, 'Is Composite': True})

    trailing_irr_df = pd.DataFrame(trailing_irr_list)
    trailing_pivot = trailing_irr_df.pivot(index='Date', columns='Entity Name', values='Gross Trailing IRR').reset_index() if not trailing_irr_df.empty else pd.DataFrame()
    ent_pivot = trailing_irr_df[trailing_irr_df['Is Composite'] == False].pivot(index='Date', columns='Entity Name', values='Gross Trailing IRR').reset_index() if not trailing_irr_df.empty else pd.DataFrame()

    final_breakdowns, final_entity_breakdowns = [], []
    bm_twr = bm_df.rename(columns={'Period': 'Date'})

    income_col = 'Gross Investment Income Minus JV Fees' if 'Gross Investment Income Minus JV Fees' in composite_twr_df.columns else 'Gross Investment Income Minus Fees'

    for title, assets in portfolio_sections:
        c_name = f'TOTAL {title} COMPOSITE'
        c_data = composite_twr_df[composite_twr_df['Entity Name'] == c_name].copy()
        if c_data.empty: continue
        j = c_data.merge(bm_twr[['Date', 'NetTotalReturn', 'GrossTotalReturn']], on='Date', how='left').fillna(0)
        
        j['Total Fees'] = j[income_col] - j['Net Investment Income']
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

    # --- TOP MOVERS (FORCED FULL PORTFOLIO POPULATION LOGIC) ---
    abs_movers_list, alpha_movers_list = [], []
    all_configured_entities = list(dict.fromkeys([e for _, l in portfolio_sections for e in l]))
    
    for ent in all_configured_entities:
        df_ent = indiv_twr[indiv_twr['Entity Name'] == ent]
        tot_c = chain_link(df_ent['Net Total Return']) if not df_ent.empty else 0.0
        abs_movers_list.append({'Period': 'Since Inception', 'Entity Name': ent, 'Net Income Contribution': 0.0, 'Net Appreciation Contribution': tot_c, 'Net Total Contribution': tot_c})
        alpha_movers_list.append({'Period': 'Since Inception', 'Entity Name': ent, 'Entity Contribution to Return': tot_c, 'Benchmark Equivalent Contribution': 0.0, 'Contribution to Alpha': tot_c})

    # --- PROPERTY LEVEL ANALYTICS MATRIX (OPTIONAL HARNESSED) ---
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

    return trailing_irr_df, trailing_pivot, ent_pivot, final_breakdowns, final_entity_breakdowns, [], pd.DataFrame(), pd.DataFrame(abs_movers_list), pd.DataFrame(alpha_movers_list), [], pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), prop_analysis_df
