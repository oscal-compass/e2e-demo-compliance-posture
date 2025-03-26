# Copyright (c) 2025 The OSCAL Compass Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""OSCAL transformation tasks."""
import pathlib
from typing import List

from trestle.oscal.component import ComponentDefinition


class ComponentDefinitionHelper():
    """Component definition helper."""

    def __init__(self, ipath: pathlib.Path) -> None:
        """Initialize."""
        self.cd = ComponentDefinition.oscal_read(ipath)

    def get_title(self) -> str:
        """Get title."""
        return self.cd.metadata.title

    def get_version(self) -> str:
        """Get version."""
        return self.cd.metadata.version

    def get_controls_source(self) -> List[str]:
        """Get controls source."""
        component = self.cd.components[0]
        control_implementation = component.control_implementations[0]
        return control_implementation.source
        
    def get_controls(self) -> List[str]:
        """Get controls."""
        rval = []
        component = self.cd.components[0]
        control_implementation = component.control_implementations[0]
        implemented_requirements = control_implementation.implemented_requirements
        for implemented_requirement in implemented_requirements:
            control_id = implemented_requirement.control_id
            if control_id in rval:
                text = f'duplicate control id {control_id}'
                raise RuntimeError(text)
            rval.append(control_id)
        return sorted(rval, key=lambda item: (item.split('-')[0], float(item.split('-')[1])))

    def get_rules_for_control(self, control_id: str) -> List[str]:
        """Get rules for control."""
        rval = []
        component = self.cd.components[0]
        control_implementation = component.control_implementations[0]
        implemented_requirements = control_implementation.implemented_requirements
        for implemented_requirement in implemented_requirements:
            if control_id == implemented_requirement.control_id:
                for prop in implemented_requirement.props:
                    if prop.name == 'Rule_Id':
                        rule = prop.value
                        if rule not in rval:
                            rval.append(rule)
        return sorted(rval)

    def get_checks_for_rule(self, rule_id: str) -> List[str]:
        """Get checks for rule."""
        rval = []
        component = self.cd.components[0]
        props = component.props
        for prop in props:
            if prop.name == 'Rule_Id':
                if prop.value != rule_id:
                    continue
                rule_set = prop.remarks
                check_id = self._get_check_for_rule_set(rule_set)
                if not check_id:
                    continue
                if check_id in rval:
                    continue
                rval.append(check_id)
        return sorted(rval)

    def _get_check_for_rule_set(
        self,
        rule_set: str,
    ) -> List[str]:
        """Get check for rule-set."""
        rval = None
        component = self.cd.components[0]
        props = component.props
        for prop in props:
            if prop.name == 'Check_Id':
                if rule_set == prop.remarks:
                    rval = prop.value
                    break
        return rval
