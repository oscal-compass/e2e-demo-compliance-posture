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
    
    def get_rules(self) -> List[str]:
        """Get rules."""       
        cdef = self.jdata['component-definition']
        components = cdef['components']
        component = components[0]
        props = component['props']
        rule_id_list = []
        for prop in props:
            if prop['name'] == 'Rule_Id':
                rule_id_list.append(prop['value'])
        return rule_id_list
    
    def get_rule_set(self, rule_id: str) -> str:
        """Get rule-set for rule."""
        rule_set = None
        cdef = self.jdata['component-definition']
        components = cdef['components']
        component = components[0]
        props = component['props']
        rule_id_list = []
        for prop in props:
            if prop['name'] == 'Rule_Id':
                if prop['value'] == rule_id:
                    rule_set = prop['remarks']
                    break
        return rule_set
        
    def get_control(self, rule_set: str) -> str:
        """Get control for rule-set."""
        control = None
        cdef = self.jdata['component-definition']
        components = cdef['components']
        component = components[0]
        props = component['props']
        for prop in props:
            if prop['remarks'] == rule_set:
                if prop['name'] == 'Cis_Safeguards_1_V8':
                    control = prop['value']
                    break
        return control
    
    def get_check(self, rule_set: str) -> str:
        """Get check for rule-set."""
        check = None
        cdef = self.jdata['component-definition']
        components = cdef['components']
        component = components[0]
        props = component['props']
        for prop in props:
            if prop['remarks'] == rule_set:
                if prop['name'] == 'Check_Id':
                    check = prop['value']
                    break
        return check
    
    
    