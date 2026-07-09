"""Core entity packages (club, comedian, show, ...).

This __init__ makes laughtrack.core.entities a regular (non-namespace)
package: import-linter rejects implicit namespace packages as contract
source modules, and grimp skips their submodules when building the import
graph (TASK-3695).
"""
