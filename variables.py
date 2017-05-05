import os
import re

class Variables(object):
    RE_VAR = r"^(?P<option>.*?)=(?P<value>.*)?$"
    FILE_NAME = 'variables.cfg'

    def __init__(self):
        config_file_path = self._join_path_to_script_directory(self.FILE_NAME)

        self.config = {}
        with open(config_file_path) as config_file:
            for idx, line in enumerate(config_file):
                mo = re.compile(self.RE_VAR).match(line)
                if not mo:
                    raise ValueError(FILE_NAME + ':' + str(idx) + ' illegal line pattern')    
                name, val = mo.group('option', 'value')
                self.config[name] = val

    def __getitem__(self, key):
        return self.config[key]

    def _join_path_to_script_directory(self, path):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), path)


def main():
    v = Variables()
    print(v["pushbullet_token"])
    print(v.config)

if __name__ == '__main__':
    main()