# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
# -*- coding: utf-8 -*-
from __future__ import (print_function, division, unicode_literals,
                        absolute_import)

import os.path as op

from nipype.interfaces.base import (CommandLineInputSpec, CommandLine, traits, TraitedSpec,
                    File, isdefined, Undefined, InputMultiObject)
from .base import MRTrix3BaseInputSpec, MRTrix3Base


class DWIDenoiseInputSpec(MRTrix3BaseInputSpec):
    in_file = File(
        exists=True,
        argstr='%s',
        position=-2,
        mandatory=True,
        desc='input DWI image')
    mask = File(
        exists=True,
        argstr='-mask %s',
        position=1,
        desc='mask image')
    extent = traits.Tuple(
        (traits.Int, traits.Int, traits.Int),
        argstr='-extent %d,%d,%d',
        desc='set the window size of the denoising filter. (default = 5,5,5)')
    noise = File(
        argstr='-noise %s',
        name_template='%s_noise',
        name_source='in_file',
        keep_extension=True,
        desc='the output noise map')
    out_file = File(
        argstr='%s',
        position=-1,
        name_template='%s_denoised',
        name_source='in_file',
        keep_extension=True,
        desc='the output denoised DWI image')


class DWIDenoiseOutputSpec(TraitedSpec):
    noise = File(desc='the output noise map', exists=True)
    out_file = File(desc='the output denoised DWI image', exists=True)

class DWIDenoise(MRTrix3Base):
    """
    Denoise DWI data and estimate the noise level based on the optimal
    threshold for PCA.

    DWI data denoising and noise map estimation by exploiting data redundancy
    in the PCA domain using the prior knowledge that the eigenspectrum of
    random covariance matrices is described by the universal Marchenko Pastur
    distribution.

    Important note: image denoising must be performed as the first step of the
    image processing pipeline. The routine will fail if interpolation or
    smoothing has been applied to the data prior to denoising.

    Note that this function does not correct for non-Gaussian noise biases.

    For more information, see
    <https://mrtrix.readthedocs.io/en/latest/reference/commands/dwidenoise.html>

    Example
    -------

    >>> import nipype.interfaces.mrtrix3 as mrt
    >>> denoise = mrt.DWIDenoise()
    >>> denoise.inputs.in_file = 'dwi.mif'
    >>> denoise.inputs.mask = 'mask.mif'
    >>> denoise.inputs.noise = 'noise.mif'
    >>> denoise.cmdline                               # doctest: +ELLIPSIS
    'dwidenoise -mask mask.mif -noise noise.mif dwi.mif dwi_denoised.mif'
    >>> denoise.run()                                 # doctest: +SKIP
    """

    _cmd = 'dwidenoise'
    input_spec = DWIDenoiseInputSpec
    output_spec = DWIDenoiseOutputSpec


class MRDeGibbsInputSpec(MRTrix3BaseInputSpec):
    in_file = File(
        exists=True,
        argstr='%s',
        position=-2,
        mandatory=True,
        desc='input DWI image')
    axes = traits.ListInt(
        default_value=[0, 1],
        usedefault=True,
        sep=',',
        minlen=2,
        maxlen=2,
        argstr='-axes %s',
        desc='indicate the plane in which the data was acquired (axial = 0,1; '
             'coronal = 0,2; sagittal = 1,2')
    nshifts = traits.Int(
        default_value=20,
        usedefault=True,
        argstr='-nshifts %d',
        desc='discretization of subpixel spacing (default = 20)')
    minW = traits.Int(
        default_value=1,
        usedefault=True,
        argstr='-minW %d',
        desc='left border of window used for total variation (TV) computation '
             '(default = 1)')
    maxW = traits.Int(
        default_value=3,
        usedefault=True,
        argstr='-maxW %d',
        desc='right border of window used for total variation (TV) computation '
             '(default = 3)')
    out_file = File(
        name_template='%s_unr',
        name_source='in_file',
        keep_extension=True,
        argstr='%s',
        position=-1,
        desc='the output unringed DWI image')

class MRDeGibbsOutputSpec(TraitedSpec):
    out_file = File(desc='the output unringed DWI image', exists=True)

class MRDeGibbs(MRTrix3Base):
    """
    Remove Gibbs ringing artifacts.

    This application attempts to remove Gibbs ringing artefacts from MRI images
    using the method of local subvoxel-shifts proposed by Kellner et al.

    This command is designed to run on data directly after it has been
    reconstructed by the scanner, before any interpolation of any kind has
    taken place. You should not run this command after any form of motion
    correction (e.g. not after dwipreproc). Similarly, if you intend running
    dwidenoise, you should run this command afterwards, since it has the
    potential to alter the noise structure, which would impact on dwidenoise's
    performance.

    Note that this method is designed to work on images acquired with full
    k-space coverage. Running this method on partial Fourier ('half-scan') data
    may lead to suboptimal and/or biased results, as noted in the original
    reference below. There is currently no means of dealing with this; users
    should exercise caution when using this method on partial Fourier data, and
    inspect its output for any obvious artefacts.

    For more information, see
    <https://mrtrix.readthedocs.io/en/latest/reference/commands/mrdegibbs.html>

    Example
    -------

    >>> import nipype.interfaces.mrtrix3 as mrt
    >>> unring = mrt.MRDeGibbs()
    >>> unring.inputs.in_file = 'dwi.mif'
    >>> unring.cmdline
    'mrdegibbs -axes 0,1 -maxW 3 -minW 1 -nshifts 20 dwi.mif dwi_unr.mif'
    >>> unring.run()                                 # doctest: +SKIP
    """

    _cmd = 'mrdegibbs'
    input_spec = MRDeGibbsInputSpec
    output_spec = MRDeGibbsOutputSpec


class DWIBiasCorrectInputSpec(MRTrix3BaseInputSpec):
    in_file = File(
        exists=True,
        argstr='%s',
        position=-2,
        mandatory=True,
        desc='input DWI image')
    in_mask = File(
        argstr='-mask %s',
        desc='input mask image for bias field estimation')
    use_ants = traits.Bool(
        argstr='-ants',
        mandatory=True,
        desc='use ANTS N4 to estimate the inhomogeneity field',
        xor=['use_fsl'])
    use_fsl = traits.Bool(
        argstr='-fsl',
        mandatory=True,
        desc='use FSL FAST to estimate the inhomogeneity field',
        xor=['use_ants'])
    bias = File(
        argstr='-bias %s',
        desc='bias field')
    out_file = File(
        name_template='%s_biascorr',
        name_source='in_file',
        keep_extension=True,
        argstr='%s',
        position=-1,
        desc='the output bias corrected DWI image',
        genfile=True)

class DWIBiasCorrectOutputSpec(TraitedSpec):
    bias = File(desc='the output bias field', exists=True)
    out_file = File(desc='the output bias corrected DWI image', exists=True)

class DWIBiasCorrect(MRTrix3Base):
    """
    Perform B1 field inhomogeneity correction for a DWI volume series.

    For more information, see
    <https://mrtrix.readthedocs.io/en/latest/reference/scripts/dwibiascorrect.html>

    Example
    -------

    >>> import nipype.interfaces.mrtrix3 as mrt
    >>> bias_correct = mrt.DWIBiasCorrect()
    >>> bias_correct.inputs.in_file = 'dwi.mif'
    >>> bias_correct.inputs.use_ants = True
    >>> bias_correct.cmdline
    'dwibiascorrect -ants dwi.mif dwi_biascorr.mif'
    >>> bias_correct.run()                             # doctest: +SKIP
    """

    _cmd = 'dwibiascorrect'
    input_spec = DWIBiasCorrectInputSpec
    output_spec = DWIBiasCorrectOutputSpec


class ResponseSDInputSpec(MRTrix3BaseInputSpec):
    algorithm = traits.Enum(
        'msmt_5tt',
        'dhollander',
        'tournier',
        'tax',
        argstr='%s',
        position=1,
        mandatory=True,
        desc='response estimation algorithm (multi-tissue)')
    in_file = File(
        exists=True,
        argstr='%s',
        position=-5,
        mandatory=True,
        desc='input DWI image')
    mtt_file = File(argstr='%s', position=-4, desc='input 5tt image')
    wm_file = File(
        'wm.txt',
        argstr='%s',
        position=-3,
        usedefault=True,
        desc='output WM response text file')
    gm_file = File(
        argstr='%s', position=-2, desc='output GM response text file')
    csf_file = File(
        argstr='%s', position=-1, desc='output CSF response text file')
    in_mask = File(
        exists=True, argstr='-mask %s', desc='provide initial mask image')
    max_sh = InputMultiObject(
        traits.Int,
        argstr='-lmax %s',
        sep=',',
        desc=('maximum harmonic degree of response function - single value for '
              'single-shell response, list for multi-shell response'))


class ResponseSDOutputSpec(TraitedSpec):
    wm_file = File(argstr='%s', desc='output WM response text file')
    gm_file = File(argstr='%s', desc='output GM response text file')
    csf_file = File(argstr='%s', desc='output CSF response text file')


class ResponseSD(MRTrix3Base):
    """
    Estimate response function(s) for spherical deconvolution using the specified algorithm.

    Example
    -------

    >>> import nipype.interfaces.mrtrix3 as mrt
    >>> resp = mrt.ResponseSD()
    >>> resp.inputs.in_file = 'dwi.mif'
    >>> resp.inputs.algorithm = 'tournier'
    >>> resp.inputs.grad_fsl = ('bvecs', 'bvals')
    >>> resp.cmdline                               # doctest: +ELLIPSIS
    'dwi2response tournier -fslgrad bvecs bvals dwi.mif wm.txt'
    >>> resp.run()                                 # doctest: +SKIP

    # We can also pass in multiple harmonic degrees in the case of multi-shell
    >>> resp.inputs.max_sh = [6,8,10]
    >>> resp.cmdline
    'dwi2response tournier -fslgrad bvecs bvals -lmax 6,8,10 dwi.mif wm.txt'
    """

    _cmd = 'dwi2response'
    input_spec = ResponseSDInputSpec
    output_spec = ResponseSDOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['wm_file'] = op.abspath(self.inputs.wm_file)
        if self.inputs.gm_file != Undefined:
            outputs['gm_file'] = op.abspath(self.inputs.gm_file)
        if self.inputs.csf_file != Undefined:
            outputs['csf_file'] = op.abspath(self.inputs.csf_file)
        return outputs


class ACTPrepareFSLInputSpec(CommandLineInputSpec):
    in_file = File(
        exists=True,
        argstr='%s',
        mandatory=True,
        position=-2,
        desc='input anatomical image')

    out_file = File(
        'act_5tt.mif',
        argstr='%s',
        mandatory=True,
        position=-1,
        usedefault=True,
        desc='output file after processing')


class ACTPrepareFSLOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='the output response file')


class ACTPrepareFSL(CommandLine):
    """
    Generate anatomical information necessary for Anatomically
    Constrained Tractography (ACT).

    Example
    -------

    >>> import nipype.interfaces.mrtrix3 as mrt
    >>> prep = mrt.ACTPrepareFSL()
    >>> prep.inputs.in_file = 'T1.nii.gz'
    >>> prep.cmdline                               # doctest: +ELLIPSIS
    'act_anat_prepare_fsl T1.nii.gz act_5tt.mif'
    >>> prep.run()                                 # doctest: +SKIP
    """

    _cmd = 'act_anat_prepare_fsl'
    input_spec = ACTPrepareFSLInputSpec
    output_spec = ACTPrepareFSLOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = op.abspath(self.inputs.out_file)
        return outputs


class ReplaceFSwithFIRSTInputSpec(CommandLineInputSpec):
    in_file = File(
        exists=True,
        argstr='%s',
        mandatory=True,
        position=-4,
        desc='input anatomical image')
    in_t1w = File(
        exists=True,
        argstr='%s',
        mandatory=True,
        position=-3,
        desc='input T1 image')
    in_config = File(
        exists=True,
        argstr='%s',
        position=-2,
        desc='connectome configuration file')

    out_file = File(
        'aparc+first.mif',
        argstr='%s',
        mandatory=True,
        position=-1,
        usedefault=True,
        desc='output file after processing')


class ReplaceFSwithFIRSTOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='the output response file')


class ReplaceFSwithFIRST(CommandLine):
    """
    Replace deep gray matter structures segmented with FSL FIRST in a
    FreeSurfer parcellation.

    Example
    -------

    >>> import nipype.interfaces.mrtrix3 as mrt
    >>> prep = mrt.ReplaceFSwithFIRST()
    >>> prep.inputs.in_file = 'aparc+aseg.nii'
    >>> prep.inputs.in_t1w = 'T1.nii.gz'
    >>> prep.inputs.in_config = 'mrtrix3_labelconfig.txt'
    >>> prep.cmdline                               # doctest: +ELLIPSIS
    'fs_parc_replace_sgm_first aparc+aseg.nii T1.nii.gz \
mrtrix3_labelconfig.txt aparc+first.mif'
    >>> prep.run()                                 # doctest: +SKIP
    """

    _cmd = 'fs_parc_replace_sgm_first'
    input_spec = ReplaceFSwithFIRSTInputSpec
    output_spec = ReplaceFSwithFIRSTOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = op.abspath(self.inputs.out_file)
        return outputs
