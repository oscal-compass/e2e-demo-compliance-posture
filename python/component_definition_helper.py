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
import json
import pathlib
from typing import List


class ComponentDefinitionHelper():
    """Component definition helper."""

    def __init__(self, ipath: pathlib.Path) -> None:
        """Initialize."""
        with open(ipath, 'r') as f:
            self.jdata = json.load(f)

    def get_title(self) -> str:
        """Get title."""
        cdef = self.jdata['component-definition']
        metadata = cdef['metadata']
        title = metadata['title']
        return title

    def get_version(self) -> str:
        """Get version."""
        cdef = self.jdata['component-definition']
        metadata = cdef['metadata']
        version = metadata['version']
        return version

    def get_controls(self) -> List[str]:
        """Get controls."""
        rval = []
        cdef = self.jdata['component-definition']
        components = cdef['components']
        component = components[0]
        control_implementations = component['control-implementations']
        control_implementation = control_implementations[0]
        implemented_requirements = control_implementation['implemented-requirements']
        for implemented_requirement in implemented_requirements:
            control_id = implemented_requirement['control-id']
            if control_id in rval:
                text = f'duplicate control id {control_id}'
                raise RuntimeError(text)
            rval.append(control_id)

        return sorted(rval, key=lambda item: (item.split('-')[0], float(item.split('-')[1])))

    def get_rules_for_control(self, control_id: str) -> List[str]:
        """Get rules for control."""
        rval = []
        cdef = self.jdata['component-definition']
        components = cdef['components']
        component = components[0]
        control_implementations = component['control-implementations']
        control_implementation = control_implementations[0]
        implemented_requirements = control_implementation['implemented-requirements']
        for implemented_requirement in implemented_requirements:
            if control_id == implemented_requirement['control-id']:
                for prop in implemented_requirement['props']:
                    if prop['name'] == 'Rule_Id':
                        rule = prop['value']
                        if rule not in rval:
                            rval.append(rule)
        return sorted(rval)

    def get_checks_for_rule(self, rule_id: str) -> List[str]:
        """Get checks for rule."""
        rval = []
        cdef = self.jdata['component-definition']
        components = cdef['components']
        component = components[0]
        props = component['props']
        for prop in props:
            if prop['name'] == 'Rule_Id':
                if prop['value'] != rule_id:
                    continue
                rule_set = prop['remarks']
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
        cdef = self.jdata['component-definition']
        components = cdef['components']
        component = components[0]
        props = component['props']
        for prop in props:
            if prop['name'] == 'Check_Id':
                if rule_set == prop['remarks']:
                    rval = prop['value']
                    break
        return rval
