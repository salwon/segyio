import segyio
import numpy as np

class SegyIO_Shots():
    '''
    Creates an object to deal with shot-ordered SEGY files
    Assumes data are ordered by FieldRecord/trace_num, although trace_num is probably not strict
    Main interaction is with the "shots" object, a dictionary laid out as:
    { FieldRecord: ['Trace_Position', 'Num_Traces', 'Source_XY', 'Receiver_XYs'] }
    'Trace_Position': The position of the first trace in the SEGY
    'Num_Traces': Number of traces in the shot
    'Source_XY': XY for the shot
    'Receiver_XYs': List of tuples representing XY position of receivers (ordered the same as the shot data)
    Accessing by position instead of record key can be done using the object.idents
    
    Retrieve shots in a few ways:
    1) Individual shots using get_shot(FieldRecord) (returns numpy array)
    2) All shots as a dict using get_all_shots
    3) Slicing the SegyIO_Shots instance - returns dict of shots
    
    Note: dict of shots allows the individual shots to have different numbers of traces
    '''
    
    
    def __init__(self, filename):
        '''
        Reads through the segy using segyio and builds the dictionary to explain the shots
        
        '''
        self.filename = filename
        with segyio.open(self.filename,ignore_geometry=True) as f:
            self.traces_per_shot_nominal = f.bin[segyio.BinField.Traces]
            self.num_samples = len(f.samples)
            self.samp_int = f.bin[segyio.BinField.Interval]/1000
            self.shots = {}
            file_headers = f.header[:] #Grab an iterator for all of the headers
            curr_ident = None
            pos_in_file = 0
            for trace in file_headers:
                #print(trace[segyio.TraceField.FieldRecord])
                #Check to see if we're in a new shot
                if curr_ident != trace[segyio.TraceField.FieldRecord]:
                    curr_ident = trace[segyio.TraceField.FieldRecord]
                    self.shots[curr_ident] = {}
                    self.shots[curr_ident]['Trace_Position'] = pos_in_file
                    self.shots[curr_ident]['Num_Traces'] = 1
                    self.shots[curr_ident]['Source_XY'] = (trace[segyio.TraceField.SourceX],trace[segyio.TraceField.SourceY])
                    self.shots[curr_ident]['Receiver_XYs'] = []
                else: #Not in a new shot, so increase the number of traces in the shot by 1
                    self.shots[curr_ident]['Num_Traces'] += 1
                self.shots[curr_ident]['Receiver_XYs'].append((trace[segyio.TraceField.GroupX],trace[segyio.TraceField.GroupY]))
                pos_in_file += 1
            self.records = list(self.shots.keys())
            self.num_shots = len(self.shots)
                
    def get_shot(self, FieldRecord):
        '''
        Returns a single shot as a numpy array
        Shots are identified by their FieldRecord number
        '''
        
        position = self.shots[FieldRecord]['Trace_Position']
        traces_in_shot = self.shots[FieldRecord]['Num_Traces']
        retrieved_shot = np.zeros((traces_in_shot, self.num_samples))
        with segyio.open(self.filename, ignore_geometry=True) as f:
            shot_traces = f.trace[position:position+traces_in_shot]
            for i, trace in enumerate(shot_traces):
                retrieved_shot[i] = trace
        return retrieved_shot
    
    def __getitem__(self, key):
        shot_dict = {}
        
        if isinstance(key, slice) :
            #Get the start, stop, and step from the slice
            for i in range(*key.indices(self.num_shots)):
                ident = self.records[i]
                shot_dict[ident] = self.get_shot(ident)
        
        elif isinstance(key, int) :
            if key < 0 : #Handle negative indices
                key += self.num_shots
            if key > self.num_shots:
                raise IndexError("The index (%d) is out of range."%key)
            shot_dict[self.records[key]] = self.get_shot(self.records[key])
        
        return shot_dict
