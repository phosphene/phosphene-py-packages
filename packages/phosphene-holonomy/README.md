# holonomy

A generic mathematical engine for path-dependent dynamical systems, non-abelian hysteresis, and geometric state preservation.

`holonomy` provides pure, immutable, and differentiable abstractions for modeling systems where state changes depend on the path taken through control space. In continuum mechanics, geometry, and non-linear dynamics, traversing a closed parameter loop $\gamma(t)$ leaves a permanent residual displacement in state:

$$\Delta \mathcal{M} = \oint_\gamma \partial_t \mathcal{M} \, dt \neq 0$$

Elevating this governing physical invariant into software guarantees **trajectory preservation by definition**: every state is treated as an immutable value, and time evolution records an explicit, verifiable lineage rather than performing in-place buffer mutations.

---

## 1. Pure Mathematical Core (`holonomy.core` / root)

The top-level package operates on timeless mathematical abstractions:

- **`Manifold` & `State`**: Immutable spatial configurations, coordinate discretizations, or abstract metric spaces ($\mathcal{M}_0$). Array buffers are strictly read-only (`flags.writeable = False`).
- **`ControlLoop` & `ForcingField`**: Parameterized trajectories in external control space traversing closed or transient forcing curves ($\gamma(t): [0, T] \to \mathcal{C}$ such that $\mathcal{F}(0) = \mathcal{F}(T)$).
- **`TransferClosure` & `compute_flux_divergence`**: Pure constitutive mappings $(\mathcal{M}, \mathcal{F}) \mapsto \mathbf{J}$ producing generalized flux or transfer vector fields.
- **`CapacityEdge`**: Explicit boundary representation tracking available capacity headroom ($K - k$) and classifying discrete operational regimes (`interior_radiation`, `boundary_grazing`, `saturated_ceiling`) without hard-coded branching logic.
- **`next_state`**: Generalized continuity/conservation integration: $\partial_t \mathcal{M} = -\mathcal{D}(\mathbf{J})$.
- **`EvolutionTrace` & `HolonomyDefect`**: Ordered, append-only lineage of immutable states along a control loop, enabling zero-loss historical rollback, mass/energy conservation auditing, and exact path residue calculation ($\Delta \mathcal{M} = \mathcal{M}(T) - \mathcal{M}(0)$).

---

## 2. Numerical Genealogy and the Background Realization

To prevent complex computational methods from acting as opaque black boxes, `holonomy` maps its operations along a rigorous 4-tier numerical genealogy linking simple scalar closed forms to high-dimensional continuous flows:

```
Rung 0: Scalar Closed Forms      (math.exp, math.log, zero arrays, Nee-May-Harvey closed form)
   │
Rung 1: Discretized State Spaces (Vectorized probability distributions P across unobserved states)
   │
Rung 2: Coupled Linear Semigroups (Metzler generator M_k, scaling-and-squaring Padé, Krylov subspace,
   │                              calibrated against Jensen's strictly non-negative Uniformization oracle)
Rung 3: Capacity-Bounded Models  (Continuous interval flows + discrete cladogenetic observation vertices)
```

### The Kneebone Background Realization

Following G. T. Kneebone’s principle of the Euclidean background realization in abstract projective geometry, lower-order rungs serve as an exact, invariant touch-point—**not as a gating, forcing, or restrictive mechanism**, but as a transparent ground for evaluation. 

Researchers remain completely free to deploy complex dynamical models, high-dimensional priors, or carrying-capacity manifolds. The engine pairs higher-order evaluations with a **Background Realization Report**:
- Computes the scalar closed-form baseline $\ln L_{\text{rung0}}$ and the capacity-bounded evaluation $\ln L_{\text{rung3}}$.
- Reports the exact empirical difference $\Delta \ln L = \ln L_{\text{rung3}} - \ln L_{\text{rung0}}$ alongside the bottleneck capacity regime.
- Provides a clean, objective reference point that reveals where higher-order terms actively diverge from simpler baselines without prescribing or gatekeeping scientific modeling choices.

---

## 3. Domain Specialization Dialects

The generalized mathematical kernel is specialized into domain dialects that provide natural language entry points native to each scientific literature:

### A. Fluvial & Coastal Geomorphology (`holonomy.geomorph`)
Models erodible bed evolution under cyclic hydrodynamic forcing (tides, floods, storm waves):
- `Bed`: Bathymetric boundary geometry and active-layer stratigraphy.
- `Flow`: Hydrodynamic forcing fields (velocity, boundary shear stress).
- `flux.meyer_peter_muller` / `flux.flux_divergence`: Constitutive sediment transport closures.
- `exner.next_bed` / `exner.bed_evolution_trace` / `exner.holonomy_defect`: Exner sediment mass conservation $\partial_t \eta = -\frac{1}{1-p} \nabla \cdot \mathbf{q}_s$ and cyclic topographic displacement.

### B. Skeletal Morphometrics & Morphogenesis (`holonomy.morphometrics`)
Models biological form generation, allometric scaling, and permanent anatomical divergence:
- `Configuration`: Landmark configurations and centroid sizes in Kendall shape space.
- `allometric_growth_closure`: Differential growth tensors driven by ontogenetic stress gradients.
- `remodeling.ontogenetic_trace` / `remodeling.morphological_defect`: Structural continuity and permanent skeletal divergence across cyclic loading.

### C. Deterministic Macroevolutionary Suite (`holonomy.macroevo`)
Replaces heuristic, destructive random-walk MCMC tools (such as PyRate) with pure, data-agnostic deterministic likelihoods, continuous-time Markov models, and calibration oracles (zero disk I/O, zero study-specific prose):
- `primitives`: Self-sufficient Rung 0/1 units of reasoning for Jetz (2012) Tip DR (`equal_splits`, `tip_dr`, `tip_dr_diagnostic`), Poisson (`log_poisson_count_pmf`, `log_poisson_process_density`), Keiding (`preservation_effort`, `keiding_observability_prob`, `log_keiding_conditioning`), Lineage Duration (`log_lineage_duration_density`, `log_turnover_survival`), and Standing Diversity.
- `escalation`: Multi-tier numerical genealogy (Rung 0–3) linking scalar closed forms to Metzler semigroups (`propagate_dense_pade`, `propagate_sparse_krylov`, `propagate_uniformized`), paired with the Kneebone `BackgroundRealizationReport` (`background_realization`).
- `master_equation`: Unified Etienne (2012) continuous-time Markov master equation solver (`branching_loglik`, `carrying_capacity_profile`) built directly on `CapacityEdge`, `BranchingTrace`, and pluggable propagators.
- `diversity_surface`: Exact analytical profile likelihood surfaces (`profile_likelihood_surface`, `continuous_profile_likelihood_surface`) and formal $\chi^2$ LRT / AIC diagnostics.
- `joint_likelihood`: Protocol-based taphonomically conditioned joint likelihood (`LineageObservation`, `joint_taphonomic_loglik` → `JointLikelihoodBreakdown`).
- `phylogenetic_dr`: Pure string-to-value Newick parser (`newick_tip_paths`, strictly tip-to-root) and singularity diagnostics (`tree_tip_dr_diagnostics`).

---

## 4. Quickstart & Lossless Skimming

### Pure Core Engine:
```python
import numpy as np
from phosphene.holonomy import (
    Manifold,
    State,
    ControlLoop,
    linear_gradient_transfer,
    evolution_trace,
)

# 1. Establish immutable state manifold
x = np.linspace(0, 1000, 21)
y = np.linspace(0, 500, 11)
baseline = np.zeros((11, 21))
manifold = Manifold.from_grid(x, y, baseline)
initial_state = State.create(manifold, baseline)

# 2. Evaluate evolution trace across cyclic control loop
loop = ControlLoop.sinusoidal(period=3600.0, num_steps=12, shape=manifold.shape)
closure = linear_gradient_transfer(diffusion_coeff=0.05)
trace = evolution_trace(initial_state, loop, closure)

# 3. Audit closed-loop holonomy defect
defect = trace.defect()
print(f"Holonomy Defect L2 Norm: {defect.norm:.4e}")
```

### Background Realization Audit:
```python
from phosphene.holonomy.macroevo.escalation import evaluate_with_background_realization

# Evaluate an empirical branching schedule against the Rung 0 touch-point
branching_times = [2.0, 1.5, 0.8]
report = evaluate_with_background_realization(
    branching_times,
    lam0=0.8,
    mu0=0.1,
    K=15.0,
)

print(f"Rung 0 Baseline lnL: {report.rung0_loglik:.4f}")
print(f"Rung 3 Capacity lnL: {report.rung3_loglik:.4f}")
print(f"Likelihood Delta:    {report.delta_loglik:.4f}")
print(f"Capacity Regime:     {report.bottleneck_regime}")
```

---

## 5. Documentation & Specifications

- [`docs/NUMERICAL_GENEALOGY_AND_CALIBRATION.md`](docs/NUMERICAL_GENEALOGY_AND_CALIBRATION.md): Multi-tier numerical genealogy, Kneebone background realization, and vertex-seam continuity.
- [`docs/PYTEST_AND_HYPOTHESIS_PATTERNS.md`](docs/PYTEST_AND_HYPOTHESIS_PATTERNS.md): Codified patterns and anti-patterns for scientific algebraic dynamics, strict IEEE-754 hygiene, and variational `target()` defect hunting.
- [`docs/GENERALIZED_MATHEMATICAL_ARCHITECTURE.md`](docs/GENERALIZED_MATHEMATICAL_ARCHITECTURE.md): Formal architectural specification, semantic triad (Frege), and Three-Phase Process (Pull $\to$ Transform $\to$ Push).
- [`docs/LITERATE_SPECIFICATION.md`](docs/LITERATE_SPECIFICATION.md): Literate code walkthrough and mathematical mapping across the core kernel and domain dialects.

---

## 6. Development & Testing

All mathematical operators, vertex seams, and calibration rungs are audited via property-based invariant testing with Hypothesis:

```bash
uv sync
uv run pytest --hypothesis-show-statistics
```
