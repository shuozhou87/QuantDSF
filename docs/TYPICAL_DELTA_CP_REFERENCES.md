# Typical Heat Capacity Changes (ΔCp) in Biomolecular Binding

This note compiles literature examples and references for heat capacity changes (ΔCp) observed in different classes of molecular recognition. The goal is to anchor reasonable prior ranges for ΔCp when deciding whether to include a ΔCp term in Van't Hoff analysis.

## Quick Orientation

- For many protein–ligand interactions, reported ΔCp values are modest and negative, often on the order of a few hundred cal/mol/K (≈ −0.1 to −0.6 kcal/mol/K).
- Protein–DNA complexes typically show larger negative ΔCp (reflecting hydrophobic and ion‑release contributions), commonly approaching ≈ −0.3 to −1.2 kcal/mol/K.
- Large protein–protein interfaces can yield even larger negative ΔCp, frequently ≈ −0.8 to −2.0 kcal/mol/K, with upper‑end cases near −2.5 kcal/mol/K for very hydrophobic interfaces.

These broad ranges are consistent with classical surface area models relating ΔCp to changes in exposed nonpolar and polar surface area upon complex formation.

## Representative References and Examples

### Protein–Small Molecule (Inhibitor) Binding

- Baranauskienė L., Matulis D. Intrinsic thermodynamics of ethoxzolamide inhibitor binding to human carbonic anhydrase XIII. BMC Biophysics (2012) 5:12. doi: 10.1186/2046-1682-5-12
  - Open‑access ITC and thermal‑shift dissection of intrinsic binding thermodynamics (ΔG°, ΔH°, ΔS°, ΔCp) for sulfonamide inhibitors to CA XIII. Reports modest, negative intrinsic ΔCp values consistent with hydrophobic pocket burial.
  - URL: https://link.springer.com/article/10.1186/2046-1682-5-12

- Matulis D. and co‑workers. Thermodynamics–structure correlations of sulfonamide inhibitor binding to carbonic anhydrase. In: Biocalorimetry 2 (2004), Chapter 6. doi: 10.1002/0470011122.ch6
  - Survey of CA isoforms/inhibitors; discusses typical magnitudes and structure–thermodynamics correlations for ΔH°, ΔS°, and ΔCp.

### Protein–DNA Recognition

- Spolar R.S., Record M.T. Jr. Coupling of local folding to site‑specific binding of proteins to DNA. Science (1994) 263:777–784. doi: 10.1126/science.8303294
  - Classic review highlighting large negative ΔCp (ΔC°assoc) as a hallmark of high‑specificity protein–DNA recognition; attributes magnitude to hydrophobic effect and coupled folding/ordering events.
  - PubMed: https://pubmed.ncbi.nlm.nih.gov/8303294/

- Ha J.H., Spolar R.S., Record M.T. Jr. Role of the hydrophobic effect in stability of site‑specific protein–DNA complexes. (Companion works referenced by the Science review.)
  - These analyses support sizable negative ΔCp values for sequence‑specific complexes.

### Protein–Protein Association

- Nagi A.D., Anderson K.S., Regan L. A calorimetric study of the thermal stability of barstar and its interaction with barnase. Biochemistry (1995) 34:5224–5233. doi: 10.1021/bi00015a036
  - ITC and DSC analysis of the barnase–barstar system; protein–protein association exhibits a significantly negative ΔCp consistent with burial of a large hydrophobic interface.
  - PubMed search: https://pubmed.ncbi.nlm.nih.gov/?term=%22A+calorimetric+study+of+the+thermal+stability+of+barstar%22

### Foundational Theory / SASA Correlations

- Livingstone J.R., Spolar R.S., Record M.T. Jr. Contribution to the thermodynamics of protein folding from the reduction in water‑accessible nonpolar surface area. Biochemistry (1991) 30:4237–4244. doi: 10.1021/bi00231a019
  - Demonstrates proportionality between ΔCp and reduction in water‑accessible non‑polar surface area; the same framework underpins ΔCp expectations for binding.
  - PubMed: https://pubmed.ncbi.nlm.nih.gov/2021617/

- Privalov P.L., Gill S.J. Stability of Protein Structure and Hydrophobic Interaction. Advances in Protein Chemistry (1988) 39:191–234. doi: 10.1016/S0065-3233(08)60377-0
  - Foundational treatment of ΔCp in folding and assembly; connects ΔCp to hydration and surface burial.

## Practical Takeaways for QuantDSF

- Use the ranges above as priors/guards for ΔCp fitting. Values much larger in magnitude than ≈ −1 kcal/mol/K for small‑molecule binding are uncommon and should trigger caution flags and model‑selection checks (e.g., AIC/BIC vs. the linear Van’t Hoff model).
- For narrow temperature windows (≤10–15 °C), ΔCp is often weakly identifiable; prefer ΔCp=0 unless the ΔCp model offers strong information‑criterion support and passes plausibility checks.

