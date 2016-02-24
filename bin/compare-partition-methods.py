#!/usr/bin/env python
import os
import argparse
import sys
import re
import csv
from subprocess import Popen
sys.path.insert(1, './python')
csv.field_size_limit(sys.maxsize)
from humans import humans
import utils
import compareutils
import glob

# ----------------------------------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument('--datadir', default=os.getcwd() + '/data/imgt', help='Directory from which to read non-sample-specific information (e.g. germline genes)')
parser.add_argument('--fsdir', default='/fh/fast/matsen_e/' + os.getenv('USER') + '/work/partis-dev/_output')
parser.add_argument('--mutation-multipliers', default='1')
parser.add_argument('--data', action='store_true')
parser.add_argument('--print-metrics', action='store_true')
parser.add_argument('--overwrite', action='store_true')
parser.add_argument('--expected-methods', default='vollmers-0.9:mixcr:changeo:vsearch-partition:naive-hamming-partition:partition')
parser.add_argument('--synthetic-partitions', default='distance-0.03:0.10-reassign:0.60-singletons') # 0.75-singletons
parser.add_argument('--indels', action='store_true')
parser.add_argument('--indel-location')
parser.add_argument('--lonely-leaves', action='store_true')
parser.add_argument('--mimic', action='store_true')
parser.add_argument('--box', action='store_true')
parser.add_argument('--zipf', action='store_true')
parser.add_argument('--extra-label-str')
parser.add_argument('--bak', action='store_true')
parser.add_argument('--count-distances', action='store_true')
parser.add_argument('--n-leaf-list', default='10')
parser.add_argument('--hfrac-bound-list')
parser.add_argument('--subset', type=int)
parser.add_argument('--n-to-partition', type=int, default=5000)
parser.add_argument('--n-data-to-cache', type=int, default=100000)
parser.add_argument('--n-sim-seqs', type=int, default=10000)
parser.add_argument('--n-subsets', type=int)
parser.add_argument('--istartstop')  # NOTE usual zero indexing
parser.add_argument('--istartstoplist')  # list of istartstops for comparisons
parser.add_argument('--plot-mean-of-subsets', action='store_true')
parser.add_argument('--humans', required=True)  #'A')
parser.add_argument('--no-similarity-matrices', action='store_true')
parser.add_argument('--seed-cluster-bounds', default='20:30')
all_actions = ['cache-data-parameters', 'simulate', 'cache-simu-parameters', 'partition', 'naive-hamming-partition', 'vsearch-partition', 'seed-partition', 'seed-naive-hamming-partition', 'run-viterbi', 'run-changeo', 'run-mixcr', 'run-igscueal', 'synthetic', 'write-plots', 'compare-subsets']
parser.add_argument('--actions', required=True)  #, choices=all_actions)  #default=':'.join(all_actions))
args = parser.parse_args()
args.actions = utils.get_arg_list(args.actions)
args.mutation_multipliers = utils.get_arg_list(args.mutation_multipliers, floatify=True)
args.n_leaf_list = utils.get_arg_list(args.n_leaf_list, floatify=True)
args.istartstop = utils.get_arg_list(args.istartstop, intify=True)
args.istartstoplist = utils.get_arg_list(args.istartstoplist, intify=True, list_of_pairs=True)
args.humans = utils.get_arg_list(args.humans)
args.hfrac_bound_list = utils.get_arg_list(args.hfrac_bound_list, floatify=True, list_of_pairs=True)
args.expected_methods = utils.get_arg_list(args.expected_methods)
args.synthetic_partitions = utils.get_arg_list(args.synthetic_partitions)
for isp in range(len(args.synthetic_partitions)):  # I really shouldn't have set it up this way
    args.synthetic_partitions[isp] = 'misassign-' + args.synthetic_partitions[isp]
args.seed_cluster_bounds = utils.get_arg_list(args.seed_cluster_bounds, intify=True)

if 'cache-data-parameters' in args.actions:
    args.data = True

print 'TODO change name from hfrac_bounds'
assert args.subset is None or args.istartstop is None  # dosn't make sense to set both of them

if args.subset is not None:
    if 'write-plots' not in args.actions:
        assert args.n_subsets == 10  # for all the subset plots, I split into ten subsets, then ended up only using the first thre of 'em, so you have to set n_subsets to 10 if you're running methods, but then to 3 when you're writing plots
if args.istartstop is not None: 
    args.n_to_partition = args.istartstop[1] - args.istartstop[0]

if args.bak:
    args.fsdir = args.fsdir.replace('_output', '_output.bak')

# ----------------------------------------------------------------------------------------
# compareutils.FOOP()
# sys.exit()

# ----------------------------------------------------------------------------------------
procs = []
for human in args.humans:

    if human in humans['stanford']:
        datadir = '/shared/silo_researcher/Matsen_F/MatsenGrp/data/stanford-lineage/2014-11-17-vollmers'
        datafname = glob.glob(datadir + '/*' + human + '*')[0]  # should throw an index error if length is less than one... but still, this is hackey
    elif human in humans['adaptive']:
        datafname = args.fsdir.replace('_output', 'data') + '/adaptive/' + human + '/shuffled.csv'
    else:
        assert False

    label = human
    if args.extra_label_str is not None:
        label += '-' + args.extra_label_str

    print 'run', human
    n_leaves, mut_mult = None, None  # values if we're runing on data
    parameterlist = [{'n_leaves' : None, 'mut_mult' : None, 'hfrac_bounds' : None}]
    if not args.data:
        if args.hfrac_bound_list is None:
            parameterlist = [{'n_leaves' : nl, 'mut_mult' : mm, 'hfrac_bounds' : None} for nl in args.n_leaf_list for mm in args.mutation_multipliers]
        else:
            parameterlist = [{'n_leaves' : nl, 'mut_mult' : mm, 'hfrac_bounds' : hbs} for nl in args.n_leaf_list for mm in args.mutation_multipliers for hbs in args.hfrac_bound_list]

    for action in args.actions:
        if action == 'write-plots' or action == 'compare-subsets':
            continue
        print ' ', action
        if action == 'cache-data-parameters':
            compareutils.execute(args, action, datafname, label, n_leaves, mut_mult, procs)
            continue

        for params in parameterlist:
            compareutils.execute(args, action, datafname, label, params['n_leaves'], params['mut_mult'], procs, params['hfrac_bounds'])

    if 'write-plots' in args.actions:
        compareutils.write_all_plot_csvs(args, label, parameterlist, datafname)
    if 'compare-subsets' in args.actions:
        compareutils.compare_subsets(args, label)

if len(procs) > 0:
    exit_codes = [p.wait() for p in procs]
    print 'exit ', exit_codes
