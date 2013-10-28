# -*- coding: utf-8 -*-
import logging
from optparse import make_option
import pygraphviz as pgv

from django.core.management.base import BaseCommand, CommandError
from workflows.models import Workflow

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '''Generates a graph of available state machines'''
    option_list = BaseCommand.option_list + (
        make_option('--layout', '-l', action='store', dest='layout', default='dot',
                    help='Layout to be used by GraphViz for visualization. Layouts: circo dot fdp neato twopi'),
        make_option('--format', '-f', action='store', dest='format', default='pdf',
                    help='Format of the output file. Formats: pdf, jpg, png'),
        make_option('--create-dot', action='store_true', dest='create_dot', default=False,
                    help='Create a dot file'),
    )
    args = '[workflow]'
    label = 'workflow name, i.e. my-workflow'

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError('need one or more arguments for workflow codename')

        for workflow_name in args:
            self.render_workfow(workflow_name, **options)

    @staticmethod
    def render_workfow(name, **options):
        workflow = Workflow.objects.get(codename=name)
        graph = pgv.AGraph(strict=False, directed=True)
        graph.graph_attr.update({
            'label': 'Workflow %s' % workflow.name,
            'fontname': 'Helvetica',
            'center': 'true',
            'labelloc': 't',
            'rank': 'same',
            'truecolor': 'true',
            'bgcolor': 'transparent'
        })
        graph.node_attr.update({
            'shape': 'box'
        })
        graph.edge_attr.update({
            'fontcolor': 'gray60',
            'fontsize': '8.0',
            'decorate': 'true'
        })

        states = []
        edges = []
        for state in workflow.states.all():
            states.append(state)
            for transition in state.transitions.all():
                edges.append((state, transition))

        for state in states:
            if workflow.initial_state == state:
                kwargs = {
                    'fontcolor': 'white',
                    'fillcolor': 'black',
                    'style': 'filled',
                    'root': 'true'
                }
            else:
                kwargs = {}
            graph.add_node(state.codename, label=state.name, **kwargs)

        for state, transition in edges:
            graph.add_edge(state.codename, transition.destination.codename, label=transition.name)

        loc = 'workflow_%s' % (name,)
        if options['create_dot']:
            graph.write('%s.dot' % loc)

        logger.debug('Setting layout %s' % options['layout'])
        logger.debug('Trying to render %s' % loc)
        graph.draw("%s.%s" % (loc, options['format']), prog=options['layout'])
        logger.info('Created workflow graph for %s at %s' % (name, loc))
