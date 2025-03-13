# -*- mode:python; coding:utf-8 -*-

# Copyright 2024 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.dom import minidom

import paramiko
import yaml
from c2p.common.logging import getLogger
from c2p.common.utils import get_datetime
from c2p.framework.models import Policy, PVPResult, RawResult
from c2p.framework.models.pvp_result import (
    ObservationByCheck,
    PVPResult,
    ResultEnum,
    Subject,
)
from c2p.framework.oscal_utils import add_prop, uuid
from c2p.framework.plugin_spec import PluginConfig, PluginSpec
from pydantic.v1 import BaseModel, Field
from trestle.oscal import common
from trestle.oscal.assessment_results import LocalDefinitions1
from trestle.oscal.common import (
    AssessmentAssets,
    AssessmentPlatform,
    ImplementedComponent,
    InventoryItem,
    Property,
    SystemComponent,
    SystemComponentOperationalStateValidValues,
)

logger = getLogger(__name__)


class FieldRef(BaseModel):
    field_path: str


class ValueFrom(BaseModel):
    field_ref: FieldRef


class Env(BaseModel):
    name: str
    value: Optional[str] = None
    value_from: Optional[ValueFrom] = None


class AgentRunCommand(BaseModel):
    command: Optional[List[str]] = Field(None, description='The list of command strings to execute (entrypoint).')
    args: Optional[List[str]] = Field(None, description='The list of arguments to pass to the command.')
    env: Optional[List[Env]] = Field(None, description='A list of environment variables to be passed to the container.')


RUN_YAML = """
run:
  env:
    - name: LC_PROFILE_ID
      value_from:
        field_ref:
          field_path: profile_id
    - name: LC_remote_path_to_ssg
      value_from:
        field_ref:
          field_path: remote_path_to_ssg
    - name: LC_REMOTE_TAILORED_PROFILE_PATH
      value_from:
        field_ref:
          field_path: remote_path_to_policy
    - name: LC_REMOTE_ARF_PATH
      value_from:
        field_ref:
          field_path: remote_path_to_arf
    - name: LC_REMOTE_REPORT_PATH
      value_from:
        field_ref:
          field_path: remote_path_to_report
  command: ["oscap"]
  args:
  - xccdf eval
  - --verbose INFO
  - --verbose-log-file oscap.log
  - --profile ${LC_PROFILE_ID}
  - --tailoring-file ${LC_REMOTE_TAILORED_PROFILE_PATH}
  - --results-arf ${LC_REMOTE_ARF_PATH}
  - --report ${LC_REMOTE_REPORT_PATH}
  - --oval-results ${LC_remote_path_to_ssg}
"""

RUN = yaml.safe_load(RUN_YAML)


class NamespacedElement:
    def __init__(self, element: ET.Element, namespace: Optional[Tuple[str, str]] = None) -> None:
        self.element = element
        self.namespace = namespace
        self.text = self.element.text
        self.tag = self.element.tag

    def find(self, xpath) -> 'NamespacedElement':
        xpath = self.__add_namespace_prefix(xpath)
        element = self.element.find(xpath, namespaces=self.__build_namespaces())
        return NamespacedElement(element, self.namespace)

    def findall(self, xpath) -> List['NamespacedElement']:
        xpath = self.__add_namespace_prefix(xpath)
        elements = self.element.findall(xpath, namespaces=self.__build_namespaces())
        return [NamespacedElement(x, self.namespace) for x in elements]

    def findtext(self, xpath, default=None):
        xpath = self.__add_namespace_prefix(xpath)
        return self.element.findtext(xpath, default=default, namespaces=self.__build_namespaces())

    def get(self, key, default=None):
        return self.element.get(key, default=default)

    def __add_namespace_prefix(self, xpath) -> str:
        if self.namespace:
            return re.sub(r"(^|(?<=/))(\w+)", rf"\1{self.namespace[0]}:\2", xpath)
        else:
            return xpath

    def __build_namespaces(self) -> Optional[Dict[str, str]]:
        if self.namespace:
            return {self.namespace[0]: self.namespace[1]}
        else:
            return None


class PluginConfigOpenScap(PluginConfig):
    profile_id: str
    selected_rules: Optional[List[str]] = None
    deploy: Optional[bool] = True
    collect: Optional[bool] = True
    show_progress: Optional[bool] = True
    run: Optional[AgentRunCommand] = AgentRunCommand(**RUN["run"])
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    path_to_ssh_key: Optional[str] = None
    path_to_evidence_dir: Optional[str] = None
    remote_path_to_ssg: str
    remote_path_to_policy: Optional[str] = '/tmp/tailored.xml'
    remote_path_to_arf: Optional[str] = '/tmp/arf.xml'
    remote_path_to_report: Optional[str] = '/tmp/report.html'
    accepted_return_codes: Optional[List[int]] = [0, 2]
    path_to_policy: Optional[str] = None


def scp_transfer(config: PluginConfigOpenScap, local_file, remote_file, mode='download'):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=config.host, port=config.port, username=config.user, key_filename=config.path_to_ssh_key)

    sftp = ssh.open_sftp()
    if mode == 'download':
        sftp.get(remote_file, local_file)
    else:
        sftp.put(local_file, remote_file)
    sftp.close()
    ssh.close()


def execute_ssh_command(config: PluginConfigOpenScap, tailored_profile: str):
    command = config.run.command
    args = config.run.args
    env_variables = {}
    for env in config.run.env:
        name = env.name
        if env.value:
            value = env.value
        elif env.value_from:
            field_path = env.value_from.field_ref.field_path
            value = config.dict().get(field_path)
        else:
            continue
        env_variables[name] = value

    full_command = ' '.join(command + args)
    host = config.host
    port = config.port
    user = config.user
    key_filename = config.path_to_ssh_key
    logger.info(f'Executing on {host}:{port}: {full_command}')

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, port=port, username=user, key_filename=key_filename)

    stdin, stdout, stderr = ssh.exec_command(full_command, environment=env_variables)
    exit_status = stdout.channel.recv_exit_status()

    stdout_text = stdout.read().decode().strip()
    stderr_text = stderr.read().decode().strip()

    logger.debug(stdout_text)
    if stderr_text != '':
        logger.error(stderr_text)

    ssh.close()
    return exit_status, stdout_text, stderr_text


def run_cmd(env: Optional[Dict[str, str]] = None, *argv) -> Tuple[Optional[str], Optional[str]]:
    current_env = os.environ.copy()
    if env:
        current_env.update(env)

    process = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        env=current_env,
        shell=True,
    )

    stdout = ''
    for stdout_line in process.stdout:
        stdout += stdout_line
        logger.info(stdout_line.strip())

    for stderr_line in process.stderr:
        logger.error(stderr_line.strip())

    process.stdout.close()
    process.stderr.close()
    process.wait()

    if process.returncode != 0:
        stderr = process.stderr.read()
        logger.error(f'An error occurred. Return code: {process.returncode}')
        logger.error(stderr)
        return (None, stderr)
    return (stdout, None)


def invoke_by_cmd(run_command: AgentRunCommand) -> str:
    cmd = run_command.command
    if run_command.args:
        cmd = cmd + run_command.args
    cmd = ' '.join(cmd)
    logger.info(f'Command: {cmd}')

    env = None
    if run_command.env:
        env = [dict([x.name, x.value]) for x in run_command.env]
    stdout, stderr = run_cmd(env, cmd)
    if stderr:
        raise Exception(stderr)

    return stdout


def extract_idrefs(xml_file, profile_id):
    """
    Extracts `idref` values from the specified `Profile` in an XML file.
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()

    namespaces = {'xccdf': 'http://checklists.nist.gov/xccdf/1.2'}

    profile = root.find(f".//xccdf:Profile[@id='{profile_id}']", namespaces)
    if profile is None:
        print(f"Profile ID '{profile_id}' not found.")
        return []

    idrefs = [select.attrib['idref'] for select in profile.findall('.//xccdf:select', namespaces)]

    return idrefs


def create_tailored_profile(original_profile_id, profile_id, selected_rules):
    """
    Generates a tailored XCCDF profile XML string.

    :param profile_id: ID of the tailored profile
    :param selected_rules: List of (rule_id, selected) tuples
    """
    ns_xccdf = 'http://checklists.nist.gov/xccdf/1.2'
    ns_xhtml = 'http://www.w3.org/1999/xhtml'
    namespaces = {'xccdf': ns_xccdf}
    ET.register_namespace('xccdf', ns_xccdf)

    tailoring = ET.Element(f'{{{ns_xccdf}}}Tailoring', attrib={'id': 'xccdf_scap-workbench_tailoring_default'})

    version = ET.SubElement(tailoring, f'{{{ns_xccdf}}}version', attrib={'time': '2025-03-11T12:00:00'})
    version.text = '1'

    profile = ET.SubElement(tailoring, f'{{{ns_xccdf}}}Profile', attrib={'id': profile_id, 'extends': original_profile_id})

    title = ET.SubElement(profile, f'{{{ns_xccdf}}}title', attrib={'xmlns:xhtml': ns_xhtml, 'xml:lang': 'en-US', 'override': 'true'})
    title.text = 'Customized Profile'
    description = ET.SubElement(profile, f'{{{ns_xccdf}}}description', attrib={'xmlns:xhtml': ns_xhtml, 'xml:lang': 'en-US', 'override': 'true'})
    description.text = 'This is a customized profile.'

    for rule_id, selected in selected_rules:
        ET.SubElement(profile, f'{{{ns_xccdf}}}select', attrib={'idref': rule_id, 'selected': str(selected).lower()})

    xml_string = minidom.parseString(ET.tostring(tailoring, encoding='utf-8')).toprettyxml(indent='  ')

    return xml_string


class PluginOpenScap(PluginSpec):

    def __init__(self, config: Optional[PluginConfigOpenScap] = None) -> None:
        super().__init__()
        self.config = config

    def generate_pvp_result(self, raw_result: RawResult) -> PVPResult:
        pvp_result: PVPResult = PVPResult()
        observations: List[ObservationByCheck] = []

        xml_string = raw_result.data
        root = ET.fromstring(xml_string)
        if root.tag == 'TestResult':
            root = NamespacedElement(root)
            test_result = root
        else:
            root = NamespacedElement(root, ('xccdf', 'http://checklists.nist.gov/xccdf/1.2'))
            test_result = root.find('.//TestResult')
        benchmark = test_result.find('benchmark')
        target_facts = test_result.find('target-facts')
        rule_results = test_result.findall('rule-result')

        def to_props(object):
            props: List[Property] = []
            [add_prop(props, x[0], x[1], []) for x in object.items()]
            return props

        components = [
            SystemComponent(
                uuid=uuid(),
                type='service',
                title='scap_comp_ssg',
                description='',
                status=common.Status(state=SystemComponentOperationalStateValidValues.operational),
            )
        ]
        # TODO: fix to propery extract
        inventory_item_props = {
            'target': test_result.findtext('target'),
            'target_type': test_result.findtext('target_type', 'ubuntu2404'),
            'host_name': test_result.findtext('target'),
        }
        inventory_items = [
            InventoryItem(
                uuid=uuid(),
                description='',
                props=to_props(inventory_item_props),
                implemented_components=[ImplementedComponent(component_uuid=x.uuid) for x in components],
            )
        ]

        assessment_component_props = {
            'scanner_name': target_facts.find("fact[@name='urn:xccdf:fact:scanner:name']").text,
            'scanner_version': target_facts.find("fact[@name='urn:xccdf:fact:scanner:version']").text,
            'version': test_result.get('version'),
            'weight': rule_results[0].get('weight'),
            'benchmark_id': benchmark.get('id'),
            'benchmark_href': benchmark.get('href'),
            'id': test_result.get('id'),
        }
        assessment_assets = AssessmentAssets(
            components=[
                SystemComponent(
                    uuid=uuid(),
                    type='Validator',
                    title='OpenSCAP',
                    description='',
                    props=to_props(assessment_component_props),
                    status=common.Status(state=SystemComponentOperationalStateValidValues.operational),
                )
            ],
            assessment_platforms=[AssessmentPlatform(uuid=uuid())],
        )

        pvp_result.local_definitions = LocalDefinitions1(components=components, inventory_items=inventory_items, assessment_assets=assessment_assets)

        for rule_result in rule_results:

            xccdf_rule_id = rule_result.get('idref')
            # check_id = xccdf_rule_id.replace('xccdf_org.ssgproject.content_rule_', '')
            check_id = xccdf_rule_id
            observation = ObservationByCheck(
                check_id=check_id,
                methods=['TEST-AUTOMATED'],
                collected=get_datetime(),
            )
            props = {
                'idref': xccdf_rule_id,
                'result': rule_result.findtext('result'),
                'time': rule_result.findtext('time'),
                'severity': rule_result.findtext('severity'),
            }
            observation.props = to_props(props)

            subject_uuid = pvp_result.local_definitions.inventory_items[0].uuid
            subject = Subject(
                subject_uuid=subject_uuid,
                title=self.get_prop_value(pvp_result.local_definitions.inventory_items[0].props, 'target', 'n/a'),
                type='inventory-item',
                resource_id=check_id,
                result=ResultEnum.Error,
            )
            observation.subjects = [subject]
            observations.append(observation)

        pvp_result.observations_by_check = observations

        return pvp_result

    # TODO: Currently, the interface "generate_pvp_policy" in PluginSpec is Any so we can return any value but should be considered better way.
    def generate_pvp_policy(self, policy: Policy) -> str:
        config = self.config
        profile_id = config.profile_id
        tailored_profile_id = f'{profile_id}.tailored'

        with tempfile.NamedTemporaryFile(delete=True) as tmpfile:
            scp_transfer(config, tmpfile.name, config.remote_path_to_ssg)
            idrefs = extract_idrefs(tmpfile.name, profile_id)

        rule_sets = policy.rule_sets
        if config.selected_rules:
            logger.info('Use rule sets described in c2p-config')
            selected_rules = config.selected_rules
        else:
            logger.info(f'Retrieve XCCDF rules from component-definition')
            selected_rules = [x.check_id for x in rule_sets]
        rules = []
        for id in idrefs:
            if id in selected_rules:
                rules.append((id, True))
            else:
                rules.append((id, False))
        tailored_profile = create_tailored_profile(profile_id, tailored_profile_id, rules)

        if config.path_to_policy:
            with open(config.path_to_policy, 'w') as f:
                f.write(tailored_profile)
        else:
            print(tailored_profile)

        return tailored_profile

    def deploy(self, tailored_profile: str):
        config = self.config
        if config.deploy:
            with tempfile.NamedTemporaryFile(delete=True) as tmpfile:
                tmpfile.write(tailored_profile.encode('utf-8'))
                scp_transfer(config, tmpfile.name, config.remote_path_to_policy, mode='upload')
            exit_status, stdout_text, stderr_text = execute_ssh_command(config, tailored_profile)
            if exit_status in config.accepted_return_codes:
                logger.info(f'Successfully deployed.')
                scp_transfer(config, tmpfile.name, config.remote_path_to_policy)
                if config.path_to_evidence_dir:
                    p = Path(config.path_to_evidence_dir)
                    p.mkdir(parents=True, exist_ok=True)
                    out_path = p / 'stdout.txt'
                    err_path = p / 'stderr.txt'
                    log_path = p / 'oscap.log'
                    arf_path = p / 'arf.xml'
                    report_path = p / 'report.html'
                    tailored_path = p / 'tailored_profile.xml'
                    with out_path.open('w') as f:
                        f.write(stdout_text)
                    with err_path.open('w') as f:
                        f.write(stderr_text)
                    scp_transfer(config, tailored_path.absolute().as_posix(), config.remote_path_to_policy)
                    scp_transfer(config, log_path.absolute().as_posix(), 'oscap.log')
                    scp_transfer(config, arf_path.absolute().as_posix(), config.remote_path_to_arf)
                    scp_transfer(config, report_path.absolute().as_posix(), config.remote_path_to_report)
            else:
                logger.error(f'Some error happens: the exit code = {exit_status}')

    def collect(self) -> RawResult:
        config = self.config
        if config.collect:
            p = Path(config.path_to_evidence_dir)
            p.mkdir(parents=True, exist_ok=True)
            arf_path = p / 'arf.xml'
            scp_transfer(config, arf_path.absolute().as_posix(), config.remote_path_to_arf)
            with arf_path.open('r') as f:
                data = f.read()
            return RawResult(data=data)
        raise NotImplementedError('Should not call if the field is collect == false')

    def get_prop_value(self, props: List[Property], name: str, default=None):
        values = [x.value for x in props if x.name == name]
        return values[0] if values and len(values) > 0 else default
