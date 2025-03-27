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
import argparse
import pathlib
from datetime import datetime
from typing import Dict, List

from component_definition_helper import ComponentDefinitionHelper

from markdown_helper import MarkdownHelper

from observations_helper import ObservationsHelper


class TableFormat():
    """Table format."""

    def __init__(self) -> None:
        """Initialize."""
        self.th_color = 'lightblue'
        self.td_color_odd = 'ghostwhite'
        self.td_color_even = 'linen'
        self.state = False

    def get_th(self) -> str:
        """Get th."""
        return self.th_color

    def get_td(self) -> str:
        """Get td."""
        if self.state:
            rval = self.td_color_odd
        else:
            rval = self.td_color_even
        self.state = not self.state
        return rval


class CompliancePosture():
    """Compliance posture."""

    def __init__(self) -> None:
        """Initialize."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--markdown', required=True, help='output file comprising compliance posture markdown')
        parser.add_argument('--observations', required=True, help='input file comprising OSCAL observations')
        parser.add_argument(
            '--software', required=True, help='input file comprising OSCAL software component definition'
        )
        parser.add_argument(
            '--validation', required=True, help='input file comprising OSCAL validation component definition'
        )
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

    def _calculate_posture_by_control(self, inventory_item: Dict, control_tuples: List[str]):
        """Calculate posture by control."""
        summary = {}
        host = inventory_item['host_name']
        for control_tuple in control_tuples:
            control_id = control_tuple[0]
            check_id = control_tuple[2]
            if control_id not in summary.keys():
                summary[control_id] = None
            status = self.observations_helper.get_status(host, check_id)
            if summary[control_id] is None:
                summary[control_id] = status
            elif summary[control_id] == 'pass':
                summary[control_id] = status
        return summary

    def _calculate_posture_by_rule(self, inventory_item: Dict, control_tuples: List[str]):
        """Calculate posture by rule."""
        summary = {}
        host = inventory_item['host_name']
        for control_tuple in control_tuples:
            control_id = control_tuple[0]
            rule_id = control_tuple[1]
            check_id = control_tuple[2]
            if control_id not in summary.keys():
                summary[control_id] = {}
            if rule_id not in summary[control_id].keys():
                summary[control_id][rule_id] = None
            status = self.observations_helper.get_status(host, check_id)
            if summary[control_id][rule_id] is None:
                summary[control_id][rule_id] = status
            elif summary[control_id][rule_id] == 'pass':
                summary[control_id][rule_id] = status
        return summary

    def _display_controls(self, iteration, inventory_item, control_tuples, table_format):
        """Display controls."""
        postures = self._calculate_posture_by_control(inventory_item, control_tuples)
        for control_id in postures.keys():
            status = postures[control_id]
            if status == 'pass':
                image = '<img src="images/Basic_green_dot.png" width="12" height="12">'
            elif status == 'fail':
                image = '<img src="images/Basic_red_dot.png" width="12" height="12">'
            else:
                image = '<img src="images/Basic_gold_dot.png" width="12" height="12">'
            if status == 'unknown':
                status = f'<i title="result not found for given check">{status}</i>'
            td_color = table_format.get_td()
            self.markdown_helper.add_line('<tr>')
            self.markdown_helper.add_line(f'<td align= "left", bgcolor="{td_color}">')
            self.markdown_helper.add_line(f'{control_id}')
            self.markdown_helper.add_line(f'<td align= "left", bgcolor="{td_color}">')
            self.markdown_helper.add_line(f'{image} ')
            self.markdown_helper.add_line(f'{status}')

            if iteration > 1:
                self.markdown_helper.add_line(f'<td align= "left", bgcolor="{td_color}">')
                self.markdown_helper.add_line(f'<td align= "left", bgcolor="{td_color}">')
                self._display_rules(iteration, inventory_item, control_tuples, table_format, control_id)

    def _display_rules(self, iteration, inventory_item, control_tuples, table_format, control_id):
        """Display rules."""
        postures = self._calculate_posture_by_rule(inventory_item, control_tuples)
        for rule_id in postures[control_id].keys():
            status = postures[control_id][rule_id]
            if status == 'pass':
                image = '<img src="images/Basic_green_dot.png" width="12" height="12">'
            elif status == 'fail':
                image = '<img src="images/Basic_red_dot.png" width="12" height="12">'
            else:
                image = '<img src="images/Basic_gold_dot.png" width="12" height="12">'
            if status == 'unknown':
                status = f'<i title="result not found for given check">{status}</i>'
            td_color = table_format.get_td()
            self.markdown_helper.add_line('<tr>')
            self.markdown_helper.add_line(f'<td align= "left", bgcolor="{td_color}">')
            self.markdown_helper.add_line(f'<td align= "left", bgcolor="{td_color}">')
            self.markdown_helper.add_line(f'<td align= "left", bgcolor="{td_color}">')
            self.markdown_helper.add_line(f'{rule_id}')
            self.markdown_helper.add_line(f'<td align= "left", bgcolor="{td_color}">')
            self.markdown_helper.add_line(f'{image} {status}')

            if iteration > 2:
                self.markdown_helper.add_line(f'<td align= "left", bgcolor="{td_color}">')
                self.markdown_helper.add_line(f'<td align= "left", bgcolor="{td_color}">')
                self._display_checks(iteration, inventory_item, control_tuples, table_format, control_id, rule_id)

    def process(self):
        """Process."""
        inventory = self.observations_helper.get_inventory()

        control_tuples = []

        control_id_list = self.software_helper.get_controls()
        for control_id in control_id_list:
            rule__id_list = self.software_helper.get_rules_for_control(control_id)
            for rule_id in rule__id_list:
                check_id_list = self.validation_helper.get_checks_for_rule(rule_id)
                for check_id in check_id_list:
                    control_tuple = (control_id, rule_id, check_id)
                    control_tuples.append(control_tuple)

        self.markdown_helper.add_line('# End-to-End Demo: Compliance Posture')
        self.markdown_helper.add_line('')
        self.markdown_helper.add_line('This repo comprises Compliance Posture for the end-to-end demo.')
        self.markdown_helper.add_line('')
        self.markdown_helper.add_line('The end-to-end demo [overview](https://github.com/oscal-compass/e2e-demo).')
        self.markdown_helper.add_line('<br/>')
        self.markdown_helper.add_line('The end-to-end-demo [compliance posture portion](https://github.com/oscal-compass/e2e-demo#demo-2---cncf-oscal-compass-automated-compliance-posture) instructions.')
        self.markdown_helper.add_line('')

        now = datetime.now()
        datetime_without_ms = now.strftime('%Y-%m-%d %H:%M:%S')
        self.markdown_helper.add_line(f'Last updated: *{datetime_without_ms}*')
        self.markdown_helper.add_line('')

        self.markdown_helper.add_line('<hr>')
        self.markdown_helper.add_line('<hr>')

        type_list = []
        for key in inventory.keys():
            inventory_item = inventory[key]
            tgt_type = inventory_item['target_type']
            if tgt_type not in type_list:
                type_list.append(tgt_type)

        source = self.software_helper.get_controls_source().split('/')[1]
        title = self.software_helper.get_title().replace('for ', 'for: ')
        version = self.software_helper.get_version()

        for tgt_type in type_list:
            self.markdown_helper.add_line('<h2>')
            self.markdown_helper.add_line(f'Controls for: {source}')
            self.markdown_helper.add_line('</h2>')
            self.markdown_helper.add_line('<h2>')
            self.markdown_helper.add_line(f'{title} {version}')
            self.markdown_helper.add_line('</h2>')
            self.markdown_helper.add_line('<h2>')
            self.markdown_helper.add_line(f'type: {tgt_type}')
            self.markdown_helper.add_line('</h2>')

            for key in inventory.keys():
                inventory_item = inventory[key]

                if inventory_item['target_type'] == tgt_type:
                    host = inventory_item['host_name']
                    self.markdown_helper.add_line('<h3>')
                    self.markdown_helper.add_line(f'host: {host}')
                    self.markdown_helper.add_line('</h3>')

                    for iteration in [1, 2]:

                        if iteration == 1:
                            self.markdown_helper.add_line('<details open>')
                            self.markdown_helper.add_line('<summary>')
                            self.markdown_helper.add_line('<b>')
                            self.markdown_helper.add_line('Status by control')
                            self.markdown_helper.add_line('</b>')
                            self.markdown_helper.add_line('</summary>')
                        elif iteration == 2:
                            self.markdown_helper.add_line('<details>')
                            self.markdown_helper.add_line('<summary>')
                            self.markdown_helper.add_line('<b>')
                            self.markdown_helper.add_line('Status by control + rule')
                            self.markdown_helper.add_line('</b>')
                            self.markdown_helper.add_line('</summary>')

                        self.markdown_helper.add_line('<table>')

                        table_format = TableFormat()
                        th_color = table_format.get_th()

                        self.markdown_helper.add_line('<tr>')
                        self.markdown_helper.add_line(f'<th align= "left", bgcolor="{th_color}">')
                        self.markdown_helper.add_line('control name')
                        self.markdown_helper.add_line(f'<th align= "left", bgcolor="{th_color}">')
                        self.markdown_helper.add_line('control status')
                        if iteration > 1:
                            self.markdown_helper.add_line(f'<th align= "left", bgcolor="{th_color}">')
                            self.markdown_helper.add_line('rule name')
                            self.markdown_helper.add_line(f'<th align= "left", bgcolor="{th_color}">')
                            self.markdown_helper.add_line('rule status')
                        self.markdown_helper.add_line('</tr>')

                        self._display_controls(iteration, inventory_item, control_tuples, table_format)

                        self.markdown_helper.add_line('</table>')

                        if iteration in [1, 2, 3]:
                            self.markdown_helper.add_line('</details>')

                        self.markdown_helper.add_line('<br/>')
                        self.markdown_helper.add_line('<br/>')

            self.markdown_helper.add_line('<br/>')

            self.markdown_helper.add_line('<hr>')
            self.markdown_helper.add_line('<hr>')

            self.markdown_helper.add_line('<br/>')
            self.markdown_helper.add_line('<br/>')

        self.markdown_helper.write()


def main():
    """Run."""
    cp = CompliancePosture()
    cp.process()


if __name__ == '__main__':
    main()
