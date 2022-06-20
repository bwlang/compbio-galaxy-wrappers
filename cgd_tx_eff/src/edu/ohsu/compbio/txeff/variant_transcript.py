from edu.ohsu.compbio.annovar.annovar_parser import AnnovarVariantFunction

class VariantTranscript(AnnovarVariantFunction):
    
    def __init__(self, chromosome, position, ref, alt):
        '''
        Create new VariantTranscript using chromosome, position, ref, and alt.
        '''
        super().__init__(chromosome, position, ref, alt)
            
        self.protein_transcript = None
            
    def __eq__(self, obj):
        if super.__eq__(self,obj):
            return self.protein_transcript == obj.protein_transcript
        else:           
            return False
    