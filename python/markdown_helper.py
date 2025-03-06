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
import pathlib


class MarkdownHelper():
    """Markdown helper."""

    def __init__(self, ipath: pathlib.Path) -> None:
        """Initialize."""
        self.ipath = ipath
        self.lines = []

    def add_line(self, line) -> None:
        """Add line."""
        self.lines.append(line)

    def write(self) -> None:
        """Write."""
        with open(self.ipath, 'w') as file:
            for line in self.lines:
                file.write(f'{line}\n')
