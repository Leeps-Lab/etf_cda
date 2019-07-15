import csv

# a utility to process and organize CSV config files
# one ConfigManager object should be created per subsession
class ConfigManager():

    # config manager takes a path to a config csv, the current round number
    # and a dict mapping config field names to their type
    def __init__(self, config_file_path, round_number, fields_dict):

        self.rounds = []
        with open(config_file_path) as infile:
            rows = list(csv.DictReader(infile))
        
        self.num_rounds = len(rows)
        if round_number >= self.num_rounds:
            return

        row = rows[round_number-1]

        self.round_dict = {}
        for field, field_type in fields_dict.items():
            if field not in row:
                raise ValueError('input CSV is missing field "{}"'.format(field))
            
            if field_type is int:
                self.round_dict[field] = int(row[field])
            elif field_type is float:
                self.round_dict[field] = float(row[field])
            elif field_type is bool:
                self.round_dict[field] = (row[field].lower() == 'true')
            elif field_type is str:
                self.round_dict[field] = row[field]
            else:
                raise ValueError('invalid field type: "{}"'.format(field_type.__name__))
        
    def __getattr__(self, field):
        if field == 'num_rounds':
            return self.num_rounds
        if field not in self.round_dict:
            raise AttributeError('field "{}" does not exist'.format(field))
        return self.round_dict[field]
