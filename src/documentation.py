# =====================================================================
# MODULE 5: METHODOLOGY FRAMEWORK & PLATFORM TEXT GLOSSARY
# =====================================================================
import pandas as pd

def get_disclosures():
    return pd.DataFrame([
        ("1. Core Portfolio Automation", "The reporting system processes raw multi-tier transactional records entirely within volatile memory spaces. By utilizing virtual io.BytesIO byte arrays, inbound investment rows compile into professional reports without leaving localized session environments."),
        ("2. Newton-Raphson Custom Solvers", "To safely evaluate non-normal cash flow distributions or aggressive development cycles, the custom XIRR engine anchors calculations using an initial target heuristic. This approach prevents systemic anchor failures common to institutional portfolios."),
        ("3. Multi-Period Return Smoothing", "Calculates discrete time-weighted returns by scaling across asset denominators. Multi-period performance linking perfectly matches parent portfolios via Cariño smoothing models, neutralizing data formatting drift across execution rows."),
        ("4. Operational Value-Add (Alpha)", "Bottom-up benchmarking strips apart asset Net Operating Income (NOI) and Appreciation metrics. Elements map dynamically against targeted regional NCREIF Property Index classifications to isolate true operational value add.")
    ], columns=['Methodological Control Module', 'Institutional Specification Parameters'])
