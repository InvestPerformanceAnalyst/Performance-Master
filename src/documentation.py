# =====================================================================
# MODULE 5: METHODOLOGY FRAMEWORK & PLATFORM TEXT GLOSSARY
# =====================================================================
import pandas as pd

def get_disclosures():
    return pd.DataFrame([
        ("1. Core Portfolio Automation", "Harnesses raw ledger rows directly inside an active server memory footprint. By leveraging stateless io.BytesIO virtualization layers, reporting records compile instantly without permanent disk storage footprints."),
        ("2. Newton-Raphson Custom Solvers", "To safely evaluate non-normal distribution patterns or erratic investment cycles, the custom XIRR solver anchors iterations against actual capital multiple (MOIC) CAGR parameters. This technique systematically eliminates root-solver anchoring failures on complex real estate J-curves."),
        ("3. Geometric TWR Custom Linking Engine", "Slices discrete calendar intervals to chain-link Time-Weighted Returns (TWR). Reconciles individual position contributions perfectly back to overall fund totals via continuous compounding coefficients (natural logarithms), neutralizing data formatting drift across execution rows."),
        ("4. Bottom-Up Operational Value-Add (Alpha)", "Deconstructs property-level operations into independent Net Operating Income (NOI) and Capital Appreciation components. Elements pair dynamically against highly specific NCREIF regional categories to isolate pure operational Alpha outperformance.")
    ], columns=['Topic', 'Description'])
