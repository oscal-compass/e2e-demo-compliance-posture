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
import os

def main():
    """Run."""
    pause_file = 'pause.txt'
    parser = argparse.ArgumentParser()
    parser.add_argument('--enable',  action='store_true', help='enable pausing')
    parser.add_argument('--disable',  action='store_true', help='disable pausing')
    args = parser.parse_args()
    if args.enable:
        with open(pause_file, 'w') as file:
            file.write('pause enabled')
    elif args.disable:
        os.remove(pause_file)
    else:
        if os.path.exists(pause_file):
            input('Press "Enter" key to continue...')


if __name__ == '__main__':
    main()
