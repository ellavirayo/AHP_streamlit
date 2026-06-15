import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="AHP Priority Calculator", layout="centered")
st.title("🌿 AHP Priority Calculator – Energy Suitability Mapping")
st.markdown("""
**Pairwise comparison for Solar, Wind, and Biomass suitability.**  
Follow Saaty's 1–9 scale: *1 = equal importance, 9 = extreme importance*.  
Reciprocal values are automatically set.  
**Goal:** CR < 10% for consistent judgments.  
Powered by AHP (Saaty 1997).  
""")

# ---- AHP core functions ----
def get_ri(n):
    """Random Index for AHP consistency check (Saaty)."""
    ri_dict = {1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12,
               6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
    return ri_dict.get(n, 1.51)

def ahp_priority(matrix):
    """Compute priority vector (normalized column average method)."""
    matrix = np.array(matrix, dtype=float)
    col_sums = matrix.sum(axis=0)
    norm_mat = matrix / col_sums
    priority = norm_mat.mean(axis=1)
    return priority

def check_consistency(matrix, priority):
    """Compute lambda_max, CI, CR."""
    n = len(matrix)
    weighted_sum = np.dot(matrix, priority)
    lambda_max = np.mean(weighted_sum / priority)
    CI = (lambda_max - n) / (n - 1)
    RI = get_ri(n)
    CR = CI / RI if RI != 0 else 0.0
    return lambda_max, CI, CR

def display_pairwise_matrix(criteria, comparison_dict):
    """Display matrix and results."""
    n = len(criteria)
    indices = [(i, j) for i in range(n) for j in range(i+1, n)]
    matrix = np.eye(n)
    for idx, (i, j) in enumerate(indices):
        val = comparison_dict.get(f"{i}_{j}", 1.0)
        matrix[i, j] = val
        matrix[j, i] = 1.0 / val if val != 0 else np.inf
    return matrix

# ---- Energy-specific interfaces ----
def build_comparison_ui(energy_type, criteria_list):
    """Create pairwise comparison table for a given energy type."""
    st.subheader(f"⚡ {energy_type} – Pairwise comparisons")
    st.caption("Judge: How much more important is the **row criterion** compared to the **column criterion**?")
    
    n = len(criteria_list)
    comparisons = {}
    cols = st.columns(1)
    with cols[0]:
        for i in range(n):
            for j in range(i+1, n):
                key = f"{energy_type}_{i}_{j}"
                value = st.number_input(
                    f"**{criteria_list[i]}** vs **{criteria_list[j]}**",
                    min_value=1.0/9.0, max_value=9.0, value=1.0, step=1.0, key=key,
                    format="%.4f"
                )
                comparisons[f"{i}_{j}"] = value
    return comparisons

def run_ahp(energy_type, criteria, comparisons):
    """Run full AHP and display results."""
    matrix = display_pairwise_matrix(criteria, comparisons)
    priorities = ahp_priority(matrix)
    lambda_max, CI, CR = check_consistency(matrix, priorities)
    
    # Results DataFrame
    df = pd.DataFrame({
        "Criterion": criteria,
        "Weight (%)": priorities * 100,
        "Rank": priorities.argsort()[::-1] + 1
    }).sort_values("Weight (%)", ascending=False)
    
    st.subheader("📊 AHP Results")
    st.dataframe(df.style.format({"Weight (%)": "{:.2f}"}))
    st.write(f"**λ_max** = {lambda_max:.4f} **CI** = {CI:.4f} **CR** = {CR:.4f}")
    
    if CR < 0.1:
        st.success(f"✅ Consistency Ratio = {CR:.3f} (< 0.10) → Judgments are consistent.")
    else:
        st.warning(f"⚠️ Consistency Ratio = {CR:.3f} (≥ 0.10) → Please revise your comparisons to improve consistency.")
    
    return df, CR

# ---- Main app logic ----
energy_option = st.sidebar.radio("Select energy type", ["Solar", "Wind", "Biomass"])

criteria_sets = {
    "Solar": [
        "Active faults", "Protected areas", "Indigenous areas", "Urban/built-up areas",
        "Global horizontal irradiation", "Slope", "Distance from transmission lines",
        "Distance from roads"
    ],
    "Wind": [
        "Active faults", "Protected areas", "Indigenous areas", "Urban/built-up areas",
        "Global horizontal irradiation", "Slope", "Distance from transmission lines",
        "Distance from roads"
    ],
    "Biomass": [
        "Active faults", "Protected areas", "Indigenous areas", "Urban/built-up areas",
        "Crop residue, per province", "Slope", "Distance from transmission lines",
        "Distance from roads"
    ]
}

criteria = criteria_sets[energy_option]
st.sidebar.markdown(f"**Criteria for {energy_option} suitability:**")
for c in criteria:
    st.sidebar.markdown(f"- {c}")

# Session state to store comparisons across reruns
if "comparisons" not in st.session_state:
    st.session_state.comparisons = {}
if "run_pressed" not in st.session_state:
    st.session_state.run_pressed = False

comparisons = build_comparison_ui(energy_option, criteria)

if st.button("🚀 Calculate priorities", type="primary", key="calculate"):
    st.session_state.comparisons[energy_option] = comparisons
    st.session_state.run_pressed = True
    run_ahp(energy_option, criteria, comparisons)

if st.session_state.run_pressed and energy_option in st.session_state.comparisons:
    stored = st.session_state.comparisons[energy_option]
    if st.button("🔄 Re‑calculate (after changing values)", key="recalc"):
        run_ahp(energy_option, criteria, stored)

st.markdown("---")
st.caption("AHP implementation matches original calculator (eigenvector method, normalized column averaging).")