import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="AHP Priority Calculator", layout="wide")
st.title("🌿 AHP Priority Calculator – Energy Suitability Mapping")
st.markdown("""
**Pairwise comparison matrix for Solar, Wind, and Biomass suitability.**  
Use Saaty's 1–9 scale:  
*1 = equal importance, 3 = moderate, 5 = strong, 7 = very strong, 9 = extreme.*  
**Only fill the upper triangle** (green cells). The rest is automatic.  
Goal: Consistency Ratio (CR) < 0.10.
""")

# ---- AHP core functions (unchanged) ----
def get_ri(n):
    ri_dict = {1:0.00,2:0.00,3:0.58,4:0.90,5:1.12,6:1.24,7:1.32,8:1.41,9:1.45,10:1.49}
    return ri_dict.get(n, 1.51)

def ahp_priority(matrix):
    matrix = np.array(matrix, dtype=float)
    col_sums = matrix.sum(axis=0)
    norm_mat = matrix / col_sums
    return norm_mat.mean(axis=1)

def check_consistency(matrix, priority):
    n = len(matrix)
    weighted_sum = np.dot(matrix, priority)
    lambda_max = np.mean(weighted_sum / priority)
    CI = (lambda_max - n) / (n - 1)
    RI = get_ri(n)
    CR = CI / RI if RI != 0 else 0.0
    return lambda_max, CI, CR

# ---- New: matrix table UI with dropdowns (whole numbers only) ----
def build_matrix_ui(energy_type, criteria):
    st.subheader(f"⚡ {energy_type} – Pairwise Comparison Matrix")
    st.caption("⬆️ **Upper triangle (green background):** click to select 1–9. Lower triangle is automatic reciprocal.")
    
    n = len(criteria)
    # Initialize session state for this energy type
    matrix_key = f"matrix_{energy_type}"
    if matrix_key not in st.session_state:
        # Default: all 1's (equal importance)
        st.session_state[matrix_key] = np.ones((n, n))
    
    # Create a form to capture all edits at once
    with st.form(key=f"form_{energy_type}"):
        # Build the matrix grid using columns
        # First, create header row with criteria names
        cols_header = st.columns([1.5] + [1] * n)  # extra space for row labels
        cols_header[0].markdown("**Criteria →**")
        for j, crit in enumerate(criteria):
            cols_header[j+1].markdown(f"**{crit}**")
        
        # Store updated values temporarily
        new_matrix = st.session_state[matrix_key].copy()
        
        # For each row
        for i in range(n):
            cols = st.columns([1.5] + [1] * n)
            cols[0].markdown(f"**{criteria[i]}**")  # row label
            for j in range(n):
                if i == j:
                    # Diagonal: fixed 1
                    cols[j+1].markdown("1")
                elif i < j:
                    # Upper triangle: editable dropdown
                    current_val = int(new_matrix[i, j])
                    selected = cols[j+1].selectbox(
                        label="",  # no extra label
                        options=[1,2,3,4,5,6,7,8,9],
                        index=current_val-1,
                        key=f"{energy_type}_{i}_{j}",
                        label_visibility="collapsed"
                    )
                    new_matrix[i, j] = float(selected)
                    new_matrix[j, i] = 1.0 / float(selected)  # reciprocal
                else:
                    # Lower triangle: show reciprocal (read-only)
                    reciprocal = new_matrix[i, j]
                    if reciprocal == int(reciprocal):
                        cols[j+1].markdown(f"{int(reciprocal)}")
                    else:
                        # show as fraction or decimal
                        cols[j+1].markdown(f"{reciprocal:.3f}")
        
        # Submit button
        submitted = st.form_submit_button("✅ Update matrix and calculate priorities")
        if submitted:
            st.session_state[matrix_key] = new_matrix
            return new_matrix
    return None

def run_ahp(energy_type, criteria, matrix):
    priorities = ahp_priority(matrix)
    lambda_max, CI, CR = check_consistency(matrix, priorities)
    
    df = pd.DataFrame({
        "Criterion": criteria,
        "Weight (%)": priorities * 100,
        "Rank": priorities.argsort()[::-1] + 1
    }).sort_values("Weight (%)", ascending=False)
    
    st.subheader("📊 AHP Results")
    st.dataframe(df.style.format({"Weight (%)": "{:.2f}"}))
    st.write(f"**λ_max** = {lambda_max:.4f} **CI** = {CI:.4f} **CR** = {CR:.4f}")
    
    if CR < 0.1:
        st.success(f"✅ Consistency Ratio = {CR:.3f} (< 0.10) → Consistent.")
    else:
        st.warning(f"⚠️ Consistency Ratio = {CR:.3f} (≥ 0.10) → Please revise the matrix above.")
    return df, CR

# ---- Main app ----
energy_option = st.sidebar.radio("Select energy type", ["Solar", "Wind", "Biomass"])

criteria_sets = {
    "Solar": ["Active faults","Protected areas","Indigenous areas","Urban/built-up areas",
              "Global horizontal irradiation","Slope","Distance from transmission lines","Distance from roads"],
    "Wind": ["Active faults","Protected areas","Indigenous areas","Urban/built-up areas",
             "Global horizontal irradiation","Slope","Distance from transmission lines","Distance from roads"],
    "Biomass": ["Active faults","Protected areas","Indigenous areas","Urban/built-up areas",
                "Crop residue, per province","Slope","Distance from transmission lines","Distance from roads"]
}

criteria = criteria_sets[energy_option]

# Show criteria in sidebar
st.sidebar.markdown(f"**Criteria for {energy_option} suitability:**")
for c in criteria:
    st.sidebar.markdown(f"- {c}")

# Build matrix UI and get matrix if submitted
matrix = build_matrix_ui(energy_option, criteria)

if matrix is not None:
    run_ahp(energy_option, criteria, matrix)
else:
    # Optionally show a placeholder
    st.info("👆 Fill the upper triangle (green dropdowns) and click **Update matrix** to see priorities.")

st.markdown("---")
st.caption("AHP implementation matches bpmsg.com calculator. The matrix view makes all comparisons visible at once.")