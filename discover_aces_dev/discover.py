# -*- coding: utf-8 -*-
import itertools
import logging
import os
import re
from collections import defaultdict

from discover_aces_dev.common import paths_common_ancestor, vivified_to_dict

__all__ = [
    'ACES_URN', 'ACES_TYPES', 'ACES_CTL_TRANSFORM_ROOT_CATEGORIES',
    'EXCLUDED_CLASSIFIERS', 'REFERENCE_IMPLEMENTATION_TRANSFORMS_ROOT',
    'CTLTransform', 'CTLTransformPair', 'find_transform_pairs',
    'discover_aces_ctl', 'classify_aces_ctl_transforms'
]

ACES_ID_SEPARATOR = '.'
ACES_URN_SEPARATOR = ':'
ACES_URN = 'urn:ampas:aces:transformId:v1.5'
ACES_NAMESPACE = 'Academy'
ACES_TYPES = [
    'IDT', 'LMT', 'ODT', 'RRT', 'RRTODT', 'InvRRT', 'InvODT', 'InvRRTODT',
    'ACESlib', 'ACEScsc', 'ACESutil'
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


def patch_invalid_id(id_):
    invalid_id = id_
    if not id_.startswith(ACES_URN):
        logging.warning(f'{invalid_id} is missing "ACES" URN!')

        id_ = f'{ACES_URN}:{id_}'

    if 'Academy.P3D65_108nits_7.2nits_ST2084' in id_:
        logging.warning(f'{invalid_id} has an invalid separator in "7.2nits"!')

        id_ = id_.replace('7.2', '7')
    elif 'ACEScsc' in id_:
        if not 'ACEScsc.Academy' in id_:
            logging.warning(f'{invalid_id} is missing "Academy" namespace!')

            id_ = id_.replace('ACEScsc', 'ACEScsc.Academy')

        if id_.endswith('a1.v1'):
            logging.warning(f'{invalid_id} version scheme is invalid!')

            id_ = id_.replace('a1.v1', 'a1.1.0')

    return id_


class CTLTransform:
    def __init__(self, path):
        self._path = path

        self._code = None
        self._id = None
        self._urn = None
        self._type = None
        self._namespace = None
        self._name = None
        self._major_version_number = None
        self._minor_version_number = None
        self._patch_version_number = None
        self._user_name = None
        self._description = ''
        self._source = None
        self._target = None

        self._parse()

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
    def urn(self):
        return self._urn

    @property
    def type(self):
        return self._type

    @property
    def namespace(self):
        return self._namespace

    @property
    def name(self):
        return self._name

    @property
    def major_version_number(self):
        return self._major_version_number

    @property
    def minor_version_number(self):
        return self._minor_version_number

    @property
    def patch_version_number(self):
        return self._patch_version_number

    @property
    def user_name(self):
        return self._user_name

    @property
    def description(self):
        return self._description

    @property
    def source(self):
        return self._source

    @property
    def target(self):
        return self._target

    def __str__(self):
        return f'{self.__class__.__name__}({self._name})'

    def __repr__(self):
        return (f"{self.__class__.__name__}("
                f"'{self._name}', '{os.path.basename(self._path)}')")

    def _parse_id(self):
        if self._id is None:
            return

        id_ = patch_invalid_id(self._id)

        self._urn, components = id_.rsplit(ACES_URN_SEPARATOR, 1)
        components = components.split(ACES_ID_SEPARATOR)
        self._type, components = components[0], components[1:]

        assert self._urn == ACES_URN, (
            f'{self._path} URN {self._urn} is invalid!')

        assert len(components) in (3, 4, 5), (
            f'{self._path} transform has an invalid id!')

        if len(components) == 3:
            (self._major_version_number, self._minor_version_number,
             self._patch_version_number) = components
        elif len(components) == 4:
            if self._type in ('ACESlib', 'ACESutil'):
                (self._name, self._major_version_number,
                 self._minor_version_number,
                 self._patch_version_number) = components
            elif self._type == 'IDT':
                (self._name, self._namespace, self._major_version_number,
                 self._minor_version_number) = components
        else:
            (self._namespace, self._name, self._major_version_number,
             self._minor_version_number,
             self._patch_version_number) = components

        assert self._type in ACES_TYPES, (
            f'{self._path} type {self._type} is invalid!')

        if self._name is not None:
            if '_to_' in self._name:
                self._source, self._target = self._name.split('_to_')
            elif self._type in ('IDT', 'LMT'):
                self._source, self._target = self._name, 'ACES2065-1'
            elif self._type == 'ODT':
                self._source, self._target = 'OCES', self._name
            elif self._type == 'InvODT':
                self._source, self._target = self._name, 'OCES'
            elif self._type == 'RRTODT':
                self._source, self._target = 'ACES2065-1', self._name
            elif self._type == 'InvRRTODT':
                self._source, self._target = self._name, 'ACES2065-1'
        else:
            if self._type == 'RRT':
                self._source, self._target = 'ACES2065-1', 'OCES'
            elif self._type == 'InvRRT':
                self._source, self._target = 'OCES', 'ACES2065-1'

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
                    self._parse_id()
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
    def __init__(self, forward_transform, inverse_transform):
        self._forward_transform = forward_transform
        self._inverse_transform = inverse_transform

    @property
    def forward_transform(self):
        return self._forward_transform

    @property
    def inverse_transform(self):
        return self._inverse_transform

    def __str__(self):
        return f'{self.__class__.__name__}({self._forward_transform.name}, {self._inverse_transform.name})'

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
                ctl_transform = CTLTransform(list(pairs.values())[0])

                logging.info(
                    f'Classifying "{ctl_transform}" under "{classifiers}".')

                classified_ctl_transforms[category][classifiers][basename] = (
                    ctl_transform)

            elif len(pairs) == 2:
                forward_ctl_transform = CTLTransform(
                    pairs['forward_transform'])
                inverse_ctl_transform = CTLTransform(
                    pairs['inverse_transform'])

                ctl_transform = CTLTransformPair(forward_ctl_transform,
                                                 inverse_ctl_transform)

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
                    print(f'\t"{ctl_transform.source}" to '
                          f'"{ctl_transform.target}"')
                elif isinstance(ctl_transform, CTLTransformPair):
                    print(f'\t"{ctl_transform.forward_transform.source}" to '
                          f'"{ctl_transform.forward_transform.target}"')
                    print(f'\t"{ctl_transform.inverse_transform.source}" to '
                          f'"{ctl_transform.inverse_transform.target}"')
