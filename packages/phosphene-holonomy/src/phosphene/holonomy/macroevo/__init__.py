"""macroevo module: replacements for PyRate macroevolutionary diversification."""

from phosphene.holonomy.macroevo.diversity_surface import (
    DiversityTrajectory,
    ProfileLikelihoodSurface,
    compute_profile_likelihood_surface,
    evaluate_ltt_log_likelihood,
)
from phosphene.holonomy.macroevo.joint_likelihood import (
    FossilTaxonRecord,
    compute_joint_taphonomic_likelihood,
)
from phosphene.holonomy.macroevo.master_equation import (
    MasterEquationParams,
    construct_transition_matrix,
    solve_master_equation,
    compute_etienne_branching_loglik,
    profile_etienne_k,
)
from phosphene.holonomy.macroevo.phylogenetic_dr import (
    TipDRAudit,
    audit_tree_diversification_rates,
    parse_simple_newick,
)
from phosphene.holonomy.macroevo.primitives import (
    log_diversity_hazard,
    log_extinction_density,
    log_keiding_conditioning,
    log_poisson_occurrences,
    regularized_inverse_branch_length,
    tip_diversification_rate,
)
from phosphene.holonomy.macroevo.galapagos import (
    ColonistStatus,
    GalapagosClade,
    GalapagosDataset,
    load_galapagos_csv,
    load_galapagos_json,
)
from phosphene.holonomy.macroevo.comparative_metrics import (
    DomainComparisonReport,
    generate_canonical_comparison,
)
from phosphene.holonomy.macroevo.escalation import (
    BranchingState,
    BranchingTrace,
    ScientistEscalationReport,
    rung0_pure_death_logprob,
    rung0_constant_rate_loglik,
    assemble_metzler_generator,
    propagate_uniformized,
    propagate_dense_pade,
    propagate_sparse_krylov,
    step_interval_vertex,
    step_observation_vertex,
    evaluate_with_escalation_ladder,
)

__all__ = [
    "log_diversity_hazard",
    "log_keiding_conditioning",
    "log_poisson_occurrences",
    "log_extinction_density",
    "regularized_inverse_branch_length",
    "tip_diversification_rate",
    "DiversityTrajectory",
    "ProfileLikelihoodSurface",
    "compute_profile_likelihood_surface",
    "evaluate_ltt_log_likelihood",
    "MasterEquationParams",
    "construct_transition_matrix",
    "solve_master_equation",
    "compute_etienne_branching_loglik",
    "profile_etienne_k",
    "TipDRAudit",
    "parse_simple_newick",
    "audit_tree_diversification_rates",
    "FossilTaxonRecord",
    "compute_joint_taphonomic_likelihood",
    "ColonistStatus",
    "GalapagosClade",
    "GalapagosDataset",
    "load_galapagos_csv",
    "load_galapagos_json",
    "DomainComparisonReport",
    "generate_canonical_comparison",
    "BranchingState",
    "BranchingTrace",
    "ScientistEscalationReport",
    "rung0_pure_death_logprob",
    "rung0_constant_rate_loglik",
    "assemble_metzler_generator",
    "propagate_uniformized",
    "propagate_dense_pade",
    "propagate_sparse_krylov",
    "step_interval_vertex",
    "step_observation_vertex",
    "evaluate_with_escalation_ladder",
]
