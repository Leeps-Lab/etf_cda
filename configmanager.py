import csv
import os

# a utility to process and organize CSV config files
# a ConfigManager is tied to a specific round number, so
# one ConfigManager object should be created per subsession
class ConfigManager():

    config_cache = {}
    config_mtimes = {}

    # returns a list of dicts representing the config file at a path
    # caches results, checking for file changes to update cache
    @classmethod
    def _get_config_from_path(cls, config_file_path):
        config_mtime = os.stat(os.path.abspath(config_file_path)).st_mtime
        if config_file_path not in cls.config_cache or config_mtime > cls.config_mtimes[config_file_path]:
            with open(config_file_path) as infile:
                rows = list(csv.DictReader(infile))
            cls.config_cache[config_file_path] = rows
            cls.config_mtimes[config_file_path] = config_mtime
        return cls.config_cache[config_file_path]

    # config manager takes a path to a config csv, the current round number
    # and a dict mapping config field names to their type
    def __init__(self, config_file_path, round_number, fields_dict):
        self.round_number = round_number

        rows = self._get_config_from_path(config_file_path)
        
        self.num_rounds = len(rows)
        self.round_dict = {}
        if round_number > self.num_rounds:
            return

        row = rows[round_number-1]

        for field, field_type in fields_dict.items():
            if field not in row:
                raise ValueError('input CSV is missing field "{}"'.format(field))
            
            if field_type not in (int, float, bool, str):
                raise ValueError('invalid field type: "{}"'.format(field_type.__name__))

            try:
                if field_type is int:
                    self.round_dict[field] = int(row[field])
                elif field_type is float:
                    self.round_dict[field] = float(row[field])
                elif field_type is bool:
                    self.round_dict[field] = (row[field].upper() == 'TRUE')
                elif field_type is str:
                    self.round_dict[field] = row[field]
            except ValueError:
                self.round_dict[field] = None
        
    # each of the fields specified in fields_dict can be accessed as an attribute of ConfigManager
    # for example: with a field called "period_length"
    #
    #    config = ConfigManager( ... )
    #    length = config.period_length
    def __getattr__(self, field):
        if field == 'num_rounds':
            return self.num_rounds
        if self.round_number > self.num_rounds:
            raise AttributeError('no config exists for round {}'.format(self.round_number))
        if field not in self.round_dict:
            raise AttributeError('field "{}" does not exist'.format(field))
        return self.round_dict[field]
