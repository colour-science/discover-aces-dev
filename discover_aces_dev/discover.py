# -*- coding: utf-8 -*-
import itertools
import logging
import os
import re
from collections import defaultdict

from discover_aces_dev.common import paths_common_ancestor, vivified_to_dict

__all__ = [
    'REFERENCE_IMPLEMENTATION_TRANSFORMS_ROOT', 'discover_aces_ctl',
    'ACES_CTL_TRANSFORM_ROOT_CATEGORIES', 'classify_aces_ctl_transforms'
]

ACES_CTL_TRANSFORM_ROOT_CATEGORIES = {
    'csc': 'csc',
    'idt': 'input_transform',
    'lib': 'lib',
    'lmt': 'lmt',
    'odt': 'output_transform',
    'outputTransforms': 'output_transform',
    'rrt': 'rrt',
    'utilities': 'utility'
}

EXCLUDED_CLASSIFIERS = ['vendorSupplied']

REFERENCE_IMPLEMENTATION_TRANSFORMS_ROOT = os.environ.get(
    'OPENCOLORIO_CONFIG_ACES__REFERENCE_IMPLEMENTATION_TRANSFORMS_ROOT',
    os.path.join(
        os.path.dirname(__file__), '../', 'reference_implementation',
        'transforms'))


class CTLTransform:
    def __init__(self, name, path):
        self._name = name
        self._path = path

        self._code = None
        self._id = None
        self._user_name = None
        self._description = ''

        self._parse()

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    @property
    def code(self):
        return self._code

    @property
    def id(self):
        return self._id

    @property
    def user_name(self):
        return self._user_name

    @property
    def description(self):
        return self._description

    def __str__(self):
        return f'{self.__class__.__name__}({self._name})'

    def __repr__(self):
        return (f"{self.__class__.__name__}("
                f"'{self._name}', '{os.path.basename(self._path)}')")

    def _parse(self):
        with open(self._path) as ctl_file:
            self._code = ctl_file.read()

            lines = filter(None,
                           (line.strip() for line in self._code.split('\n')))

            in_header = True
            for line in lines:
                search = re.search('<ACEStransformID>(.*)</ACEStransformID>',
                                   line)
                if search:
                    self._id = search.group(1)
                    continue

                search = re.search('<ACESuserName>(.*)</ACESuserName>', line)
                if search:
                    self._user_name = search.group(1)
                    continue

                if line.startswith('//'):
                    self._description += line[2:].strip()
                    self._description += '\n'
                else:
                    in_header = False

                if not in_header:
                    break


class CTLTransformPair:
    def __init__(self, name, forward_transform, inverse_transform):
        self._name = name
        self._forward_transform = forward_transform
        self._inverse_transform = inverse_transform

    @property
    def name(self):
        return self._name

    @property
    def forward_transform(self):
        return self._forward_transform

    @property
    def inverse_transform(self):
        return self._inverse_transform

    def __str__(self):
        return f'{self.__class__.__name__}({self._name})'

    def __repr__(self):
        return (f"{self.__class__.__name__}("
                f"CTLTransform('{self._forward_transform.name}', "
                f"'{os.path.basename(self._forward_transform.path)}'), "
                f"CTLTransform('{self._inverse_transform.name}', "
                f"'{os.path.basename(self._inverse_transform.path)}'))")


def find_transform_pairs(ctl_transforms):
    ctl_transform_pairs = defaultdict(dict)
    for ctl_transform in ctl_transforms:
        is_forward = True
        basename = os.path.splitext(os.path.basename(ctl_transform))[0]
        if basename.startswith('Inv'):
            basename = basename.replace('Inv', '')
            is_forward = False
        if '_to_ACES' in basename:
            basename = basename.replace('_to_ACES', '')
            is_forward = False

        basename = basename.replace('ACES_to_', '')

        if is_forward:
            ctl_transform_pairs[basename]['forward_transform'] = ctl_transform
        else:
            ctl_transform_pairs[basename]['inverse_transform'] = ctl_transform

    return ctl_transform_pairs


def discover_aces_ctl(root_directory=REFERENCE_IMPLEMENTATION_TRANSFORMS_ROOT):
    root_directory = os.path.normpath(os.path.expandvars(root_directory))

    ctl_transforms = defaultdict(list)
    for directory, _sub_directories, filenames in os.walk(root_directory):
        if not filenames:
            continue

        for filename in filenames:
            if not filename.lower().endswith('ctl'):
                continue

            ctl_transform = os.path.join(directory, filename)
            logging.info(f'"{ctl_transform}" CTL transform was found!')

            ctl_transforms[directory].append(ctl_transform)

    return ctl_transforms


def classify_aces_ctl_transforms(unclassified_ctl_transforms):
    classified_ctl_transforms = defaultdict(lambda: defaultdict(dict))

    separator = os.sep
    root_directory = paths_common_ancestor(
        *itertools.chain.from_iterable(unclassified_ctl_transforms.values()))
    for directory, ctl_transforms in unclassified_ctl_transforms.items():
        sub_directory = directory.replace(f'{root_directory}{separator}', '')
        category, *classifiers = [
            ACES_CTL_TRANSFORM_ROOT_CATEGORIES.get(classifier, classifier)
            for classifier in sub_directory.split(separator)
            if classifier not in EXCLUDED_CLASSIFIERS
        ]

        if not classifiers:
            classifiers = 'base'
        else:
            classifiers = '/'.join(classifiers)

        for basename, pairs in find_transform_pairs(ctl_transforms).items():
            if len(pairs) == 1:
                ctl_transform = CTLTransform(basename, list(pairs.values())[0])

                logging.info(
                    f'Classifying "{ctl_transform}" under "{classifiers}".')

                classified_ctl_transforms[category][classifiers][basename] = (
                    ctl_transform)

            elif len(pairs) == 2:
                forward_ctl_transform = CTLTransform(
                    basename, pairs['forward_transform'])
                inverse_ctl_transform = CTLTransform(
                    basename, pairs['inverse_transform'])

                ctl_transform = CTLTransformPair(
                    basename, forward_ctl_transform, inverse_ctl_transform)

                logging.info(
                    f'Classifying "{ctl_transform}" under "{classifiers}".')

                classified_ctl_transforms[category][classifiers][basename] = (
                    ctl_transform)

    return vivified_to_dict(classified_ctl_transforms)


if __name__ == '__main__':
    from pprint import pprint
    from rich.logging import RichHandler

    logging.basicConfig(
        level=logging.INFO, datefmt="[%X] ", handlers=[RichHandler()])

    classified_ctl_transforms = classify_aces_ctl_transforms(
        discover_aces_ctl())

    pprint(classified_ctl_transforms)
    for category, classifiers in classified_ctl_transforms.items():
        for classifier, ctl_transforms in classifiers.items():
            for name, ctl_transform in ctl_transforms.items():
                print(f'[ {name} ]')
                if isinstance(ctl_transform, CTLTransform):
                    print(f'\t{ctl_transform.id}')
                elif isinstance(ctl_transform, CTLTransformPair):
                    print(f'\t{ctl_transform.forward_transform.id}')
                    print(f'\t{ctl_transform.inverse_transform.id}')
