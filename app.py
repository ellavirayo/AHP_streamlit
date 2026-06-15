import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="AHP Priority Calculator", layout="centered")
st.title("🌿 AHP Priority Calculator – Energy Suitability Mapping")
st.markdown("""
**Pairwise comparisons for Solar, Wind, and Biomass suitability**  
Use Saaty's 1–9 scale:  
1 = Equal importance, 3 = Moderate, 5 = Strong, 7 = Very strong, 9 = Extreme  
(2,4,6,8 are intermediate values).  
**Goal:** Consistency Ratio (CR) < 0.10  
""")

# ---- AHP core functions ----
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

# ---- BPMSG-style pairwise comparison UI ----
def build_comparisons_ui(energy_type, criteria):
    st.subheader(f"⚡ {energy_type} – Pairwise Comparisons")
    st.caption("For each pair, indicate which criterion is more important and by how much (1–9).")
    
    n = len(criteria)
    comparisons = {}  # store (i, j) -> strength (float)
    
    # Generate all pairs (i < j)
    pairs = []
    for i in range(n):
        for j in range(i+1, n):
            pairs.append((i, j, criteria[i], criteria[j]))
    
    # Create a table-like layout using columns
    for idx, (i, j, crit_i, crit_j) in enumerate(pairs):
        st.markdown("---")
        cols = st.columns([2, 1, 1, 2])
        
        with cols[0]:
            st.write(f"**{crit_i}**  vs  **{crit_j}**")
        
        # Choice: A, Equal, or B
        choice_key = f"{energy_type}_choice_{i}_{j}"
        choice = st.radio(
            "Which is more important?",
            options=[crit_i, "Equal", crit_j],
            index=1,  # default Equal
            key=choice_key,
            horizontal=True,
            label_visibility="collapsed"
        )
        
        strength = 1.0  # default equal
        
        if choice == crit_i:
            # A is more important
            strength = st.selectbox(
                f"How much more important is {crit_i} than {crit_j}?",
                options=[2,3,4,5,6,7,8,9],
                index=0,
                key=f"{energy_type}_str_{i}_{j}",
                label_visibility="collapsed"
            )
            comparisons[f"{i}_{j}"] = float(strength)   # a_ij = strength
        elif choice == crit_j:
            # B is more important
            strength = st.selectbox(
                f"How much more important is {crit_j} than {crit_i}?",
                options=[2,3,4,5,6,7,8,9],
                index=0,
                key=f"{energy_type}_str_{i}_{j}",
                label_visibility="collapsed"
            )
            comparisons[f"{i}_{j}"] = 1.0 / float(strength)  # a_ij = 1/strength
        else:  # Equal
            comparisons[f"{i}_{j}"] = 1.0
        
        # Show current numerical value (optional)
        if strength == 1:
            st.caption("→ Equal importance (1)")
        elif choice == crit_i:
            st.caption(f"→ {crit_i} is {strength} times more important than {crit_j}")
        else:
            st.caption(f"→ {crit_j} is {strength} times more important than {crit_i}")
    
    return comparisons

def build_matrix_from_comparisons(criteria, comparisons):
    n = len(criteria)
    matrix = np.eye(n)
    for i in range(n):
        for j in range(i+1, n):
            val = comparisons.get(f"{i}_{j}", 1.0)
            matrix[i, j] = val
            matrix[j, i] = 1.0 / val
    return matrix

def run_ahp(energy_type, criteria, comparisons):
    matrix = build_matrix_from_comparisons(criteria, comparisons)
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
        st.warning(f"⚠️ Consistency Ratio = {CR:.3f} (≥ 0.10) → Please revise some comparisons.")
    
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

st.sidebar.markdown(f"**Criteria for {energy_option} suitability:**")
for c in criteria:
    st.sidebar.markdown(f"- {c}")

# Session state to remember comparisons per energy type
if "all_comparisons" not in st.session_state:
    st.session_state.all_comparisons = {}

# Build the UI for the selected energy type
comparisons = build_comparisons_ui(energy_option, criteria)

if st.button("🚀 Calculate Priorities", type="primary"):
    st.session_state.all_comparisons[energy_option] = comparisons
    run_ahp(energy_option, criteria, comparisons)

# Optional: show previous results if they exist
if energy_option in st.session_state.all_comparisons:
    if st.button("🔄 Recalculate (after changes)"):
        run_ahp(energy_option, criteria, st.session_state.all_comparisons[energy_option])

st.markdown("---")
st.caption("Interface replicates bpmsg.com AHP calculator. Input is intuitive: choose which criterion dominates, then how much (2–9).")