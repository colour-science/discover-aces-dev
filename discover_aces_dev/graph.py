# -*- coding: utf-8 -*-

import logging

from discover_aces_dev.common import is_networkx_installed
from discover_aces_dev.discover import (CTLTransform, CTLTransformPair,
                                        classify_aces_ctl_transforms,
                                        discover_aces_ctl)

if is_networkx_installed():  # pragma: no cover
    import networkx as nx

__all__ = []


def _exclusion_filterer_ARRIIDT(filename):
    if 'Alexa' not in filename:
        return True

    if 'Alexa-v3-raw-EI800' in filename and 'ND1pt3' not in filename:
        return True

    return False


def _build_graph():
    unclassified_ctl_transforms = []
    classified_ctl_transforms = classify_aces_ctl_transforms(
        discover_aces_ctl(filterers=[_exclusion_filterer_ARRIIDT]))

    for category, classifiers in classified_ctl_transforms.items():
        for classifier, ctl_transforms in classifiers.items():
            for name, ctl_transform in ctl_transforms.items():
                if isinstance(ctl_transform, CTLTransform):
                    unclassified_ctl_transforms.append(ctl_transform)
                elif isinstance(ctl_transform, CTLTransformPair):
                    unclassified_ctl_transforms.append(
                        ctl_transform.forward_transform)
                    unclassified_ctl_transforms.append(
                        ctl_transform.inverse_transform)

    graph = nx.DiGraph()

    for ctl_transform in unclassified_ctl_transforms:
        source = ctl_transform.source
        target = ctl_transform.target

        if source is None or target is None:
            continue

        graph.add_node(source, ctl_transform_type=ctl_transform.type)
        graph.add_node(target, ctl_transform_type=ctl_transform.type)

        graph.add_edge(source, target)

    return graph


CONVERSION_GRAPH = _build_graph() if is_networkx_installed() else None


def plot_automatic_colour_conversion_graph(filename, prog='dot', args=''):
    if is_networkx_installed(raise_exception=True):
        agraph = nx.nx_agraph.to_agraph(CONVERSION_GRAPH)

        agraph.node_attr.update(
            style='filled',
            shape='circle',
            fontname='Helvetica',
            fontsize=20)

        ctl_transforms_csc = []
        ctl_transforms_idt = []
        ctl_transforms_odt = []
        ctl_transforms_output_transform = []
        ctl_transforms_lmt = []

        for node in agraph.nodes():
            ctl_transform_type = node.attr['ctl_transform_type']
            if node in ('ACES2065-1', 'OCES'):
                node.attr.update(
                    shape='doublecircle',
                    color='#673AB7FF',
                    fillcolor='#673AB770',
                    fontsize=30)
            elif ctl_transform_type == 'ACEScsc':
                node.attr.update(color='#00BCD4FF', fillcolor='#00BCD470')
                ctl_transforms_csc.append(node)
            elif ctl_transform_type == 'IDT':
                node.attr.update(color='#B3BC6D', fillcolor='#E6EE9C')
                ctl_transforms_idt.append(node)
            elif ctl_transform_type in ('ODT', 'InvODT'):
                node.attr.update(color='#CA9B52', fillcolor='#FFCC80')
                ctl_transforms_odt.append(node)
            elif ctl_transform_type in ('RRTODT', 'InvRRTODT'):
                node.attr.update(color='#C88719', fillcolor='#FFB74D')
                ctl_transforms_output_transform.append(node)
            elif ctl_transform_type == 'LMT':
                node.attr.update(color='#4BA3C7', fillcolor='#81D4FA')
                ctl_transforms_lmt.append(node)

        agraph.add_subgraph(
            ctl_transforms_csc, name='cluster_ACEScsc', color='#00BCD4FF')
        agraph.add_subgraph(
            ctl_transforms_idt, name='cluster_IDT', color='#B3BC6D')
        agraph.add_subgraph(
            ctl_transforms_odt, name='cluster_ODT', color='#CA9B52')
        agraph.add_subgraph(
            ctl_transforms_output_transform,
            name='cluster_OutputTransform',
            color='#C88719')
        agraph.add_subgraph(
            ctl_transforms_lmt, name='cluster_LMT', color='#4BA3C7')

        agraph.edge_attr.update(color='#26323870')
        agraph.draw(filename, prog=prog, args=args)

        return agraph


if __name__ == '__main__':
    from rich.logging import RichHandler

    logging.basicConfig(
        level=logging.INFO, datefmt="[%X] ", handlers=[RichHandler()])

    plot_automatic_colour_conversion_graph('conversion_graph.png')
