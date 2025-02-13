'''
Created on Aug. 24, 2022

@author: pleyte
'''

import csv
import logging
import sys

from argparse import ArgumentParser, RawDescriptionHelpFormatter, FileType
from collections import defaultdict
from BCBio import GFF
from edu.ohsu.compbio.txeff.util.tfx_log_config import TfxLogConfig

__version__ = 0.1

class RefseqToCcds(object):
    '''
    This class handles operations related to mapping from a RefSeq id to a CCDS id.
    The mappings can be found in NCBI's gff file: https://ftp.ncbi.nlm.nih.gov/refseq/H_sapiens/annotation/GRCh37_latest/refseq_identifiers/GRCh37_latest_genomic.gff.gz
    
    Running the refseq_to_ccdcs.py module from the command line takes the NCBI gff file and writes out a csv file with only the mappings, which significantly improves performance.      
    '''
    def __init__(self):
        '''
        Constructor
        '''
        self.logger = logging.getLogger(__name__)

    def get_mappings_from_gff(self, gff_file_name: str):
        '''
        Read the GFF file and return all refseq-to-ccds mappings 
        '''
        refseq_ccds_map = defaultdict(set)
        
        limit_info = dict(gff_type=['CDS'])
        with open(gff_file_name, 'r') as gff_file:
            self.logger.info(f"Reading {gff_file_name}")
            
            for rec in GFF.parse(gff_file, limit_info=limit_info):
                for feature in rec.features:
                    if feature.id.startswith('rna-'):
                        
                        # Remove the 'rna-' prefix and the occasional "-n" suffix (eg rna-NM_123.2-1)
                        ref_seq_id_parts = feature.id.split('-')                    
                        ref_seq_id = ref_seq_id_parts[1]
                        
                        if feature.sub_features:
                            for sub_feature in feature.sub_features:                                
                                dbXrefs = sub_feature.qualifiers.get('Dbxref')
                                for dbxref in dbXrefs:
                                    if(dbxref.startswith('CCDS')):
                                        ccds_id = dbxref.split(':')[1]
                                        refseq_ccds_map[ref_seq_id].add(ccds_id)
                                        self.logger.debug(f"{ref_seq_id} --> {ccds_id}")
                                    
        self.logger.info(f"Read RefSeq-CCDS map of size {len(refseq_ccds_map)} from GFF")
        return refseq_ccds_map
    
    def get_mappings_from_csv(self, csv_file_name: str):
        '''
            Read the csv file created by write_mappings, and return thm in a map object.
        '''
        refseq_ccds_map = defaultdict()
        
        with open(csv_file_name) as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                if refseq_ccds_map.get(row['refseq_id']) is not None:
                    raise Exception(f"RefSeq id {row['refseq_id']} is already mapped to {refseq_ccds_map.get(row['refseq_id'])}. Cannot add additional mapping to {row['ccds_id']}")
                
                refseq_ccds_map[row['refseq_id']] = row['ccds_id']
        
        self.logger.info(f"Read RefSeq-CCDS map of size {len(refseq_ccds_map)} from CSV")
        
        return refseq_ccds_map
        
        
    def write_mappings(self, refSeq_to_ccds: map, csv_file_name: str):
        '''
        Write the RefSeq-to-CCDS map to CSV file. The map seems to be a RefSeq id mapped to a list containing exactly one CCDS id. 
        '''
        fields = ['refseq_id', 'ccds_id']
        with open(csv_file_name, 'w') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(fields)
            
            for refseq_id, ccds_ids in refSeq_to_ccds.items():
                if(len(ccds_ids) != 1):
                    raise Exception(f"RefSeq ids are expected to map to exactly one CCDS id, but {len(ccds_ids)} found: {ccds_ids}")
                for value in refSeq_to_ccds.get(refseq_id):
                    csv_writer.writerow([refseq_id, value])

        self.logger.info(f"Wrote {len(refSeq_to_ccds)} refseq-to-cccds mappings to {csv_file_name}")

def main():
    logging.config.dictConfig(TfxLogConfig().log_config)
    
    parser = ArgumentParser(description='', formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-c", "--csv", help="CSV file to write out RefSeq-to-CCDS mappings", type=FileType('w'), required=True)
    parser.add_argument("-g", "--gff", help="GFF file to read RefSeq-to-CCDS mappings", type=FileType('r'), required=True)
    parser.add_argument('-V', '--version', action='version', version=__version__)

    # Process arguments
    args = parser.parse_args()
    
    refSeqToCcds = RefseqToCcds()
    
    # Read mappings from gff
    refSeq_to_ccds_map = refSeqToCcds.get_mappings_from_gff(args.gff.name)
    
    # Write mappings to csv 
    refSeqToCcds.write_mappings(refSeq_to_ccds_map, args.csv.name)
    
    # Read mappings from csv for validation
    csv_mappings = refSeqToCcds.get_mappings_from_csv(args.csv.name)
    assert len(refSeq_to_ccds_map.keys()) == len(csv_mappings.keys()), f"The size of the GFF and CSV maps should be the same but {len(refSeq_to_ccds_map.keys())} != {len(csv_mappings.keys())}" 
    
    return
    
if __name__ == "__main__":    
    sys.exit(main())

        