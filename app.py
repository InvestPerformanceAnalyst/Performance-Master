# =====================================================================
# WEB APPLICATION INTERFACE CORE PLATFORM DEMO
# =====================================================================
import streamlit as st
import pandas as pd
import io
import sys
import os

# Optimize browser real estate: Enforce full-bleed wide layout configuration
st.set_page_config(
    page_title="Institutional Real Estate Portfolio Analytics Platform Demo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# Updated app title targeting the requested showcase format
st.title("📊 Institutional Real Estate Portfolio Analytics Platform Demo")
st.write("---")

tab_brief, tab_code, tab_engine = st.tabs(["📋 Platform Vision & Capabilities", "💻 Source Code Sneak-Peak", "⚙️ Run Analytical Calculation Core"])

# ---------------------------------------------------------------------
# TAB 1: STRATEGIC CAPABILITIES & FIRST-PERSON VISION BRIEF
# ---------------------------------------------------------------------
with tab_brief:
    st.markdown("## Bridging the Gap: From Back-Office Fragmentation to Front-Office Intelligence")
    
    st.write(
        "I engineered this enterprise performance solution for **Affinius Capital**, where it is deployed and widely "
        "utilized across various functional internal teams. My core objective during this initiative was to design and "
        "architect a standardized, highly scalable reporting and analytics tech product capable of solving the structural "
        "data fragmentation and lack of operational standardization inherent across the real estate private equity (REPE) landscape."
    )
    st.write(
        "To demonstrate my capabilities in bridging the gap between back-office raw outputs and front-office actionable intelligence, "
        "I isolated a subset of my core calculation modules and turned them into this interactive web showcase. To preserve complete "
        "institutional compliance and protect proprietary records, all underlying investment positions, asset allocations, and cash "
        "flow history lines have been scrubbed using sanitized data that I manufactured for this presentation."
    )
    
    st.markdown("### 🔍 Core Value-Add Architecture Modules I Shipped Natively:")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ⚖️ Holistic Performance Surveillance & Transparency")
        st.write(
            "Evaluating complex multi-tier vehicles on an isolated metric introduces systemic blind spots. I built a dual-track "
            "financial math engine that computes **both Time-Weighted Returns (TWR) and Internal Rates of Return (IRR)** concurrently "
            "for every single asset, fund vehicle, and customized portfolio sector composite. Displaying these metrics side-by-side "
            "empowers portfolio managers to instantly verify operational asset-level efficiency alongside money-weighted dollar "
            "surveillance across any targeted date horizon."
        )
        st.markdown("#### 🎯 Active Institutional Alpha Benchmarking")
        st.write(
            "True portfolio risk surveillance requires rigorous baseline comparison. My analytics engine automatically maps unstandardized "
            "transaction inputs directly against core institutional indices—including NFI-ODCE and granular bottom-up NCREIF "
            "Property Index (NPI) sectors. By anchoring these matrices to exact chronological quarters, the platform enables "
            "front-office stakeholders to cleanly separate active operational management value-add (Alpha) from passive market tailwinds."
        )
    with col2:
        st.markdown("#### 📊 Instant Contribution Profiling (Top Movers & Detractors)")
        st.write(
            "To remove ambiguity around performance drivers, I integrated a robust, GIPS-compliant **Cariño Logarithmic Attribution "
            "core** that programmatically continuous-smooths multi-period asset returns. This allows the end-user to cut through the noise "
            "and instantly identify the top absolute and relative contributors or detractors driving fund return adjustments. "
            "What used to require hours of manual spreadsheet audit is condensed into a scannable, programmatic summary table."
        )
        st.markdown("#### 📈 Dynamic Trend Diagnostic & Historical Visualization")
        st.write(
            "Data is only valuable if it drives a decision. I engineered automated, interactive visualization chart layers that "
            "allow users to trace historical metrics over time. By visually packaging rolling correlation movements, J-curve cash-flow "
            "progressions, and asset-level duration decay models, the interface turns complex backend financial ledgers into "
            "intuitive, diagnostic trend tools for senior leadership."
        )

    st.markdown("---")
    st.markdown("#### Technical Implementation Blueprint Execution")
    st.dataframe(get_disclosures(), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------
# TAB 2: SOURCE CODE ACCESSIBILITY SYNTAX SHOWCASE (UNRESTRICTED)
# ---------------------------------------------------------------------
with tab_code:
    st.markdown("## Production Source Syntax Pipeline Preview")
    st.write("Examine the clean engineering implementation design paradigms of the decoupled backend modules:")
    src_module = st.selectbox("Select a file block to review syntax structure:", ["src/math_core.py", "src/summary_engine.py", "src/analytics_engine.py", "src/excel_exporter.py"])
    
    try:
        with open(src_module, "r") as f:
            code_content = f.read()
        st.code(code_content, language="python")
    except FileNotFoundError:
        st.info(f"Save '{src_module}' into your working directory folder tree to parse lines live here.")

# ---------------------------------------------------------------------
# TAB 3: STREAM PROCESSING ENGINE LAYER (THE INTERACTIVE TOOL)
# ---------------------------------------------------------------------
with tab_engine:
    st.markdown("## Interactive Calculation Sandbox")
    st.write("Test the calculation engine below. View raw input columns live on screen, monitor real-time standard output console statuses, and extract compiled performance deliverables.")
    
    DEMO_FILE_PATH = "data/Performance_Master_Sample_Inputs.xlsx"
    
    st.sidebar.markdown("### 📥 Source File Settings")
    data_source = st.sidebar.radio(
        "Choose Inbound Data Feed:",
        ["Use Pre-loaded Demo File", "Upload Custom Master Workbook"]
    )
    
    active_bytes = None
    if "Pre-loaded" in data_source:
        if os.path.exists(DEMO_FILE_PATH):
            try:
                with open(DEMO_FILE_PATH, "rb") as f:
                    file_data = f.read()
                
                if b"version https://git-lfs" in file_data[:100]:
                    st.error("❌ **Git LFS Mirror Pointer Error Detected!** \n\n"
                             "The pre-loaded demo spreadsheet file inside your GitHub repository is currently stored as a text shortcut link "
                             "instead of a binary Excel file. Upload the binary file directly using **'Upload Custom Master Workbook'**.")
                else:
                    active_bytes = file_data
                    st.success("✅ Connected to repository demo file (`Performance_Master_Sample_Inputs.xlsx`).")
            except Exception as e:
                st.error(f"Error accessing repository file path: {str(e)}")
        else:
            st.warning(f"⚠️ Sample file not detected at directory location `{DEMO_FILE_PATH}`. Please upload your own workbook below.")
    else:
        uploaded_file = st.file_uploader("Upload Master Performance Workbook (.xlsx)", type=["xlsx"])
        if uploaded_file is not None:
            active_bytes = uploaded_file.getvalue()
            st.success("📊 Custom workbook successfully bridged into server RAM.")

    if active_bytes is not None:
        try:
            xls = pd.ExcelFile(io.BytesIO(active_bytes), engine='openpyxl')
            sheets = xls.sheet_names
            
            # --- NEUTRALIZED RE-PHRASING: BACK-OFFICE LEDGER REVIEWS ---
            st.write("---")
            st.markdown("### 🔎 Back-Office Data Reality: Live Raw Inbound Inspector")
            st.markdown(
                "Before running the underlying calculation loops, utilize this viewer to examine the non-standardized transactional "
                "ledgers, variable column headers, and un-aggregated source structures typical of back-office operational data feeds:"
            )
            
            sheet_select = st.selectbox("Select a raw accounting ledger tab to inspect:", sheets)
            raw_df = pd.read_excel(xls, sheet_select)
            
            # Calculate metrics to display aggregation capability
            total_rows_parsed = 0
            unique_assets = 0
            unique_composites = 0
            
            for sheet_name in sheets:
                try:
                    temp_df = pd.read_excel(io.BytesIO(active_bytes), sheet_name=sheet_name, engine='openpyxl')
                    total_rows_parsed += temp_df.shape[0]
                    if sheet_name == 'Cashflow' and 'Entity Name' in temp_df.columns:
                        unique_assets = temp_df['Entity Name'].nunique()
                    if sheet_name == 'Configuration' and 'Composite Grouping' in temp_df.columns:
                        unique_composites = temp_df['Composite Grouping'].nunique()
                except Exception: pass
            
            if unique_assets == 0 and 'Entity Name' in raw_df.columns:
                unique_assets = raw_df['Entity Name'].nunique()

            st.markdown("#### ⚡ Real-Time Ingested System Profile")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            with m_col1:
                st.metric(label="Ingested Database Tabs", value=f"{len(sheets)} Active Sheets")
            with m_col2:
                st.metric(label="Surveilled Positions", value=f"{unique_assets} Unique Entities")
            with m_col3:
                st.metric(label="Structured Rollups", value=f"{unique_composites} Fund Composites")
            with m_col4:
                st.metric(label="Total Inbound Matrix Size", value=f"{total_rows_parsed:,} Rows")

            st.dataframe(raw_df.head(20), use_container_width=True)
            st.caption(f"📊 Showing top 20 records of tab '{sheet_select}' (Current Sheet Dimensions: {raw_df.shape[0]} rows × {raw_df.shape[1]} columns).")
                
            # --- HIGH-VISIBILITY INTERACTIVE RUN CALLOUT BLOCK ---
            st.write("---")
            st.markdown("### ⚙️ Execute Financial Engineering Engine & Compiler")
            st.info(
                "👉 **Action Required:** Click the button below to execute the backend reporting pipelines. "
                "The system will inject the raw memory streams into your packages, trace execution progress inside "
                "the live console below, and construct a multi-tab chart spreadsheet inside server RAM. \n\n"
                "⚠️ *Performance Note:* Given the total data volume, multi-period Cariño smoothing loops, custom Newton-Raphson IRR "
                "root solvers, and Excel chart-sheet generations, **this calculation loop can take up to 2 minutes to complete.**"
            )
            
            if st.button("🚀 Click Here to Run Portfolio Core & Generate Output Report"):
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
                    master_df, active_days_df, irr_val_df, twr_aggregate_df, composite_twr_df, indiv_twr, portfolio_sections = build_performance_summary(
                        cf_df, twr_df, bm_df, config_df, "Blended Institutional Master Composite", [], REPORTING_DATE
                    )
                    print(f" -> Computed {master_df.shape[0]} unique portfolio composite clusters.")

                    print("Log Trace 300: Executing Module 3 Advanced Geometric Attribution and Optional NPI Grid Loops...")
                    error_log = []
                    
                    trailing_irr_df, trailing_pivot, ent_pivot, final_breakdowns, final_entity_breakdowns, final_return_distributions, j_curve_export, abs_df, alpha_df, corr_matrices, rolling_corr_df, brinson_df, aum_pivot, decay_df, prop_analysis_df = build_analytics(
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
                    export_to_excel(excel_buffer, master_df, active_days_df, irr_val_df, twr_aggregate_df, composite_twr_df, trailing_irr_df, trailing_pivot, ent_pivot, final_breakdowns, final_entity_breakdowns, final_return_distributions, j_curve_export, abs_df, alpha_df, corr_matrices, rolling_corr_df, error_log, get_disclosures(), portfolio_sections, brinson_df, aum_pivot, decay_df, prop_analysis_df)
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
        except Exception as e:
            st.error(f"File Reader Error: Your workbook could not be decoded. {str(e)}")
