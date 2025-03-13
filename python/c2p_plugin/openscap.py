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
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.dom import minidom

import paramiko
import yaml
from c2p.common.logging import getLogger
from c2p.framework.models import Policy, PVPResult, RawResult
from c2p.framework.models.pvp_result import (
    ObservationByCheck,
    PVPResult,
    ResultEnum,
    Subject,
)
from c2p.framework.oscal_utils import add_prop
from c2p.framework.plugin_spec import PluginConfig, PluginSpec
from pydantic.v1 import BaseModel, Field
from trestle.oscal.common import Property
from trestle.tasks.xccdf_result_to_oscal_ar import (
    default_description,
    default_title,
    default_type,
)
from trestle.transforms.implementations.xccdf import XccdfTransformer

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


class PluginOpenScap(PluginSpec):

    def __init__(self, config: Optional[PluginConfigOpenScap] = None) -> None:
        super().__init__()
        self.config = config

    def generate_pvp_result(self, raw_result: RawResult) -> PVPResult:
        xccdf_transformer = XccdfTransformer()
        xccdf_transformer.set_title(default_title)
        xccdf_transformer.set_description(default_description)
        xccdf_transformer.set_type(default_type)
        xccdf_transformer.set_tags({})
        results = xccdf_transformer.transform(raw_result.data)
        raw = ET.fromstring(raw_result.data)
        result = results.__root__[0]
        local_definitions = result.local_definitions
        inventory_item = local_definitions.inventory_items[0]

        # --- Trestle XccdfTransformer failed to extract host_name and target_type. Manually add them.
        target = self.get_prop_value(inventory_item.props, 'target', 'n/a')
        if self.get_prop_value(inventory_item.props, 'host_name', None) == None:
            add_prop(inventory_item.props, 'host_name', target, [])

        ns = {
            'arf': 'http://scap.nist.gov/schema/asset-reporting-format/1.1',
            'core': 'http://scap.nist.gov/schema/reporting-core/1.1',
            'xccdf': 'http://checklists.nist.gov/xccdf/1.2',
        }
        benchmark = raw.find('.//xccdf:benchmark', ns)
        if benchmark is not None and 'href' in benchmark.attrib:
            ssg_target = Path(benchmark.attrib['href']).stem
            inventory_item.props = [x for x in inventory_item.props if x.name != 'target_type']
            add_prop(inventory_item.props, 'target_type', ssg_target, [])
        local_definitions.inventory_items[0] = inventory_item
        # ---

        observations = result.observations
        obcs = []
        for observation in observations:
            props = observation.props
            check_id = self.get_prop_value(props, 'idref')
            subjects = []
            for s in observation.subjects:
                subject = Subject(
                    subject_uuid=s.subject_uuid,
                    title=target,
                    type=s.type.__root__,
                    resource_id=check_id,
                    result=ResultEnum.Error,
                )
                subjects.append(subject)
            obc = ObservationByCheck(
                check_id=check_id,
                methods=observation.methods,
                collected=observation.collected,
            )
            obc.props = props
            obc.subjects = subjects
            obcs.append(obc)
        pvp_result: PVPResult = PVPResult()
        pvp_result.observations_by_check = obcs
        pvp_result.local_definitions = local_definitions
        return pvp_result

    # TODO: Currently, the interface "generate_pvp_policy" in PluginSpec is Any so we can return any value but should be considered better way.
    def generate_pvp_policy(self, policy: Policy) -> str:
        config = self.config
        profile_id = config.profile_id
        tailored_profile_id = f'{profile_id}.tailored'

        with tempfile.NamedTemporaryFile(delete=True) as tmpfile:
            RPCUtils.scp_transfer(config, tmpfile.name, config.remote_path_to_ssg)
            idrefs = RPCUtils.extract_idrefs(tmpfile.name, profile_id)

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
        tailored_profile = RPCUtils.create_tailored_profile(profile_id, tailored_profile_id, rules)

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
                RPCUtils.scp_transfer(config, tmpfile.name, config.remote_path_to_policy, mode='upload')
            exit_status, stdout_text, stderr_text = RPCUtils.execute_ssh_command(config, tailored_profile)
            if exit_status in config.accepted_return_codes:
                logger.info(f'Successfully deployed.')
                RPCUtils.scp_transfer(config, tmpfile.name, config.remote_path_to_policy)
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
                    RPCUtils.scp_transfer(config, tailored_path.absolute().as_posix(), config.remote_path_to_policy)
                    RPCUtils.scp_transfer(config, log_path.absolute().as_posix(), 'oscap.log')
                    RPCUtils.scp_transfer(config, arf_path.absolute().as_posix(), config.remote_path_to_arf)
                    RPCUtils.scp_transfer(config, report_path.absolute().as_posix(), config.remote_path_to_report)
            else:
                logger.error(f'Some error happens: the exit code = {exit_status}')

    def collect(self) -> RawResult:
        config = self.config
        if config.collect:
            p = Path(config.path_to_evidence_dir)
            p.mkdir(parents=True, exist_ok=True)
            arf_path = p / 'arf.xml'
            RPCUtils.scp_transfer(config, arf_path.absolute().as_posix(), config.remote_path_to_arf)
            with arf_path.open('r') as f:
                data = f.read()
            return RawResult(data=data)
        raise NotImplementedError('Should not call if the field is collect == false')

    def get_prop_value(self, props: List[Property], name: str, default=None):
        values = [x.value for x in props if x.name == name]
        return values[0] if values and len(values) > 0 else default


class RPCUtils:

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def invoke_by_cmd(run_command: AgentRunCommand) -> str:
        cmd = run_command.command
        if run_command.args:
            cmd = cmd + run_command.args
        cmd = ' '.join(cmd)
        logger.info(f'Command: {cmd}')

        env = None
        if run_command.env:
            env = [dict([x.name, x.value]) for x in run_command.env]
        stdout, stderr = RPCUtils.run_cmd(env, cmd)
        if stderr:
            raise Exception(stderr)

        return stdout

    @staticmethod
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

    @staticmethod
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
