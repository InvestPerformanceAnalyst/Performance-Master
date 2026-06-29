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

tab_brief, tab_code, tab_engine = st.tabs(["📋 Platform Vision & Capabilities", "💻 Source Code Sneak-Peak", "⚙️ Run Analytical Calculation Core"])

# ---------------------------------------------------------------------
# TAB 1: STRATEGIC CAPABILITIES BRIEF
# ---------------------------------------------------------------------
with tab_brief:
    st.markdown("## Bridging the Gap: From Back-Office Chaos to Front-Office Intelligence")
    st.write(
        "In institutional real estate private equity, asset surveillance is frequently bottlenecked by unstructured "
        "transaction ledgers, joint-venture partner accounting variations, and fractured history tracking. This platform "
        "is a custom-engineered financial solution designed to scale performance analytics and deliver **clear, actionable intelligence** "
        "directly into the hands of portfolio managers and senior decision-makers."
    )
    
    st.markdown("### 🔍 Core Value-Add Capabilities Shipped Natively:")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ⚖️ Holistic Performance Surveillance")
        st.write(
            "Evaluating performance on a single metric creates a blind spot. This engine runs a dual-track financial core, "
            "computing **both Time-Weighted Returns (TWR) and Internal Rates of Return (IRR)** concurrently for every individual asset, "
            "parent fund, and sector composite. Linking these return profiles side-by-side provides a clean, accurate look at absolute "
            "operational efficiency alongside time-weighted capital deployment metrics."
        )
        st.markdown("#### 🎯 Institutional Relative Benchmarking")
        st.write(
            "True risk tracking demands context. The analytics engine takes flat transactional entries and maps them against "
            "localized benchmarks—including NFI-ODCE and granular regional/sector NCREIF Property Index (NPI) slices. "
            "By establishing exact temporal horizons, it isolates active management outperformance (Alpha) from basic market tailwinds."
        )
    with col2:
        st.markdown("#### 📊 At-a-Glance Contribution Profiling")
        st.write(
            "End-users shouldn't have to guess what is driving performance. The platform integrates a GIPS-compliant "
            "**Cariño Logarithmic Attribution core** that smoothly maps cross-period asset performance. This allows portfolio "
            "managers to instantly filter, identify, and view the top absolute and alpha contributors and detractors driving fund returns."
        )
        st.markdown("#### 📈 Trend Diagnostic & Historical Visualization")
        st.write(
            "The platform includes dynamic, interactive chart engines that let users visually track historical "
            "performance trajectories. By plotting rolling correlation matrices, J-curves, and asset duration drag lines, "
            "the system changes retrospective numbers into a clear look at what is driving active portfolio trends."
        )

    st.markdown("---")
    st.markdown("#### Technical Implementation Blueprint Execution")
    st.dataframe(get_disclosures(), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------
# TAB 2: SOURCE CODE ACCESSIBILITY SYNTAX SHOWCASE (WITH PAYWALL EFFECT)
# ---------------------------------------------------------------------
with tab_code:
    st.markdown("## Production Source Syntax Pipeline Preview")
    st.write("Examine the clean engineering implementation design paradigms of the decoupled backend modules:")
    src_module = st.selectbox("Select a file block to review syntax structure:", ["src/math_core.py", "src/summary_engine.py", "src/analytics_engine.py", "src/excel_exporter.py"])
    
    # RESTORED / ENHANCED: PAYWALL SNEAK-PEEK GRADUAL MOSAIC BLUR EFFECT
    try:
        with open(src_module, "r") as f:
            code_lines = f.readlines()
        
        if len(code_lines) <= 80:
            st.code("".join(code_lines), language="python")
        else:
            # Render first 80 rows natively inside standard code module block
            st.code("".join(code_lines[:80]), language="python")
            
            st.markdown("#### 🔒 RECRUITER PREMIUM INFRASTRUCTURE SNEAK-PEEK")
            # Injecting smooth CSS linear gradient masking and font blur to simulate Wall Street Journal paywall overlays
            paywall_markup = (
                "<div style='background: linear-gradient(to bottom, #000000 0%, rgba(0,0,0,0) 100%); "
                "-webkit-background-clip: text; -webkit-text-fill-color: transparent; font-family: monospace; "
                "font-size: 14px; white-space: pre; overflow: hidden; max-height: 180px; user-select: none; "
                "line-height: 1.4; opacity: 0.30; filter: blur(3.5px); pointer-events: none;'>"
                + "".join(code_lines[80:115]).replace("<", "&lt;").replace(">", "&gt;") + "</div>"
            )
            st.markdown(paywall_markup, unsafe_allow_html=True)
            st.warning("💼 **Recruiter Notice:** Advanced production calculations, multi-period attribution frameworks, and specialized charting architecture layers are restricted to simulate proprietary institutional software. **Hire Sai Yin Ye to unlock core infrastructure architecture rights.**")
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
            
            st.write("---")
            st.markdown("### 🔎 The Accounting Chaos: Live Raw Data Inspector")
            st.markdown(
                "Before triggering the engine calculations, use this browser to see how **unstructured and raw** the transaction ledgers are. "
                "Notice the uneven column counts, shifting timeline fields, and zero-dollar rows typical of joint-venture database dumps:"
            )
            
            sheet_select = st.selectbox("Select a raw accounting ledger tab to inspect:", sheets)
            raw_df = pd.read_excel(xls, sheet_select)
            
            # --- FEATURE ADDED: 2. DYNAMIC WORKBOOK SCALING SUMMARY MATRIX PROFILE ---
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

            st.markdown("#### ⚡ Real-Time Processing System Profile")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            with m_col1:
                st.metric(label="Ingested Database Tabs", value=f"{len(sheets)} Active Sheets")
            with m_col2:
                st.metric(label="Surveilled Positions", value=f"{unique_assets} Unique Entities")
            with m_col3:
                st.metric(label="Structured Rollups", value=f"{unique_composites} Fund Composites")
            with m_col4:
                st.metric(label="Total Inbound Matrix Size", value=f"{total_rows_parsed:,} Rows")
            # --------------------------------------------------------------------------

            st.dataframe(raw_df.head(20), use_container_width=True)
            st.caption(f"📊 Showing top 20 records of tab '{sheet_select}' (Current Sheet Dimensions: {raw_df.shape[0]} rows × {raw_df.shape[1]} columns).")
                
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
