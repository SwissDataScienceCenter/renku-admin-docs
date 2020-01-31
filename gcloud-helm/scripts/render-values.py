#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2017-2019 - Swiss Data Science Center (SDSC)
# A partnership between École Polytechnique Fédérale de Lausanne (EPFL) and
# Eidgenössische Technische Hochschule Zürich (ETHZ).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Render file for given template and values."""

# TODO: Look into streamlining it with dev-values.py

import argparse
import os
import subprocess
import base64
from ruamel.yaml import YAML

yaml = YAML()

# Avoid mangling of quotes.
yaml.preserve_quotes = True

def main():
    """Run dev deploy."""
    argparser = argparse.ArgumentParser(description=__doc__)

    argparser.add_argument(
        '--template',
        help='Template file.')
    argparser.add_argument(
        '--values',
        help='Values file.')
    argparser.add_argument(
        '--key',
        help='Render only values under specific key.'
    )
    argparser.add_argument(
        '--output',
        help='Output filename.'
    )
    args = argparser.parse_args()

    if args.template is None and args.values is None:
        raise RuntimeError(
            'You must specify a template and values to render.'
        )

    with open(args.template) as tmpl:
        template_ = tmpl.read()
    with open(args.values) as values:
        values_ = yaml.load(values.read())
        if args.key:
            values_ = values_[args.key]
        renku_values = template_.format(**values_)
    with open(args.output, 'w') as output:
        output.write(renku_values)


if __name__ == '__main__':
    main()
