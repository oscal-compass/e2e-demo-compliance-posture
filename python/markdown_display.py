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
"""Markdown display."""
import subprocess
import webbrowser
from sys import platform

import markdown

md_file = 'README.md'

if platform == 'darwin':
    html_file = md_file.replace('.md', '.html')
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    html_content = markdown.markdown(md_content)
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    subprocess.run(['open', html_file])
else:
    webbrowser.open('README.md', new=0)
