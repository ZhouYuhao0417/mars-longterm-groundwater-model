# Manuscript-ready methods text

This file documents the legacy exploratory high-run display, not the accepted v2 manuscript comparison. Long-term groundwater outflow was simulated using the original two-dimensional finite-volume diffusive-wave model without replacing the spatial solver. The source at 75.937180°E, 18.136689°N was treated as one prescribed equivalent crater-side boundary at the candidate low-rim outlet after basin filling; the total discharge was applied once and was not replicated across source cells. It does not represent surface transport along the northeast–southwest Nili Fossae trough. Surface-water storage and routing were controlled by the model DEM, including filling of the source depression, spill across its lowest natural saddle, downstream propagation and discharge through the open model boundary.

Three groundwater hydrographs were considered: constant baseflow, exponential recession, and staged pulses. The exponential boundary condition was

\[
Q(t)=Q_b+Q_0\exp(-t/\tau),
\]

where \(Q_b\) is the long-term baseflow, \(Q_0\) is the initial excess discharge and \(\tau\) is the recession timescale. Cumulative raw release was evaluated by analytical integration of \(Q(t)\). The effective surface-water supply was defined as

\[
V_{\mathrm{eff}}(t)=C\int_0^t Q(s)\,ds,
\]

where \(C\) is an effective along-path retention coefficient rather than a precipitation–runoff coefficient. The complementary volume,

\[
V_{\mathrm{loss}}(t)=(1-C)\int_0^t Q(s)\,ds,
\]

was recorded as unretained water.

Multi-year calculations used analytical source-basin prefilling, a dynamic downstream computational window and verified steady-state time skipping while preserving the original 600 s surface-water step during explicit two-dimensional integration. A steady interval was skipped only after two consecutive stable blocks, subject to limits on storage change and new wet-cell arrivals and a minimum boundary-outflow fraction. Shadow integrations were used to validate the skipped state. Water mass was tracked as the sum of unretained volume, source-basin storage, downstream surface storage and open-boundary outflow. Consequently, continued supply beyond the finite storage of the model domain was discharged through the open boundary rather than converted into unlimited areal inundation.

The low scenario prescribed constant Qb = 100 m³ s⁻¹ for 10 yr with C = 0.4. The completed high scenario prescribed Qb = 500 m³ s⁻¹ plus staged pulses with Q0 = 5000 m³ s⁻¹ for 30 yr and C = 1.0. The medium exponential scenario (Qb = 300 m³ s⁻¹, Q0 = 3000 m³ s⁻¹, \(\tau=3\) yr, T = 20 yr and C = 0.7) was not used as a quantitative spatial result because its two-dimensional run was incomplete.
