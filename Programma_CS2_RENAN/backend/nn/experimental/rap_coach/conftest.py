# Exclude test_arch.py from pytest collection — it is a validation utility
# used by headless_validator.py Phase 16, not a pytest test.
collect_ignore = ["test_arch.py"]
