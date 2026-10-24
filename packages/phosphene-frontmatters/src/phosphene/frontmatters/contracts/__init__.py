"""Pipeline contracts for the frontmatter synchronization system.

A pipeline contract is a Pydantic model that defines what a specific
pipeline requires from the documents it processes. Contracts are data —
defining a new pipeline means writing a new model here, not modifying
the frontmatter engine.

Available contracts:
    - WoodchipperContract: P1 research pipeline (title, date, source_quality).

Usage::

    from phosphene.frontmatters.contracts.woodchipper import WoodchipperContract
    from phosphene.frontmatters import read

    result = read(path, model_cls=WoodchipperContract)
    # Raises ValidationError if id/title/date/source_quality are missing or invalid.
"""
