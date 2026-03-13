from __future__ import annotations

from stomatal_optimiaztion.domains.thorp.equation_registry import (
    EquationMapping,
    build_mapping,
    iter_annotated_callables,
)
from stomatal_optimiaztion.domains.thorp.implements import (
    implemented_equations,
    implements,
    qualname,
)
from stomatal_optimiaztion.domains.thorp.model_card import (
    equation_id_set,
    iter_equation_refs,
    model_card_dir,
    require_equation_ids,
)
from stomatal_optimiaztion.domains.thorp.utils import (
    EquationMapping as NamespaceEquationMapping,
)
from stomatal_optimiaztion.domains.thorp.utils import (
    build_mapping as namespace_build_mapping,
)
from stomatal_optimiaztion.domains.thorp.utils import (
    equation_id_set as namespace_equation_id_set,
)
from stomatal_optimiaztion.domains.thorp.utils import (
    implemented_equations as namespace_implemented_equations,
)
from stomatal_optimiaztion.domains.thorp.utils import implements as namespace_implements
from stomatal_optimiaztion.domains.thorp.utils import (
    iter_annotated_callables as namespace_iter_annotated_callables,
)
from stomatal_optimiaztion.domains.thorp.utils import (
    iter_equation_refs as namespace_iter_equation_refs,
)
from stomatal_optimiaztion.domains.thorp.utils import model_card_dir as namespace_model_card_dir
from stomatal_optimiaztion.domains.thorp.utils import qualname as namespace_qualname
from stomatal_optimiaztion.domains.thorp.utils import (
    require_equation_ids as namespace_require_equation_ids,
)


def test_utils_namespace_reexports_traceability_and_model_card_helpers() -> None:
    assert NamespaceEquationMapping is EquationMapping
    assert namespace_build_mapping is build_mapping
    assert namespace_iter_annotated_callables is iter_annotated_callables
    assert namespace_implemented_equations is implemented_equations
    assert namespace_implements is implements
    assert namespace_qualname is qualname
    assert namespace_equation_id_set is equation_id_set
    assert namespace_iter_equation_refs is iter_equation_refs
    assert namespace_model_card_dir is model_card_dir
    assert namespace_require_equation_ids is require_equation_ids
