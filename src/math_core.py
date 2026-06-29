# =====================================================================
# MODULE 1: SETUP & QUANTITATIVE MATH CORE HELPERS
# =====================================================================
import numpy as np
import pandas as pd
from scipy.optimize import newton

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
    """Geometrically links single-period return variables to establish cumulative metrics."""
    return np.prod(1 + returns.fillna(0)) - 1

def annualize_return_exact_days(cum_ret, days_active):
    """Transforms a cumulative linked return factor into an annualized day-count rate."""
    if pd.isna(cum_ret) or days_active <= 0: return np.nan
    if days_active < 365: return cum_ret  
    return (1 + cum_ret)**(365.0 / days_active) - 1

def get_period_twr(df, ret_col, end_date, date_col='Date', ytd=False, years=None):
    """Slices a target performance dataframe time-window and returns geometric sub-links."""
    if df.empty: return np.nan
    if ytd:
        start_date = pd.to_datetime(f"{end_date.year - 1}-12-31")
    elif years is not None:
        # fractional quarter adjustment intercept to clear cloud container deployment crashes
        if years == 0.25:
            start_date = end_date - pd.DateOffset(months=3)
        else:
            start_date = end_date - pd.DateOffset(years=int(years))
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
    """Deconstructs net accounting variables down to 6 distinct sub-period components."""
    if df.empty: return df
    df['Denominator'] = df['Denominator'].replace(0, np.nan)
    df['Gross Income Return'] = df['Gross Investment Income Minus Fees'] / df['Denominator']
    df['Gross Appreciation Return'] = df['Total Gross Appreciation'] / df['Denominator']
    df['Gross Total Return'] = df['Gross Income Return'].fillna(0) + df['Gross Appreciation Return'].fillna(0)
    df['Net Income Return'] = df['Net Investment Income'] / df['Denominator']
    df['Net Appreciation Return'] = df['Net Appreciation'] / df['Denominator']
    df['Net Total Return'] = df['Net Income Return'].fillna(0) + df['Net Appreciation Return'].fillna(0)
    return df
