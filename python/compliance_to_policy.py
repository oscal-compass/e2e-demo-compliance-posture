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

import yaml
from c2p.framework.c2p import C2P
from c2p.framework.models.c2p_config import C2PConfig, ComplianceOscal
from c2p_plugin.openscap import PluginConfigOpenScap, PluginOpenScap
from pathlib import Path
import json

log_format = '[%(asctime)s %(levelname)s %(name)s] %(message)s'

logger = logging.getLogger('compliance_to_policy')


def init():
    logging.basicConfig(format=log_format, level=logging.ERROR)
    _logger = logging.getLogger('c2p_plugin.openscap')
    _logger.setLevel(logging.INFO)
    global logger
    logger.setLevel(logging.INFO)


init()

parser = argparse.ArgumentParser()
parser.add_argument(
    '--component_definition',
    type=str,
    default=f'component-definitions/oscap/component-definition.json',
    help=f'Path to component-definition.json (default: component-definitions/oscap/component-definition.json',
    required=False,
)
parser.add_argument(
    '--config',
    type=str,
    default=f'python/c2p_plugin/config.yaml',
    required=False,
)
parser.add_argument('-o', '--out', type=str, help='Path to OSCAL Assessment Results (Default: stdout)', required=False)
args = parser.parse_args()

# Setup c2p_config
c2p_config = C2PConfig()
c2p_config.compliance = ComplianceOscal()
c2p_config.compliance.component_definition = args.component_definition
c2p_config.pvp_name = 'oscap'
c2p_config.result_title = 'Ubuntu OpenScap Assessment Results'
c2p_config.result_description = 'Ubuntu OpenScap Assessment Results'

# Construct C2P
c2p = C2P(c2p_config)

# Setup c2p plugin
with open(args.config, 'r') as f:
    data = f.read()
    data = yaml.safe_load(data)
    config = PluginConfigOpenScap.parse_obj(data)

config.path_to_policy = args.out
logger.info('Transform Compliance (OSCAL) to Native Policy')
c2p_plugin = PluginOpenScap(config)
pvp_native_policy = c2p_plugin.generate_pvp_policy(c2p.get_policy())
logger.info('Deploy Native Policy to Ubuntu')
c2p_plugin.deploy(pvp_native_policy)
logger.info('Collect Native Results from Ubuntu')
pvp_raw_result = c2p_plugin.collect()
logger.info('Transform Native Result to Compliance Result (OSCAL)')
pvp_result = c2p_plugin.generate_pvp_result(pvp_raw_result)
c2p.set_pvp_result(pvp_result)
oscal_assessment_results = c2p.result_to_oscal()

output = oscal_assessment_results.oscal_serialize_json()
# TODO: workaround to extract only 'results'
output = json.loads(output)
output = {'results': output['assessment-results']['results']}
output = json.dumps(output, indent=2)

evidence_dir = Path(config.path_to_evidence_dir)
evidence_files = '\n'.join(f'  - {f.name}' for f in evidence_dir.iterdir() if f.is_file())
message = f"""
**Summary**
----------------------------------------
**Evidence Directory:** 
{config.path_to_evidence_dir}/
{evidence_files}

**OSCAL Assessment Results:**
  {args.out}
----------------------------------------
"""
if args.out:
    with open(args.out, 'w') as f:
        f.write(output)
else:
    print(output)
logger.info(message)
