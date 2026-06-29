# =====================================================================
# WEB APPLICATION INTERFACE CORE PLATFORM
# =====================================================================
import streamlit as st
import pandas as pd
import io
import os
import sys
from src.summary_engine import build_performance_summary
from src.analytics_engine import build_analytics
from src.excel_exporter import export_to_excel
from src.documentation import get_disclosures

# Intercept Print lines for Web Output Console Tracker Box
class StreamlitConsoleRedirect:
    def __init__(self, code_placeholder):
        self.code_placeholder = code_placeholder
        self.output_log = ""
    def write(self, text):
        self.output_log += text
        self.code_placeholder.code(self.output_log)
    def flush(self):
        pass

# Render Application Page Shell Header Elements
st.title("📊 Institutional Real Estate Portfolio Analytics Platform")
st.write("---")

# Setup 3-Tab Structural Architecture Layout Showcase
tab_brief, tab_code, tab_engine = st.tabs(["📋 Platform Overview", "💻 Source Code Sneak-Peak", "⚙️ Run Analytical Calculation Core"])

# ---------------------------------------------------------------------
# TAB 1: EXECUTIVE APPLICATION OVERVIEW BRIEF
# ---------------------------------------------------------------------
with tab_brief:
    st.markdown("## Platform Brief & Functional Value Proposition")
    st.write("This platform replaces manual spreadsheet calculations in private equity performance tracking with an automated Python pipeline.")
    
    st.markdown("""
    ### Key Engineering Capabilities Addressed:
    * **Stateless Memory Virtualization:** Utilizes `io.BytesIO` structures to execute deep file analysis safely inside server volatile RAM without local system directory storage.
    * **Hardened Custom XIRR Solvers:** Employs an economically anchored guess algorithm derived from Multiple on Invested Capital (MOIC) variables to maintain solver balance over erratic J-curves.
    * **Cariño Logarithmic Contribution Smoothing:** Remaps cross-period investment footprints to guarantee that individual property return contributions perfectly link back to overall composite totals.
    * **Granular NPI Alpha Benchmarking:** Ingests asset-level records, links properties to matching regional NCREIF Property Index metrics, and measures net management outperformance.
    """)
    
    st.markdown("### Underlying Data Definition Structure")
    st.dataframe(get_disclosures(), use_container_width=True)

# ---------------------------------------------------------------------
# TAB 2: SOURCE CODE ACCESSIBILITY SYNTAX SHOWCASE
# ---------------------------------------------------------------------
with tab_code:
    st.markdown("## Production Source Syntax Pipeline Preview")
    st.write("Examine the clean engineering implementation design paradigms of the core modules below:")
    
    src_module = st.selectbox("Select a decoupled production file to review:", ["src/math_core.py", "src/summary_engine.py", "src/analytics_engine.py", "src/excel_exporter.py"])
    
    try:
        with open(src_module, "r") as f:
            st.code(f.read(), language="python")
    except FileNotFoundError:
        st.info(f"Save '{src_module}' into your working repository subdirectory to display syntax structure lines live here.")

# ---------------------------------------------------------------------
# TAB 3: STREAM PROCESSING ENGINE LAYER (THE INTERACTIVE TOOL)
# ---------------------------------------------------------------------
with tab_engine:
    st.markdown("## Interactive Calculation Sandbox")
    st.write("Test the engine below. You can view the raw input workbook data live, step through the runtime compilation tracking codes, and download the institutional compiled output report.")
    
    # Define standard repository path for the demo file
    DEMO_FILE_PATH = "src/Performance-Master 918000 4.xlsx"
    
    # Streamlit sidebar controls for ingestion sourcing
    st.sidebar.markdown("### 📥 Source File Settings")
    data_source = st.sidebar.radio(
        "Choose Inbound Data Feed:",
        ["Use Live Embedded Demo File (Recommended)", "Upload Custom Master Workbook"]
    )
    
    active_workbook = None
    
    if data_select := (data_select if 'data_select' in locals() else None):
        pass

    if data_select := ("Use Live" in data_select if 'data_select' in locals() else (data_source == "Use Live Embedded Demo File (Recommended)")):
        if os.path.exists(DEMO_FILE_PATH):
            active_workbook = DEMO_FILE_PATH
            st.success("✅ Connected natively to embedded institutional sample file (`Performance-Master 918000 4.xlsx`).")
        else:
            st.warning(f"⚠️ Embedded demo file not detected at `{DEMO_FILE_PATH}`. Please upload a custom workbook below or verify your repository folder structure.")
    else:
        uploaded_file = st.file_uploader("Upload Master Performance Data Workbook (.xlsx)", type=["xlsx"])
        if uploaded_file is not None:
            active_workbook = uploaded_file
            st.success("📊 Custom investor workbook successfully bridged into server RAM.")

    # Execute downstream tracking logic only if a workbook handle is validated
    if active_workbook is not None:
        xls = pd.ExcelFile(active_workbook)
        sheets = xls.sheet_names
        
        # Live Database Previewer Block showing how raw/chaotic the data is
        st.markdown("### 🔎 Live Raw Database Inspector")
        st.write("Toggle through the raw sheets below to examine the un-scrubbed transactional rows, chaotic ledgers, and complex structural layers before running the compiler logic:")
        
        sheet_select = st.selectbox("Choose a raw database tab to analyze:", sheets)
        raw_df = pd.read_excel(xls, sheet_select)
        st.dataframe(raw_df.head(12), use_container_width=True)
        st.caption(f"Displaying top 12 raw data records from sheet '{sheet_select}' (Total Matrix Shape: {raw_df.shape[0]} rows x {raw_df.shape[1]} columns).")
            
        st.write("---")
        st.markdown("### ⚙️ Run Calculations Core Pipeline")
        st.write("Triggering the engine hooks standard print pipelines, routes variables through the engineering packages, and dynamically generates the formatted output sheet directly inside RAM.")
        
        if st.button("Execute Portfolio Engine"):
            st.markdown("#### 🖥️ Active Server Terminal Log Stream (Stdout)")
            console_box = st.empty()
            
            # Route print handles to web component view
            sys.stdout = StreamlitConsoleRedirect(console_box)
            
            try:
                print("Log Trace 100: Initializing spreadsheet workbook array memory maps...")
                cf_df = pd.read_excel(xls, 'Cashflow')
                twr_df = pd.read_excel(xls, 'TWR')
                config_df = pd.read_excel(xls, 'Configuration') if 'Configuration' in sheets else pd.DataFrame()
                bm_df = pd.read_excel(xls, 'Benchmark') if 'Benchmark' in sheets else pd.DataFrame()
                
                # Ingest optional property tables
                attr_df = pd.read_excel(xls, 'Attributes') if 'Attributes' in sheets else pd.DataFrame()
                npi_df = pd.read_excel(xls, 'Expanded NPI Detail') if 'Expanded NPI Detail' in sheets else pd.DataFrame()
                prop_comp_df = pd.read_excel(xls, 'Property Components') if 'Property Components' in sheets else pd.DataFrame()

                if 'Configuration' not in sheets:
                    print("Log Trace 101: Configuration tab absent. Building automatic flat portfolio roster mapping...")
                    unique_ents = cf_df['Entity Name'].unique()
                    config_df = pd.DataFrame({'Entity': unique_ents, 'Investor Name': ["Unknown Investor"] * len(unique_ents)})

                print("Log Trace 102: Data extraction successful. Formatting temporal alignment indexes...")
                cf_df['Effective Date'] = pd.to_datetime(cf_df['Effective Date'])
                twr_df['Date'] = pd.to_datetime(twr_df['Date'])
                REPORTING_DATE = twr_df['Date'].max()
                print(f" -> Portfolio measurement lock boundary confirmed at: {REPORTING_DATE.strftime('%Y-%m-%d')}")

                print("Log Trace 200: Executing Module 2 Money-Weighted XIRR matrices & TWR fund link summaries...")
                master_df, active_days_df, twr_agg, composite_twr_df, indiv_twr, portfolio_sections = build_performance_summary(
                    cf_df, twr_df, bm_df, config_df, "Housing Platform Fund LP", [], REPORTING_DATE
                )
                print(f" -> Computed {master_df.shape[0]} unique portfolio composite clusters.")

                print("Log Trace 300: Executing Module 3 Advanced Geometric Attribution and Optional NPI Grid Loops...")
                error_log = []
                trailing_irr_df, trailing_pivot, ent_pivot, final_breakdowns, final_entity_breakdowns, _, _, _, _, _, _, _, _, _, prop_analysis_df = build_analytics(
                    cf_df, twr_df, bm_df, config_df, indiv_twr=indiv_twr, composite_twr_df=composite_twr_df, 
                    portfolio_sections=portfolio_sections, error_log=error_log, REPORTING_DATE=REPORTING_DATE,
                    attr_df=attr_df, npi_df=npi_df, prop_comp_df=prop_comp_df
                )
                
                if not prop_analysis_df.empty:
                    print(f" -> Success: Bottom-up property metrics evaluated. Mapped {prop_analysis_df.shape[0]} tracking rows against local NPI targets.")
                else:
                    print(" -> Notice: Optional property tabs not detected. Building default blended composites.")

                print("Log Trace 400: Running Module 4 spreadsheet workbook binary output array layout compilation...")
                excel_buffer = io.BytesIO()
                export_to_excel(excel_buffer, master_df, active_days_df, trailing_irr_df, trailing_pivot, ent_pivot, final_breakdowns, final_entity_breakdowns, [], [], prop_analysis_df)
                excel_buffer.seek(0)
                
                # Restore original print target
                sys.stdout = sys.__stdout__
                st.success("Analysis Complete! Output file layout compiled inside system RAM space.")
                st.write("Click below to download your styled institutional delivery workbook:")
                
                st.download_button(
                    label="📥 Download Compiled Portfolio Report (.xlsx)",
                    data=excel_buffer,
                    file_name=f"Processed_Performance_Summary_{REPORTING_DATE.strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                sys.stdout = sys.__stdout__
                st.error(f"Environmental Compilation Failure: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    else:
        st.info("💡 Awaiting source workbook selection. Choose to run the embedded demo file or upload a custom ledger workbook to activate the analytics pipeline.")
