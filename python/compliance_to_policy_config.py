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
"""Compliance to policy config."""

import argparse
import pathlib


class VagrantHelper():
    """Vagrant helper."""

    def __init__(self, fp: str) -> None:
        """Initialize."""
        self.fp = fp

    def read(self):
        """Read."""
        ipath = pathlib.Path(self.fp)
        with open(ipath, 'r') as f:
            self.lines = f.readlines()

    def get(self, name: str, default: str) -> str:
        """Get."""
        rval = default
        for line in self.lines:
            parts = line.strip().split(' ')
            if len(parts) == 2:
                if parts[0] == name:
                    rval = parts[1]
                    break
        return rval


class C2PHelper():
    """C2P helper."""

    def __init__(self, fp: str) -> None:
        """Initialize."""
        self.fp = fp
        self.lines = []

    def add_line(self, line: str) -> None:
        """Add line."""
        self.lines.append(line)

    def write(self):
        """Write."""
        ipath = pathlib.Path(self.fp)
        with open(ipath, 'w') as f:
            for line in self.lines:
                f.write(f'{line}\n')


class ComplianceToPolicyConfig():
    """Compliance to policy config."""

    def __init__(self) -> None:
        """Initialize."""

    def process(self):
        """Process."""
        default_host = '127.0.0.1'
        default_port = '2222'
        default_profile_id = 'xccdf_org.ssgproject.content_profile_cis_level2_workstation'
        default_user = 'vagrant'
        default_path_to_ssh_key = '.vagrant/machines/default/virtualbox/private_key'
        default_path_to_evidence_dir = './evidences'
        default_remote_path_to_ssg = '/usr/share/xml/scap/ssg/content/ssg-ubuntu2404-ds.xml'
        #
        parser = argparse.ArgumentParser()
        parser.add_argument('--input', required=True, help='the vagrant ssh-config data')
        parser.add_argument('--output', required=True, help='the C2P config yaml file')
        parser.add_argument(
            '--profile_id',
            required=False,
            default=default_profile_id,
            help=f'the oscap profile id, default={default_profile_id}'
        )
        parser.add_argument(
            '--path_to_evidence_dir',
            required=False,
            default=default_path_to_evidence_dir,
            help=f'evidence dir, default={default_path_to_evidence_dir}'
        )
        parser.add_argument(
            '--remote_path_to_ssg',
            required=False,
            default=default_remote_path_to_ssg,
            help=f'path to evindence dir, default={default_remote_path_to_ssg}'
        )
        args = parser.parse_args()
        vh = VagrantHelper(args.input)
        vh.read()
        ch = C2PHelper(args.output)
        #
        name = 'profile_id'
        value = args.profile_id
        ch.add_line(f'{name}: {value}')
        #
        name = 'host'
        value = vh.get('HostName', default_host)
        ch.add_line(f'{name}: {value}')
        #
        name = 'port'
        value = vh.get('Port', default_port)
        ch.add_line(f'{name}: {value}')
        #
        name = 'user'
        value = vh.get('User', default_user)
        ch.add_line(f'{name}: {value}')
        #
        name = 'path_to_ssh_key'
        value = vh.get('IdentityFile', default_path_to_ssh_key)
        value = value.split('.vagrant')[1]
        value = f'.vagrant{value}'
        ch.add_line(f'{name}: {value}')
        #
        name = 'path_to_evidence_dir'
        value = args.path_to_evidence_dir
        ch.add_line(f'{name}: {value}')
        #
        name = 'remote_path_to_ssg'
        value = args.remote_path_to_ssg
        ch.add_line(f'{name}: {value}')
        #
        ch.write()


def main():
    """Run."""
    tgt = ComplianceToPolicyConfig()
    tgt.process()


if __name__ == '__main__':
    main()
