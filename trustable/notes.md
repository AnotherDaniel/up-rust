# TSF usage notes

## Composing and importing upstream artifacts

Currently (3rd Feb 2026), the importing of TSF artifacts comes with a few caveats:

- item and link review status is not part of the import process -> all items and links have to be re-reviewed manually to get a workable graph
- as every import step requires a Namespace assignment, multi-level composition of artifacts results in very cumbersome statement IDs: eg `UPSTREAM.ECLIPSE.ECLIPSE-PROCESSES` linking to `UPSTREAM.TSF.TA-METHODOLOGIES`. This is the result of
  - a core TSF-namespaced artifact-set of trustable tenets
  - an additional ECLIPSE-namespaced set of statements, which refine some core TSF statements
  - a combination TSF-ECLIPSE artifact done upstream, to get the TSF parent-links set up on artifact level (and not have to do this in the consuming project)
  - (the same pattern is applied to a RUST-namespaced Rust statement library)
  - this combined TSF-ECLIPSE-RUST artifact is imported into up-rust, and again needs a separate namespace (`UPSTREAM`)
- TSF (community) artifacts need a real upstream repository, where they are maintained and can be downloaded from. Until then, we have to store what we need locally in this repository (`trustable/import`)
