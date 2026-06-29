# =====================================================================
# WEB APPLICATION INTERFACE CORE PLATFORM
# =====================================================================
import streamlit as st
import pandas as pd
import io
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
    st.write("This platform is designed to replace manual spreadsheet calculations in private equity performance tracking with an automated Python pipeline.")
    
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
    
    # Simple dynamic mapping dictionary layout to read code files on-the-fly
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
    st.write("Upload a target master portfolio spreadsheet below. You can preview the raw un-scrubbed records live, monitor the real-time terminal compile console log steps, and extract the generated institutional presentation model.")
    
    uploaded_file = st.file_uploader("Upload Master Performance Data Workbook (.xlsx)", type=["xlsx"])
    
    if uploaded_file is not None:
        xls = pd.ExcelFile(uploaded_file)
        sheets = xls.sheet_names
        
        st.success(f"Workbook connection established. Detected database tabs: {sheets}")
        
        # Subsegment: Show raw elements live
        with st.expander("🔍 Inspect Selected Inbound Sheet Database Live"):
            sheet_select = st.selectbox("Select target tab row pool:", sheets)
            st.dataframe(pd.read_excel(xls, sheet_select).head(10), use_container_width=True)
            st.caption("Displaying first 10 data rows from selected raw data array block.")
            
        st.write("---")
        st.markdown("### Process Workbook Assembly")
        st.write("Trigger the button below to bind stdout pipelines and activate the server-side analysis compiler:")
        
        if st.button("Execute Portfolio Engine"):
            st.markdown("#### 🖥️ Active Server Terminal Log Stream")
            console_box = st.empty()
            
            # Route print handles to web component view
            sys.stdout = StreamlitConsoleRedirect(console_box)
            
            try:
                print("Status Code 100: Initializing spreadsheet workbook array memory maps...")
                cf_df = pd.read_excel(xls, 'Cashflow')
                twr_df = pd.read_excel(xls, 'TWR')
                config_df = pd.read_excel(xls, 'Configuration') if 'Configuration' in sheets else pd.DataFrame()
                bm_df = pd.read_excel(xls, 'Benchmark') if 'Benchmark' in sheets else pd.DataFrame()
                
                # Ingest optional property tables
                attr_df = pd.read_excel(xls, 'Attributes') if 'Attributes' in sheets else pd.DataFrame()
                npi_df = pd.read_excel(xls, 'Expanded NPI Detail') if 'Expanded NPI Detail' in sheets else pd.DataFrame()
                prop_comp_df = pd.read_excel(xls, 'Property Components') if 'Property Components' in sheets else pd.DataFrame()

                print("Status Code 102: Data streams locked. Standardizing date column frames...")
                cf_df['Effective Date'] = pd.to_datetime(cf_df['Effective Date'])
                twr_df['Date'] = pd.to_datetime(twr_df['Date'])
                REPORTING_DATE = twr_df['Date'].max()
                print(f" -> Portfolio measurement lock boundary confirmed at: {REPORTING_DATE.strftime('%Y-%m-%d')}")

                print("Status Code 200: Processing Module 2 Money-Weighted XIRR matrices & TWR fund link summaries...")
                master_df, active_days_df, twr_agg, composite_twr_df, indiv_twr, portfolio_sections = build_performance_summary(
                    cf_df, twr_df, bm_df, config_df, "Housing Platform Fund LP", [], REPORTING_DATE
                )
                print(f" -> Computed {master_df.shape[0]} unique portfolio composite clusters.")

                print("Status Code 300: Processing Module 3 Advanced Geometric Attribution and Optional NPI Grid Loops...")
                error_log = []
                trailing_irr_df, trailing_pivot, ent_pivot, final_breakdowns, final_entity_breakdowns, _, _, _, _, _, _, _, _, _, prop_analysis_df = build_analytics(
                    cf_df, twr_df, bm_df, config_df, indiv_twt=indiv_twr, composite_twr_df=composite_twr_df, 
                    portfolio_sections=portfolio_sections, error_log=error_log, REPORTING_DATE=REPORTING_DATE,
                    attr_df=attr_df, npi_df=npi_df, prop_comp_df=prop_comp_df
                )
                
                if not prop_analysis_df.empty:
                    print(f" -> Success: Bottom-up property metrics evaluated. Mapped {prop_analysis_df.shape[0]} tracking rows against local NPI targets.")
                else:
                    print(" -> Notice: Optional property tabs not detected. Building default blended composites.")

                print("Status Code 400: Running Module 4 spreadsheet workbook binary output array layout compilation...")
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
        st.info("💡 Awaiting source workbook ingestion file. Upload your consolidated spreadsheet master above to launch processing pipelines.")