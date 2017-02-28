#!/usr/bin/env python
"""This script provides a simplified contact prediction pipeline. It will
take either a sequence or alignment as starting point and predict, analyse
and evaluate the final prediction and any intermediate results.

It uses two external programs to perform this task.

   - HHblits for Sequence Alignment generation, and
   - CCMpred for Direct Coupling Analysis.

*** The two programs above need to be installed separately ***

"""


__author__ = "Felix Simkovic"
__date__ = "01 June 2016"
__version__ = 0.1

import argparse
import conkit
import logging
import os
import sys
import time

logging.basicConfig(format='%(message)s', level=logging.INFO)


def add_default_args(parser):
    """Define default arguments"""
    parser.add_argument('-prefix', default='conkit', help='Job ID')
    parser.add_argument('-wdir', default=os.getcwd(), help='Working directory')
    parser.add_argument('--demo', default=False, action="store_true", help=argparse.SUPPRESS)


def add_alignment_args(subparsers):
    """Parser with alignment as starting point"""
    from_alignment_subparser = subparsers.add_parser('aln')
    add_default_args(from_alignment_subparser)
    from_alignment_subparser.add_argument('ccmpred', help='Path to the CCMpred executable')
    from_alignment_subparser.add_argument('alignment_file', help='Path to alignment file')
    from_alignment_subparser.add_argument('alignment_format', help='Alignment format')
    from_alignment_subparser.set_defaults(which='alignment')


def add_sequence_args(subparsers):
    """Parser with sequence as starting point"""
    from_sequence_subparser = subparsers.add_parser('seq')
    add_default_args(from_sequence_subparser)
    from_sequence_subparser.add_argument('--nodca', default=False, action='store_true',
                                         help=argparse.SUPPRESS)
    from_sequence_subparser.add_argument('ccmpred', help='Path to the CCMpred executable')
    from_sequence_subparser.add_argument('hhblits', help='Path to the HHblits executable')
    from_sequence_subparser.add_argument('hhblitsdb', help='Path to HHblits database')
    from_sequence_subparser.add_argument('sequence_file', help='Path to sequence file')
    from_sequence_subparser.add_argument('sequence_format', help='Sequence format')
    from_sequence_subparser.set_defaults(which='sequence')


def main(argl=None):
    """The main routine for conkit-predict functionality

    Parameters
    ----------
    argl : list, tuple, optional
       A list containing the command line flags

    """
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers()
    # Add the subparsers
    add_alignment_args(subparsers)
    add_sequence_args(subparsers)
    # Parse all arguments
    args = parser.parse_args(argl)

    logging.info('Prefix: {0}'.format(args.prefix))
    logging.info('Working dir: {0}'.format(args.wdir))

    if args.which == 'alignment':
        aln_fname = os.path.abspath(args.alignment_file)
        aln_format = args.alignment_format.lower()

        logging.info('Input alignment file: {0}'.format(aln_fname))
        logging.info('Input alignment format: {0}'.format(aln_format))

        # Check that we can handle the alignment file
        if aln_format not in conkit.io.SEQUENCE_FILE_PARSERS:
            msg = 'Sequence format not yet implemented: {0}'.format(aln_fname)
            logging.critical(msg)
            raise ValueError(msg)

        # Convert our alignment file to JONES format
        if aln_format != 'jones':
            jon_fname = os.path.join(args.wdir, args.prefix + '.jones')
            conkit.io.convert(aln_fname, aln_format, jon_fname, 'jones')
        else:
            jon_fname = aln_fname

    elif args.which == 'sequence':
        hhblits = os.path.abspath(args.hhblits)
        hhblitsdb = os.path.abspath(args.hhblitsdb)
        seq_fname = os.path.abspath(args.sequence_file)
        seq_format = args.sequence_format.lower()
        a3m_fname = os.path.join(args.wdir, args.prefix + '.a3m')
        hhr_fname = os.path.join(args.wdir, args.prefix + '.hhr')

        logging.info('HHblits DB: {0}'.format(hhblitsdb))
        logging.info('Input sequence file: {0}'.format(seq_fname))
        logging.info('Input sequence format: {0}'.format(seq_format))

        # Check that we can handle the sequence file
        if seq_format not in conkit.io.SEQUENCE_FILE_PARSERS:
            msg = 'Sequence format not yet implemented: {0}'.format(seq_format)
            logging.critical(msg)
            raise ValueError(msg)

        # Convert our sequence file to FASTA format
        if seq_format != 'fasta':
            seq_fname_tmp = seq_fname.rsplit('.', 1)[0] + '.fasta'
            conkit.io.convert(seq_fname, seq_format, seq_fname_tmp, 'fasta')
            seq_fname = seq_fname_tmp

        # Generate a multiple sequence alignment
        hhblits_cline = conkit.applications.HHblitsCommandLine(cmd=hhblits,
                                                               input=seq_fname, output=hhr_fname,
                                                               database=hhblitsdb, oa3m=a3m_fname,
                                                               niterations=3, id=99, show_all=True,
                                                               cov=60, diff='inf', maxfilt=500000)
        logging.info('Executing: {0}'.format(hhblits_cline))
        if args.demo:
            assert os.path.isfile(a3m_fname)
            time.sleep(5)
        else:
            hhblits_cline()

        jon_fname = os.path.join(args.wdir, args.prefix + '.jones') 
        conkit.io.convert(a3m_fname, 'a3m', jon_fname, 'jones')

    else:
        raise RuntimeError('Should never get to here')

    # CCMpred requires alignments to be in the *jones* format - i.e. the format created
    # and used by David Jones in PSICOV
    logging.info('Final alignment file: {0}'.format(jon_fname))
    msa_h = conkit.io.read(jon_fname, 'jones')
    logging.info('|- Total Number of sequences: {0}'.format(msa_h.nseqs))
    logging.info('|- Pairwise Sequence Identity Threshold: {0}'.format(0.7))
    logging.info('|- Number of effective sequences: {0}'.format(msa_h.calculate_meff(identity=0.7)))
    freq_plot_fname = os.path.join(args.wdir, args.prefix + 'freq.pdf')
    conkit.plot.SequenceCoverageFigure(msa_h, file_name=freq_plot_fname)
    logging.info('|- Plotted sequence coverage: {0}'.format(freq_plot_fname))

    # Kill switch to not run CCMpred DCA
    if args.which == 'sequence' and args.nodca:
        return

    # Use the re-formatted alignment for contact prediction
    ccmpred = args.ccmpred
    matrix_fname = os.path.join(args.wdir, args.prefix + '.mat')
    ccmpred_cline = conkit.applications.CCMpredCommandLine(cmd=ccmpred,
                                                           alnfile=jon_fname, matfile=matrix_fname,
                                                           threads=2, renormalize=True)
    logging.info('Executing: {0}'.format(ccmpred_cline))
    if args.demo:
        assert os.path.isfile(matrix_fname)
        time.sleep(5)
    else:
        ccmpred_cline()

    # Add sequence information to contact hierarchy
    dtn = 5
    dfactor = 1.
    cmap = conkit.io.read(matrix_fname, 'ccmpred').top_map
    cmap.sequence = conkit.io.read(jon_fname, 'jones').top_sequence
    cmap.remove_neighbors(min_distance=dtn, inplace=True)
    cmap.sort('raw_score', reverse=True, inplace=True)
    cmap = cmap[:cmap.sequence.seq_len]                 # subset the selection
    contact_map_fname = os.path.join(args.wdir, args.prefix + 'cmap.pdf')
    conkit.plot.ContactMapFigure(cmap, file_name=contact_map_fname)
    logging.info('Plotted contact map: {0}'.format(contact_map_fname))
    logging.info('|- Min sequence separation for contacting residues: {0}'.format(dtn))
    logging.info('|- Contact list cutoff factor: {0} * L'.format(dfactor))

    # Use the ccmpred parser to write a contact file
    casprr_fname = os.path.join(args.wdir, args.prefix + '.rr')
    conkit.io.convert(matrix_fname, 'ccmpred', casprr_fname, 'casprr')
    logging.info('Final prediction file: {0}'.format(casprr_fname))

    return


if __name__ == "__main__":
    sys.exit(main())