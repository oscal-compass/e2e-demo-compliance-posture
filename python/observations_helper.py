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
from typing import Dict, List


class ObservationsHelper():
    """Observations helper."""
    
    def __init__(self, ipath: pathlib.Path) -> None:
        """Initialize."""
        with open(ipath, 'r') as f:
            self.jdata = json.load(f)
    
    def _get_prop_value(self, props: List[Dict], name: str) -> str:
        """Get result."""
        rval = None
        for prop in props:
            if prop['name'] == name:
                rval = prop['value']
                break
        return rval
     
    def get_inventory(self) -> Dict:
        """Get inventory."""
        inventory = {}
        results = self.jdata['results']
        for result in results:
            local_definitions = result['local-definitions']
            inventory_items = local_definitions['inventory-items']
            for inventory_item in inventory_items:
                uuid_ = inventory_item['uuid']
                inventory[uuid_] = {}
                props = inventory_item['props']
                name = 'target'
                inventory[uuid_][name] = self._get_prop_value(props, name)
                name = 'target_type'
                inventory[uuid_][name] = self._get_prop_value(props, name)
                name = 'host_name'
                inventory[uuid_][name] = self._get_prop_value(props, name)
        return inventory
    
    def _get_subject_uuid(self, host: str) -> str:
        """Get subject uuid."""
        uuid_ = None
        inventory = self.get_inventory()
        for key in inventory.keys():
            name = 'host_name'
            if inventory[key][name] == host:
                uuid_ = key
                break
        return uuid_
            
    def get_status(self, host: str, check: str) -> str:
        """Get status."""
        subject_uuid = self._get_subject_uuid(host)
        status = 'unknown'
        results = self.jdata['results']
        for result in results:
            if status != 'unknown':
                break
            observations = result['observations']
            for observation in observations:
                subjects = observation['subjects']
                if len(subjects) != 1:
                    raise RuntimeError(f'Expected 1 subject: {subjects}')
                subject = subjects[0]
                if subject['subject-uuid'] != subject_uuid:
                    continue
                props = observation['props']
                idref = self._get_prop_value(props,'idref')
                idref = idref.replace('xccdf_org.ssgproject.content_rule_', '')
                if idref == check:
                    status = idref = self._get_prop_value(props,'result')
                    break
        return status
        
        
        
        


 