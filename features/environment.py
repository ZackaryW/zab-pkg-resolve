from __future__ import annotations

from zab_pkg_resolve.resolver import ScenarioWorkspace


def before_scenario(context, scenario):
    context.workspace = ScenarioWorkspace()


def after_scenario(context, scenario):
    context.workspace.close()