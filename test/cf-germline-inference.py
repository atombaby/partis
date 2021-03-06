#!/usr/bin/env python
import numpy
from collections import OrderedDict
import os
import random
import argparse
import sys
import subprocess
sys.path.insert(1, './python')

import utils
import glutils
from hist import Hist

fsdir = '/fh/fast/matsen_e'
alfdir = fsdir + '/dralph/partis/allele-finder'
locus = 'igh'
region = 'v'

legend_titles = {
    'mfreq' : 'mutation',
    'nsnp' : 'N SNPs',
    'multi-nsnp' : 'N SNPs',
    'prevalence' : 'prevalence',
    'n-leaves' : 'mean N leaves',
}

# # ----------------------------------------------------------------------------------------
# sys.path.insert(1, './datascripts')
# import heads
# label = 'vz'
# ptype = 'sw'
# subject = None  # 'GMC'
# studies = [
#     'kate-qrs-2016-09-09',
#     'laura-mb-2016-12-22',
#     'chaim-donor-45-2016-08-04',
#     'adaptive-billion-read-2016-04-07',
#     'vollmers-2016-04-08',
#     # 'jason-mg-2017-02-01',
#     # 'jason-influenza-2017-02-03',
# ]

# merged_names, merged_dirs = [], []
# for study in studies:
#     names, dirs = [], []
#     metafo = heads.read_metadata(study)
#     print study
#     for dset in metafo:
#         if subject is not None and metafo[dset]['subject'] != subject:
#             continue
#         bdir = fsdir + '/processed-data/partis/' + study + '/' + label + '/' + dset
#         if metafo[dset]['timepoint'] == 'merged':
#             continue
#         if dset == 'Hs-LN3-5RACE-IgG':  # bad one
#             continue
#         if not os.path.exists(bdir):
#             print '    %s missing' % dset
#             continue
#         names.append(metafo[dset]['shorthand'])
#         dirs.append(bdir + '/plots/' + ptype + '/mute-freqs/overall')
#     outdir = fsdir + '/dralph/partis/tmp/lots-of-mfreqs/' + study
#     if subject is not None:
#         outdir += '/' + subject
#     subprocess.check_call(['./bin/compare-plotdirs.py', '--outdir', outdir, '--plotdirs', ':'.join(dirs), '--names', ':'.join(names), '--normalize'])
#     merged_names += names
#     merged_dirs += dirs
# # subprocess.check_call(['./bin/compare-plotdirs.py', '--outdir', fsdir + '/dralph/partis/tmp/lots-of-mfreqs/merged', '--plotdirs', ':'.join(merged_dirs), '--names', ':'.join(merged_names), '--normalize'])
# sys.exit()

# # ----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
def run(cmd_str):
    print '%s %s' % (utils.color('red', 'run'), cmd_str)
    sys.stdout.flush()
    # subprocess.Popen(cmd_str.split())
    subprocess.check_call(cmd_str.split())

# ----------------------------------------------------------------------------------------
def varvalstr(name, val):
    if name == 'multi-nsnp':
        valstr = ':'.join([str(v) for v in val])
    else:
        valstr = str(val)
    return valstr

# ----------------------------------------------------------------------------------------
def legend_str(args, val):
    if args.action == 'mfreq':
        lstr = '%.1fx' % val
    elif args.action == 'nsnp':
        lstr = '%d' % val
    elif args.action == 'multi-nsnp':
        lstr = '%s' % '+'.join([str(v) for v in val])
    elif args.action == 'prevalence':
        lstr = '%d%%' % (100*val)
    elif args.action == 'n-leaves':
        lstr = '%.1f' % val
    else:
        assert False
    return lstr

# ----------------------------------------------------------------------------------------
def get_outdir(baseoutdir, n_events, varname, varval):
    outdir = baseoutdir
    outdir += '/' + varname + '-' + varvalstr(varname, varval)
    return outdir + '/n-events-' + str(n_events)  # .replace('000', 'k')

# ----------------------------------------------------------------------------------------
def get_single_performance(outdir, debug=False):
    sglfo = glutils.read_glfo(outdir + '/germlines/simulation', locus=locus)
    iglfo = glutils.read_glfo(outdir + '/simu-test/sw/germline-sets', locus=locus)
    missing_alleles = set(sglfo['seqs'][region]) - set(iglfo['seqs'][region])
    spurious_alleles = set(iglfo['seqs'][region]) - set(sglfo['seqs'][region])
    if debug:
        if len(missing_alleles) > 0:
            print '    %2d  missing %s' % (len(missing_alleles), ' '.join([utils.color_gene(g) for g in missing_alleles]))
        if len(spurious_alleles) > 0:
            print '    %2d spurious %s' % (len(spurious_alleles), ' '.join([utils.color_gene(g) for g in spurious_alleles]))
        if len(missing_alleles) == 0 and len(spurious_alleles) == 0:
            print '    none missing'
    return {
        'missing' : len(missing_alleles),
        'spurious' : len(spurious_alleles),
        'total' : len([g for g in sglfo['seqs'][region] if '+' in g]),  # anybody with a '+' should be a new allele
    }

# ----------------------------------------------------------------------------------------
def plot_test(args, baseoutdir):
    import plotting
    plot_types = ['missing', 'spurious']

    def get_performance(varname, varval):
        perf_vals = {pt : [] for pt in plot_types + ['total']}
        for iproc in range(args.n_tests):
            single_vals = get_single_performance(get_outdir(baseoutdir, n_events, varname, varval) + '/' + str(iproc))
            for ptype in plot_types + ['total']:
                perf_vals[ptype].append(single_vals[ptype])
        return perf_vals

    plotvals = []
    for varval in args.varvals:
        print '%s %s' % (args.action, varvalstr(args.action, varval))
        plotvals.append({pt : {k : [] for k in ['xvals', 'ycounts', 'ytotals']} for pt in plot_types})
        for n_events in args.n_event_list:
            perf_vals = get_performance(varname=args.action, varval=varval)
            print '  %d' % n_events
            print '    iproc    %s' % ' '.join([str(i) for i in range(args.n_tests)])
            print '    missing  %s' % ' '.join([str(v) for v in perf_vals['missing']]).replace('0', ' ')
            print '    spurious %s' % ' '.join([str(v) for v in perf_vals['spurious']]).replace('0', ' ')
            for ptype in plot_types:
                count = sum(perf_vals[ptype])
                plotvals[-1][ptype]['xvals'].append(n_events)
                plotvals[-1][ptype]['ycounts'].append(count)
                plotvals[-1][ptype]['ytotals'].append(sum(perf_vals['total']))
    for ptype in plot_types:
        plotting.plot_gl_inference_fractions(baseoutdir, ptype, [pv[ptype] for pv in plotvals], labels=[legend_str(args, v) for v in args.varvals], xlabel='sample size', ylabel='fraction %s' % ptype, leg_title=legend_titles.get(args.action, None))

# ----------------------------------------------------------------------------------------
def get_base_cmd(args, n_events):
    cmd = './bin/test-allele-finding.py'
    cmd += ' --n-procs 5 --n-tests ' + str(args.n_tests)
    if not args.no_slurm:
        cmd += ' --slurm'
    cmd += ' --inf-v-genes ' + args.v_genes[0]
    cmd += ' --n-sim-events ' + str(n_events)
    return cmd

# ----------------------------------------------------------------------------------------
def run_test(args, baseoutdir):
    for val in args.varvals:
        for n_events in args.n_event_list:
            cmd = get_base_cmd(args, n_events)
            sim_v_genes = [args.v_genes[0]]
            nsnpstr = '1'
            if args.action == 'mfreq':
                cmd += ' --mut-mult ' + str(val)
            elif args.action == 'nsnp':
                nsnpstr = str(val)
            elif args.action == 'multi-nsnp':
                nsnpstr = ':'.join([str(n) for n in val])
                sim_v_genes *= len(val)
            elif args.action == 'prevalence':
                cmd += ' --allele-prevalence-freqs ' + str(1. - val) + ':' + str(val)  # i.e. previously-known allele has 1 - p, and new allele has p
            elif args.action == 'n-leaves':
                cmd += ' --n-leaves ' + str(val)  # NOTE default of 1 (for other tests) is set in test-allele-finding.py
                cmd += ' --n-leaf-distribution geometric'
                cmd += ' --n-max-queries ' + str(n_events)  # i.e. we simulate <n_events> rearrangement events, but then only use <n_events> sequences for inference
            else:
                assert False
            cmd += ' --sim-v-genes ' + ':'.join(sim_v_genes)
            cmd += ' --nsnp-list ' + nsnpstr
            cmd += ' --outdir ' + get_outdir(baseoutdir, n_events, args.action, val)
            run(cmd)

# ----------------------------------------------------------------------------------------
default_varvals = {
    'mfreq' : '0.1:1.0:2.0',
    'nsnp' : '1:2:3:4',
    'multi-nsnp' : '1,1:1,3:2,3',
    'prevalence' : '0.1:0.2:0.3',
    'n-leaves' : '1.5:3:10:25',
}
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['mfreq', 'nsnp', 'multi-nsnp', 'prevalence', 'n-leaves'])
parser.add_argument('--v-genes', default='IGHV4-39*01')
parser.add_argument('--varvals')
parser.add_argument('--n-event-list', default='1000:2000:4000:8000')  # NOTE modified later for multi-nsnp
parser.add_argument('--n-tests', type=int, default=10)
parser.add_argument('--plot', action='store_true')
parser.add_argument('--no-slurm', action='store_true')
parser.add_argument('--label')
args = parser.parse_args()

args.v_genes = utils.get_arg_list(args.v_genes)
args.n_event_list = utils.get_arg_list(args.n_event_list, intify=True)

# ----------------------------------------------------------------------------------------
baseoutdir = alfdir
if args.label is not None:
    baseoutdir += '/' + args.label
baseoutdir += '/' + args.action

if args.varvals is None:
    args.varvals = default_varvals[args.action]
kwargs = {}
if args.action == 'mfreq' or args.action == 'prevalence' or args.action == 'n-leaves':
    kwargs['floatify'] = True
if args.action == 'nsnp':
    kwargs['intify'] = True
args.varvals = utils.get_arg_list(args.varvals, **kwargs)
if args.action == 'multi-nsnp':
    args.varvals = [[int(n) for n in gstr.split(',')] for gstr in args.varvals]  # list of nsnps for each test, e.g. '1,1:2,2' runs two tests: 1) two new alleles, each with one snp and 2) two new alleles each with 2 snps
    factor = numpy.median([(len(nl) + 1) / 2. for nl in args.varvals])  # i.e. the ratio of (how many alleles we'll be dividing the events among), to (how many we'd be dividing them among for the other [single-nsnp] tests)
    args.n_event_list = [int(factor * n) for n in args.n_event_list]

if args.plot:
    plot_test(args, baseoutdir)
else:
    run_test(args, baseoutdir)
