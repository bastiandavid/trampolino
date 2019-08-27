# -*- coding: utf-8 -*-

"""Console script for trampolino."""
import sys
import click
import nipype.pipeline.engine as pe
from workflows.sample_workflow import *
from nipype.interfaces.io import DataSink
from nipype.interfaces import mrtrix3 as mrt


@click.group(chain=True, invoke_without_command=True)
@click.option('-i', '--in_file', type=str)
@click.option('-v', '--bvec', type=str)
@click.option('-b', '--bval', type=str)
@click.option('-a', '--anat', type=str)
@click.option('-o', '--odf', type=str)
@click.option('-s', '--seed', type=str)
@click.pass_context
def cli(ctx, in_file, bvec, bval, anat, odf, seed):
    ctx.obj['in_file'] = in_file
    ctx.obj['bvec'] = bvec
    ctx.obj['bval'] = bval
    ctx.obj['anat'] = anat
    ctx.obj['odf'] = odf
    ctx.obj['seed'] = seed
    datasink = pe.Node(DataSink(base_directory="/Users/bsms9gep/",
                                container="tramp"),
                                name="datasink")
    ctx.obj['results'] = datasink

@cli.command('recon')
@click.pass_context
def dw_recon(ctx):
    wf_sub = create_sample_pipeline(name='dwi')
    wf_sub.inputs.inputnode.dwi = ctx.obj['in_file']
    wf_sub.inputs.inputnode.bvecs = ctx.obj['bvec']
    wf_sub.inputs.inputnode.bvals = ctx.obj['bval']
    wf = pe.Workflow(name='recon')
    wf.connect([(wf_sub, ctx.obj['results'], [
        ("outputnode.csd","@odf"),
        ("dwi_mask.out_file","@mask")])])
    wf.run()
    ctx.obj['odf'] = '/Users/bsms9gep/tramp/wm.mif'
    if ctx.obj['seed'] is None:
        ctx.obj['seed'] = '/Users/bsms9gep/tramp/brainmask.mif'


@cli.command('track')
@click.pass_context
def odf_track(ctx):
    tck = pe.Node(mrt.Tractography(), name='track')
    tck.inputs.in_file = ctx.obj['odf']
    tck.inputs.seed_image = ctx.obj['seed']
    wf = pe.Workflow(name='track')
    wf.connect([(tck, ctx.obj['results'], [("out_file", "@tck")])])
    wf.run()
    ctx.obj['tck'] = '/Users/bsms9gep/tramp/tracking.tck'


@cli.command('filter')
@click.option('-t', '--tck', type=str)
@click.pass_context
def tck_filter(ctx, tck):
    pass


if __name__ == "__main__":
    sys.exit(cli(obj={}))