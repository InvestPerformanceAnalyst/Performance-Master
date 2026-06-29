# =====================================================================
# WEB APPLICATION INTERFACE CORE PLATFORM
# =====================================================================
import streamlit as st
import pandas as pd
import io
import sys
import os

from src.summary_engine import build_performance_summary
from src.analytics_engine import build_analytics
from src.excel_exporter import export_to_excel
from src.documentation import get_disclosures

class StreamlitConsoleRedirect:
    def __init__(self, code_placeholder):
        self.code_placeholder = code_placeholder
        self.output_log = ""
    def write(self, text):
        self.output_log += text
        self.code_placeholder.code(self.output_log)
    def flush(self):
        pass

st.title("📊 Institutional Real Estate Portfolio Analytics Platform")
st.write("---")

tab_brief, tab_code, tab_engine = st.tabs(["📋 Platform Overview", "💻 Source Code Sneak-Peak", "⚙️ Run Analytical Calculation Core"])

with tab_brief:
    st.markdown("## Platform Brief & Functional Value Proposition")
    st.write("This engine decouples performance tracking calculations from manual excel files into a structured, production-ready processing pipeline.")
    st.markdown("""
    ### Technical Architectural Breakthroughs:
    * **Stateless Memory Virtualization:** Processes large datasets safely inside server volatile RAM via `io.BytesIO` streams, avoiding any permanent file-writing overhead.
    * **Hardened Custom XIRR Solvers:** Employs an economically anchored guess algorithm to successfully navigate complex real estate J-curves without anchoring to mathematical phantom roots.
    * **Resilient Column-Remapping Layer:** Features programmatic column standardizations to gracefully process accounting files regardless of shifting JV partner fee definitions.
    * **Granular NPI Alpha Benchmarking:** Ingests asset records, pairs them with localized NCREIF Property Index indices, and isolates pure asset-level operational Alpha.
    """)
    st.markdown("### Underlying Data Definition Structure")
    st.dataframe(get_disclosures(), use_container_width=True, hide_index=True)

with tab_code:
    st.markdown("## Production Source Syntax Pipeline Preview")
    st.write("Examine the clean engineering implementation design paradigms of the decoupled backend modules:")
    src_module = st.selectbox("Select a file block to review syntax structure:", ["src/math_core.py", "src/summary_engine.py", "src/analytics_engine.py", "src/excel_exporter.py"])
    try:
        with open(src_module, "r") as f:
            st.code(f.read(), language="python")
    except FileNotFoundError:
        st.info(f"Save '{src_module}' into your working directory folder tree to parse lines live here.")

with tab_engine:
    st.markdown("## Interactive Calculation Sandbox")
    st.write("Test the calculation engine below. View raw input columns live on screen, monitor real-time standard output console statuses, and extract compiled performance deliverables.")
    
    DEMO_FILE_PATH = "data/Performance_Master_Sample_Inputs.xlsx"
    
    st.sidebar.markdown("### 📥 Source File Settings")
    data_source = st.sidebar.radio(
        "Choose Inbound Data Feed:",
        ["Use Pre-loaded Demo File", "Upload Custom Master Workbook"]
    )
    
    active_workbook = None
    if "Pre-loaded" in data_source:
        if os.path.exists(DEMO_FILE_PATH):
            active_workbook = DEMO_FILE_PATH
            st.success("✅ Connected to repository demo file (`Performance_Master_Sample_Inputs.xlsx`).")
        else:
            st.warning(f"⚠️ Sample file not detected at directory location `{DEMO_FILE_PATH}`. Please upload your own workbook below.")
    else:
        uploaded_file = st.file_uploader("Upload Master Performance Workbook (.xlsx)", type=["xlsx"])
        if uploaded_file is not None:
            active_workbook = uploaded_file
            st.success("📊 Custom workbook successfully bridged into server RAM.")

    if active_workbook is not None:
        xls = pd.ExcelFile(active_workbook)
        sheets = xls.sheet_names
        
        st.markdown("### 🔎 Live Raw Database Inspector")
        st.write("Toggle through the tabs below to view the un-scrubbed records, raw transactional rows, and complex layouts before processing:")
        sheet_select = st.selectbox("Choose a raw workbook sheet to parse:", sheets)
        st.dataframe(pd.read_excel(xls, sheet_select).head(12), use_container_width=True)
        st.caption(f"Displaying top 12 rows of tab '{sheet_select}' (Dimensions: {pd.read_excel(xls, sheet_select).shape[0]} rows).")
            
        st.write("---")
        st.markdown("### ⚙️ Assemble Financial Workbook Models")
        
        if st.button("Execute Portfolio Engine"):
            st.markdown("#### 🖥️ Active Server Terminal Log Stream")
            console_box = st.empty()
            sys.stdout = StreamlitConsoleRedirect(console_box)
            
            try:
                print("Log Trace 100: Initializing spreadsheet workbook array memory maps...")
                cf_df = pd.read_excel(xls, 'Cashflow')
                twr_df = pd.read_excel(xls, 'TWR')
                config_df = pd.read_excel(xls, 'Configuration') if 'Configuration' in sheets else pd.DataFrame()
                bm_df = pd.read_excel(xls, 'Benchmark') if 'Benchmark' in sheets else pd.DataFrame()
                
                attr_df = pd.read_excel(xls, 'Attributes') if 'Attributes' in sheets else pd.DataFrame()
                npi_df = pd.read_excel(xls, 'Expanded NPI Detail') if 'Expanded NPI Detail' in sheets else pd.DataFrame()
                prop_comp_df = pd.read_excel(xls, 'Property Components') if 'Property Components' in sheets else pd.DataFrame()

                if 'Configuration' not in sheets:
                    print("Log Trace 101: Configuration data absent. Building default flat portfolio roster...")
                    unique_ents = cf_df['Entity Name'].unique()
                    config_df = pd.DataFrame({'Entity': unique_ents, 'Investor Name': ["Unknown Investor"] * len(unique_ents)})

                print("Log Trace 102: Data extraction successful. Formatting temporal alignment indexes...")
                cf_df['Effective Date'] = pd.to_datetime(cf_df['Effective Date'])
                twr_df['Date'] = pd.to_datetime(twr_df['Date'])
                REPORTING_DATE = twr_df['Date'].max()
                print(f" -> Portfolio measurement lock boundary confirmed at: {REPORTING_DATE.strftime('%Y-%m-%d')}")

                print("Log Trace 200: Processing Module 2 Money-Weighted XIRR matrices & TWR fund link summaries...")
                master_df, active_days_df, twr_agg, composite_twr_df, indiv_twr, portfolio_sections = build_performance_summary(
                    cf_df, twr_df, bm_df, config_df, "Blended Institutional Master Composite", [], REPORTING_DATE
                )
                print(f" -> Computed {master_df.shape[0]} unique portfolio composite clusters.")

                print("Log Trace 300: Executing Module 3 Advanced Geometric Attribution and Optional NPI Grid Loops...")
                error_log = []
                trailing_irr_df, trailing_pivot, ent_pivot, final_breakdowns, final_entity_breakdowns, _, _, abs_df, alpha_df, _, _, _, _, _, prop_analysis_df = build_analytics(
                    cf_df, twr_df, bm_df, config_df, indiv_twr=indiv_twr, composite_twr_df=composite_twr_df, 
                    portfolio_sections=portfolio_sections, error_log=error_log, REPORTING_DATE=REPORTING_DATE,
                    attr_df=attr_df, npi_df=npi_df, prop_comp_df=prop_comp_df
                )
                
                if not prop_analysis_df.empty:
                    print(f" -> Success: Bottom-up property metrics evaluated. Mapped {prop_analysis_df.shape[0]} rows against local NPI targets.")
                else:
                    print(" -> Notice: Optional bottom-up property maps absent. Compiling base summary sheets.")

                print("Log Trace 400: Running Module 4 spreadsheet workbook binary output array layout compilation...")
                excel_buffer = io.BytesIO()
                export_to_excel(excel_buffer, master_df, active_days_df, trailing_irr_df, trailing_pivot, ent_pivot, final_breakdowns, final_entity_breakdowns, abs_df, alpha_df, prop_analysis_df)
                excel_buffer.seek(0)
                
                sys.stdout = sys.__stdout__
                st.success("Analysis Complete! Deliverable workbook compiled natively inside system RAM.")
                
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
