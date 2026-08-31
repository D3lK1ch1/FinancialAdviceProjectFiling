# Empty on purpose: its presence makes pytest add the project root to
# sys.path, so `tests/*.py` can `import parser`, `scope_gate`, `classifier`,
# `app` without a package/src layout.
