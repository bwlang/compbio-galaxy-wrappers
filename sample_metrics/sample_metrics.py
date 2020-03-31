#!/usr/bin/env python

# DESCRIPTION: Create sample level metrics to be passed to the CGD.  Metrics
#  are passed as a json dump.
# USAGE: sample_metrics.py -h
# CODED BY: John Letaw

from __future__ import print_function

import argparse
import json

# User libraries
from inputs import ProbeQcRead, AlignSummaryMetrics, GatkCountReads, MsiSensor, SamReader

VERSION = '0.6.0'


def supply_args():
    """
    Populate args.
    https://docs.python.org/2.7/library/argparse.html
    """
    parser = argparse.ArgumentParser(description='')
    # Input files that will be parsed for data.
    parser.add_argument('--probeqc_after', type=ProbeQcRead,
                        help='Probe coverage QC after UMI deduplication metrics.')
    parser.add_argument('--probeqc_before', type=ProbeQcRead,
                        help='Probe coverage QC before UMI deduplication metrics.')
    parser.add_argument('--picard_summary', type=AlignSummaryMetrics, help='Picard alignment summary metrics file.')
    parser.add_argument('--gatk_count_reads_total', type=GatkCountReads,
                        help='Output from GATK4 CountReads with total read count.')
    parser.add_argument('--gatk_count_reads_ints', type=GatkCountReads,
                        help='Output from GATK4 CountReads with read count for reads overlapping targets.')
    parser.add_argument('--msi', type=MsiSensor, help='TSV file containing MSI results')

    parser.add_argument('--primers_bam', help='BAM file to calculate primer reads on target.')
    parser.add_argument('--primers_bed', help='BED file containing primer coordinates only.')

    # These just get attached to the final json output as-is.
    parser.add_argument('--json_in', nargs='*',
                        help='Arbitrary number of files to be included in sample metrics that are in json format.')

    parser.add_argument('--outfile', help='Output file with json string.')
    parser.add_argument('--outfile_new', help='Output file with new style json string.')
    parser.add_argument('--outfile_txt', help='Output file in human readable text format.')
    parser.add_argument('--workflow', help='Pass the Galaxy workflow name, if applicable.')
    parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)
    args = parser.parse_args()

    # Check to make sure if one gatk_count_reads option is set, both are set.
    if args.gatk_count_reads_total and not args.gatk_count_reads_ints:
        parser.error("Argument gatk_count_reads_total requires gatk_count_reads_ints.")
    if args.gatk_count_reads_ints and not args.gatk_count_reads_total:
        parser.error("Argument gatk_count_reads_ints requires gatk_count_reads_total.")

    # Check to make sure if one primers option is set, both are set.
    if args.primers_bam and not args.primers_bed:
        parser.error("Argument primers_bam requires primers_bed.")
    if args.primers_bed and not args.primers_bam:
        parser.error("Argument primers_bed requires primers_bam.")

    return args


class RawMetricCollector:
    """
    Gather all of the metrics from each input source, and allow it to be accessible from here.
    gatk_cr_total = total number of reads, as given by GATK4 CountReads
    gatk_cr_ints = total number of reads crossing target intervals, as given by GATK4 CountReads
    msi = from MSIsensor, TSV output file
    """
    def __init__(self, args):
        self.gatk_cr_total = args.gatk_count_reads_total.count
        self.gatk_cr_ints = args.gatk_count_reads_ints.count
        self.msi = args.msi.msi
        self.picard_summary = args.picard_summary.metrics
        self.probeqc_before = args.probeqc_before.probeqc
        self.probeqc_after = args.probeqc_after.probeqc
        self.probeqc_header_before = args.probeqc_before.headers
        self.probeqc_header_after = args.probeqc_after.headers
        self.wf = args.workflow

        if args.primers_bam:
            self.primers_bam = SamReader(args.primers_bam, args.primers_bed).count
        else:
            self.primers_bam = None

        if args.json_in:
            self.json_in = args.json_in
            self.json_mets = self._json_in()
        else:
            self.json_mets = None

        self._params_stdout()

    def _json_in(self):
        """

        :return:
        """
        json_mets = {}
        for filename in self.json_in:
            with open(filename, 'r') as myfile:
                for line in myfile:
                    for k, v in json.loads(line).items():
                        json_mets[str(k)] = v
        return json_mets

    def _params_stdout(self):
        """
        Print variable contents to stdout.
        :return:
        """
        print("MSI: {0}".format(self.msi))
        print("ProbeQC Before: {0}".format(self.probeqc_before))
        print("ProbeQC After: {0}".format(self.probeqc_after))
        print("GATK CountReads Total: {0}".format(self.gatk_cr_total))
        print("GATK CountReads Intervals: {0}".format(self.gatk_cr_ints))
        print("Picard: {0}".format(self.picard_summary))
        print("JSON Metrics: {0}".format(self.json_mets))
        print("Primers BAM: {0}".format(self.primers_bam))


class SampleMetrics:
    """

    """

    def __init__(self, raw_mets):

        self.raw_mets = raw_mets

        self.probeqc_before = self.raw_mets.probeqc_before
        if self.probeqc_before:
            self.total_cov_before = self._calc_cov(self.probeqc_before, 'AVGD')
            self.total_bp_before = self._calc_total_bp(self.probeqc_before)
            self.header_mets_before = self._metrics_from_probeqc_header(self.raw_mets.probeqc_header_before[5:],
                                                                        self.raw_mets.probeqc_before,
                                                                        self.total_bp_before)
        else:
            self.total_cov_before = None
            self.total_bp_before = None
            self.header_mets_before = None

        self.probeqc_after = self.raw_mets.probeqc_after
        if self.probeqc_after:
            self.total_cov_after = self._calc_cov(self.probeqc_after, 'AVGD')
            self.total_bp_after = self._calc_total_bp(self.probeqc_after)
            self.header_mets_after = self._metrics_from_probeqc_header(self.raw_mets.probeqc_header_after[5:],
                                                                       self.raw_mets.probeqc_after,
                                                                       self.total_bp_after)
        else:
            self.total_cov_after = None
            self.total_bp_after = None
            self.header_mets_before = None

        self.pumi = self._pumi()
        self.on_target = self._add_on_target(self.raw_mets.picard_summary, self.total_cov_after)
        self.on_primer_frag_count = self.raw_mets.primers_bam
        self.on_primer_frag_count_pct = self._add_on_target(self.raw_mets.picard_summary,
                                                            self.on_primer_frag_count,
                                                            'PF_HQ_ALIGNED_READS')

    def _pumi(self):
        """
        Create the PUMI metric, if applicable.
        :return:
        """
        if self.probeqc_before and self.probeqc_after:
            return self._calc_metric(self.total_cov_before, (self.total_cov_after * 100))

    def _metrics_from_probeqc_header(self, headers, probeqc, total_bp):
        """
        :param headers:
        :param probeqc:
        :param total_bp:
        :return:
        """
        sample_metrics = {}
        for label in headers:
            this_cov = self._calc_cov(probeqc, label)
            sample_metrics[label] = self._calc_metric(total_bp, this_cov)
        return sample_metrics

    @staticmethod
    def _calc_total_bp(probeqc):
        """
        Get the total number of base pairs covered by your targeted region set.
        :return:
        """
        total_bp = 0
        for line in probeqc.values():
            try:
                curr = int(line['STOP']) - int(line['START']) + 1.0
                total_bp += curr
            except ValueError:
                pass

        return total_bp

    @staticmethod
    def _calc_cov(probeqc, metric):
        """
        Calculate total coverage across sample.
        :param probeqc:
        :param metric:
        :return:
        """
        total_cov = 0
        for line in probeqc.values():
            try:
                curr_bp = int(line['STOP']) - int(line['START']) + 1.0
                curr_cov = curr_bp * float(line[metric])
                total_cov += curr_cov
            except ValueError:
                pass

        return total_cov

    @staticmethod
    def _calc_metric(bp, cov):
        """
        Calculate the sample level AVGD from total bp anc coverage.
        :param bp:
        :param cov:
        :return:
        """
        return '{:0.1f}'.format(cov / bp)

    @staticmethod
    def _add_on_target(picard, total_cov, total_lbl='PF_ALIGNED_BASES'):
        """
        Include the percent on target reads metric, mainly for amplicon assays.
        Also include the on primer frag count percentage.  Rename variables...
        :return:
        """
        if 'PAIR' in picard:
            pf_bases_aligned = int(picard['PAIR'][total_lbl])
        elif 'UNPAIRED' in picard:
            pf_bases_aligned = int(picard['UNPAIRED'][total_lbl])
        else:
            pf_bases_aligned = None

        on_target = str("{:.4}".format((total_cov * 100.0) / pf_bases_aligned))

        return on_target


class MetricPrep(SampleMetrics):
    """
    Get the metrics we want from SampleMetrics, and prepare them for being written.
    """
    def __init__(self, raw_mets):
        super().__init__(raw_mets)
        self.mets = self._gather_metrics()
        print(self.mets)
        self.req_old = self._req_old()
        self.req_new = self._req_new()

    def _gather_metrics(self):
        """
        Old style metrics.
        :return:
        """
        mets = {'qthirty': self._get_avg_probeqc('Q30'),
                'averageDepth': self._get_avg_probeqc('AVGD'),

                'depthTen': self._get_avg_probeqc('D10'),
                'depthTwenty': self._get_avg_probeqc('D20'),
                'depthFifty': self._get_avg_probeqc('D50'),
                'depthOneHundred': self._get_avg_probeqc('D100'),
                'depthTwoHundredFifty': self._get_avg_probeqc('D250'),
                'depthFiveHundred': self._get_avg_probeqc('D500'),
                'depthSevenHundred': self._get_avg_probeqc('D700'),
                'depthOneThousand': self._get_avg_probeqc('D1000'),
                'depthTwelveHundredFifty': self._get_avg_probeqc('D1250'),
                'depthTwoThousand': self._get_avg_probeqc('D2000'),

                'allele_balance': "{:.2f}".format(self.raw_mets.json_mets['allele_balance']),
                'percentOnTarget': "{:.2f}".format(float(self.on_target)),
                'percentUmi': self.pumi,
                'tmb': self.raw_mets.json_mets['tmb'],
                'msi_pct': self.raw_mets.msi['somatic_pct'],
                'msi_sites': self.raw_mets.msi['total_sites'],
                'msi_somatic_sites': self.raw_mets.msi['somatic_sites'],
                'total_on_target_transcripts': self.on_primer_frag_count,
                'total_on_target_transcripts_pct': self.on_primer_frag_count_pct
                }

        return mets

    def _get_avg_probeqc(self, label):
        """
        Retrieve average metric from the probeqc_after dict.  All ProbeQCs are after, unless they
        are being run on UMI-containing assays.  If this is the case, the probeqc_before dict
        captures metrics before UMI deduplication occurs.
        :return:
        """
        try:
            this_cov = self._calc_cov(self.probeqc_after, label)
            return self._calc_metric(self.total_bp_after, this_cov)
        except KeyError:
            return None

    @staticmethod
    def _req_old():
        """
        Based on test name, list which metrics should be provided.
        :return:
        """
        return {'QIAseq_V3_RNA': ['qthirty', 'averageDepth', 'percentUmi'],
                'TruSightOne': ['qthirty', 'averageDepth', 'depthTwoHundredFifty', 'depthTwenty',
                                'depthOneHundred', 'percentOnTarget', 'depthTen', 'depthFifty'],
                'AgilentCRE_V1': ['qthirty', 'averageDepth', 'depthTwoHundredFifty', 'depthTwenty',
                                  'depthOneHundred', 'percentOnTarget', 'depthTen', 'depthFifty'],
                'QIAseq_V3_HEME2': ['qthirty', 'averageDepth', 'depthTwoHundredFifty', 'depthTwelveHundredFifty',
                                    'depthOneHundred', 'percentOnTarget', 'depthSevenHundred', 'percentUmi'],
                'QIAseq_V3_STP3': ['qthirty', 'averageDepth', 'depthTwoHundredFifty', 'depthTwelveHundredFifty',
                                   'depthOneHundred', 'percentOnTarget', 'depthSevenHundred', 'percentUmi'],
                'TruSeq_RNA_Exome_V1-2': ['qthirty', 'averageDepth', 'depthTwoHundredFifty', 'depthTwenty',
                                          'depthOneHundred', 'percentOnTarget', 'depthFiveHundred', 'depthOneThousand'],
                'QIAseq_V3_HOP': ['qthirty', 'averageDepth', 'depthTwoHundredFifty', 'depthTwenty',
                                  'depthOneHundred', 'percentOnTarget', 'depthTen', 'depthFifty', 'percentUmi'],
                'QIAseq_V3_HOP2': ['qthirty', 'averageDepth', 'depthTwoHundredFifty', 'depthTwenty',
                                   'depthOneHundred', 'percentOnTarget', 'depthTen', 'depthFifty', 'percentUmi']
                }

    @staticmethod
    def _req_new():
        """
        Based on test name, list which metrics should be provided.
        :return:
        """
        return {'QIAseq_V3_RNA': ['total_on_target_transcripts', 'total_on_target_transcripts_pct'],
                'TruSightOne': [],
                'AgilentCRE_V1': [],
                'QIAseq_V3_HEME2': [],
                'QIAseq_V3_STP3': ['msi_sites', 'msi_somatic_sites', 'msi_pct'],
                'TruSeq_RNA_Exome_V1-2': ['total_on_target_transcripts', 'total_on_target_transcripts_pct'],
                'QIAseq_V3_HOP': ['allele_balance'],
                'QIAseq_V3_HOP2': ['allele_balance']
                }


class Writer:
    """

    """
    def __init__(self, mets):
        self.mets = mets
        self.wf = self.mets.raw_mets.wf

    def write_cgd_new(self, filename):
        """
        Provide new metric style for CGD import.
        {
        "sampleRunMetrics": [
            {
                "metric": "total_on_target_reads",
                "value": 1230411
            },
            {
                "metric": "percent_on_target_reads",
                "value": 0.91
            }
        ],
        "geneMetrics": [
            {
                "gene": "ASXL1",
                "metric": "total_on_target_reads",
                "value": 469012
            },
            {
                "gene": "BRCA1",
                "metric": "total_on_target_reads",
                "value": 362330
            }
        ]
        }
        :return:
        """
        to_write = {'sampleRunMetrics': [], 'geneMetrics': []}
        for metric, val in self.mets.mets.items():
            if metric in self.mets.req_new[self.wf]:
                metric_dict = {'metric': str(metric), 'value': str(val)}
                to_write['sampleRunMetrics'].append(metric_dict)

        with open(filename, 'w') as jwrite:
            json.dump(to_write, jwrite)

    def write_cgd_old(self, filename):
        """
        Provide old metric style for CGD import.
        {
        "depthSevenHundred": "95.6",
        "depthTwelveHundredFifty": "66.8",
        "percentOnTarget": "61.03"
        }
        """
        to_write = {}
        for metric, val in self.mets.mets.items():
            if metric in self.mets.req_old[self.wf]:
                to_write[str(metric)] = str(val)

        with open(filename, 'w') as jwrite:
            json.dump(to_write, jwrite)

    def write_to_text(self, filename):
        """
        Write metrics to a text file, mainly to be viewed in Galaxy.
        :return:
        """
        with open(filename, 'w') as to_write:
            for metric, val in self.mets.mets.items():
                to_write.write("{}: {}\n".format(metric, val))


def main():
    args = supply_args()
    raw_mets = RawMetricCollector(args)
    samp_mets = MetricPrep(raw_mets)
    writer = Writer(samp_mets)
    writer.write_to_text('blah')
    writer.write_cgd_old('blah_cgd_old')
    writer.write_cgd_new('blah_cgd_new')


if __name__ == "__main__":
    main()
