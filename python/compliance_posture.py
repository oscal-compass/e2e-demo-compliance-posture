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

import argparse
import logging
import pathlib
from datetime import datetime

from component_definition_helper import ComponentDefinitionHelper
from markdown_helper import MarkdownHelper
from observations_helper import ObservationsHelper

logger = logging.getLogger()
logging.basicConfig(format="%(levelname)s: %(message)s")


class CompliancePosture():
    """Compliance posture."""
    
    def __init__(self) -> None:
        """Initialize."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--markdown', required=True, help='output file comprising compliance posture markdown')
        parser.add_argument('--observations', required=True, help='input file comprising OSCAL observations')
        parser.add_argument('--software', required=True, help='input file comprising OSCAL software component definition')
        parser.add_argument('--validation', required=True, help='input file comprising OSCAL validation component definition')
        self.args = parser.parse_args()
        self._init_markdown_helper()
        self._init_observations_helper()
        self._init_software_helper()
        self._init_validation_helper()
        
    def _init_markdown_helper(self):
        """Initialize markdown helper."""
        ipath = pathlib.Path(self.args.markdown)
        self.markdown_helper = MarkdownHelper(ipath)
            
    def _init_observations_helper(self):
        """Initialize observations helper."""
        ipath = pathlib.Path(self.args.observations)
        self.observations_helper = ObservationsHelper(ipath)
                
    def _init_software_helper(self):
        """Initialize software helper."""
        ipath = pathlib.Path(self.args.software)
        self.software_helper = ComponentDefinitionHelper(ipath)
                        
    def _init_validation_helper(self):
        """Initialize validation helper."""
        ipath = pathlib.Path(self.args.validation)
        self.validation_helper = ComponentDefinitionHelper(ipath)
        
    def process(self):
        """Process."""
        inventory = self.observations_helper.get_inventory()
        
        rules_sw = self.software_helper.get_rules()
        rules_val = self.validation_helper.get_rules()
        
        control_map = {}
        
        for rule in rules_sw:
            if rule not in rules_val:
                logger.warning(f'software rule missing from validation -> {rule}')
            else:
                sw_rule_set = self.software_helper.get_rule_set(rule)
                control = self.software_helper.get_control(sw_rule_set)
                val_rule_set = self.validation_helper.get_rule_set(rule)
                check = self.validation_helper.get_check(val_rule_set)
                logger.info(f'control: {control} rule: {rule} check: {check}')
                if control not in control_map.keys():
                    control_map[control] = []
                rule_check_pair = [rule, check]
                control_map[control].append(rule_check_pair)
        
        self.markdown_helper.add_line('# End-to-End Demo: Compliance Posture')
        self.markdown_helper.add_line('End-to-End Demo: Policy as Code RHEL9 results')
        self.markdown_helper.add_line('')
        self.markdown_helper.add_line('This repo comprises Compliance Posture for the end-to-end demo.')
        self.markdown_helper.add_line('')
        self.markdown_helper.add_line('The [demo overview](https://github.com/oscal-compass/e2e-demo).')
        
        now = datetime.now()
        datetime_without_ms = now.strftime('%Y-%m-%d %H:%M:%S')
        self.markdown_helper.add_line(f'Last updated: *{datetime_without_ms}*')
        self.markdown_helper.add_line('')

        self.markdown_helper.add_line('<hr>')
        self.markdown_helper.add_line('<hr>')

        type_list = []
        for key in inventory.keys():
            inventory_item = inventory[key]
            type = inventory_item['target_type']
            if type not in type_list:
                type_list.append(type)
        
        title = self.software_helper.get_title()
        version = self.software_helper.get_version()
        
        for type in type_list:
            self.markdown_helper.add_line('<h2>')
            self.markdown_helper.add_line(f'{title} {version}')
            self.markdown_helper.add_line('</h2>')
            self.markdown_helper.add_line('<h2>')
            self.markdown_helper.add_line(f'type: {type}')
            self.markdown_helper.add_line('</h2>')
            for key in inventory.keys():
                inventory_item = inventory[key]
                if inventory_item['target_type'] == type:
                    host = inventory_item['host_name']
                    self.markdown_helper.add_line('<h3>')
                    self.markdown_helper.add_line(f'host: {host}')
                    self.markdown_helper.add_line('</h3>')
                    
                    self.markdown_helper.add_line('<table>')
                    
                    th_color = 'lightblue'
                    
                    self.markdown_helper.add_line('<tr>')
                    self.markdown_helper.add_line(f'<th align= "left", bgcolor="{th_color}">')
                    self.markdown_helper.add_line('control')
                    self.markdown_helper.add_line(f'<th align= "left", bgcolor="{th_color}">')
                    self.markdown_helper.add_line('rule')
                    self.markdown_helper.add_line(f'<th align= "left", bgcolor="{th_color}">')
                    self.markdown_helper.add_line('check')
                    self.markdown_helper.add_line(f'<th align= "left", bgcolor="{th_color}">')
                    self.markdown_helper.add_line('status')
                    
                    td_color_odd = 'ghostwhite'
                    td_color_even = 'linen'
                    
                    td_flag = False
                    
                    for control in control_map.keys():
                        
                        rule_check_pair_list = control_map[control]
                        for rule_check_pair in rule_check_pair_list:
                            
                            if td_flag:
                                td_flag = False
                                td_color = td_color_even
                            else:
                                td_flag = True
                                td_color = td_color_odd
                            
                            rule = rule_check_pair[0]
                            check = rule_check_pair[1]
                        
                            status = self.observations_helper.get_status(host, check)
                            if status == 'pass':
                                image = '<img src="images/Basic_green_dot.png" width="12" height="12">'
                            elif status == 'fail':
                                image = '<img src="images/Basic_red_dot.png" width="12" height="12">'
                            else:
                                image = '<img src="images/Basic_gold_dot.png" width="12" height="12">'
                            
                            self.markdown_helper.add_line('<tr>')
                            self.markdown_helper.add_line(f'<td align= "left", bgcolor="{td_color}">')
                            self.markdown_helper.add_line(f'{control}')
                            self.markdown_helper.add_line(f'<td align= "left", bgcolor="{td_color}">')
                            self.markdown_helper.add_line(f'{rule}')
                            self.markdown_helper.add_line(f'<td align= "left", bgcolor="{td_color}">')
                            self.markdown_helper.add_line(f'{check}')
                            self.markdown_helper.add_line(f'<td align= "left", bgcolor="{td_color}">')
                            self.markdown_helper.add_line(f'{image} {status}')
                    
                    self.markdown_helper.add_line('</table>')
            
            self.markdown_helper.add_line('<br/>')
            
            self.markdown_helper.add_line('<hr>')
            self.markdown_helper.add_line('<hr>')
            
            self.markdown_helper.add_line('<br/>')
            self.markdown_helper.add_line('<br/>')
            self.markdown_helper.add_line('<br/>')
        
        self.markdown_helper.write()
        
         
def main():
    """Run."""
    cp = CompliancePosture()
    cp.process()

if __name__ == '__main__':
    main()