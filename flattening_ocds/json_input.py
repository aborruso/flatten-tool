"""

This file contains code that takes an OCDS JSON release ifle as input (not a
JSON schema, for that see schema.py).

"""

import json
import six
from collections import OrderedDict
from decimal import Decimal
from flattening_ocds.schema import SchemaParser
from flattening_ocds.input import path_search

BASIC_TYPES = [six.text_type, bool, int, Decimal]

class JSONParser(object):
    # Named for consistency with schema.SchemaParser, but not sure it's the most appropriate name.
    # Similarily with methods like parse_json_dict

    def __init__(self, json_filename=None, root_json_dict=None, main_sheet_name='main', schema_parser=None, root_list_path=None):
        self.sub_sheets = {}
        self.main_sheet = []
        self.sub_sheet_lines = {}
        self.main_sheet_lines = []
        self.main_sheet_name = main_sheet_name
        self.root_list_path = root_list_path
        if schema_parser:
            self.sub_sheet_mapping = {'/'.join(k.split('/')[1:]): v for k,v in schema_parser.sub_sheet_mapping.items()}
        else:
            self.sub_sheet_mapping = {}

        if json_filename is None and root_json_dict is None:
            raise ValueError('Etiher json_filename or root_json_dict must be supplied')

        if json_filename is not None and root_json_dict is not None:
            raise ValueError('Only one of json_file or root_json_dict should be supplied')
 
        if json_filename:
            with open(json_filename) as json_file:
                self.root_json_dict = json.load(json_file, object_pairs_hook=OrderedDict, parse_float=Decimal)
        else:
            self.root_json_dict = root_json_dict

    def parse(self):
        if self.root_list_path is None:
            root_json_list = self.root_json_dict
        else:
            root_json_list = path_search(self.root_json_dict, self.root_list_path.split('/'))
        for json_dict in root_json_list:
            self.parse_json_dict(json_dict, sheet=self.main_sheet, sheet_lines=self.main_sheet_lines)
    
    def parse_json_dict(self, json_dict, sheet, sheet_lines, parent_name='', flattened_dict=None, parent_id_fields=None):
        # Possibly main_sheet should be main_sheet_columns, but this is
        # currently named for consistency with schema.py
        
        parent_id_fields = parent_id_fields or OrderedDict()
        if flattened_dict is None:
            flattened_dict = {}
            top = True
        else:
            top = False

        for k, v in parent_id_fields.items():
            if k not in sheet:
                sheet.append(k)
            flattened_dict[k] = v

        if 'ocid' in json_dict:
            parent_id_fields['ocid'] = json_dict['ocid']

        if 'id' in json_dict:
            parent_id_fields[self.main_sheet_name+'/'+parent_name+'id'] = json_dict['id']


        for key, value in json_dict.items():
            if type(value) in BASIC_TYPES:
                if not parent_name+key in sheet:
                    sheet.append(parent_name+key)
                flattened_dict[parent_name+key] = value
            elif hasattr(value, 'items'):
                self.parse_json_dict(
                    value,
                    sheet=sheet,
                    sheet_lines=sheet_lines,
                    parent_name=parent_name+key+'/',
                    flattened_dict=flattened_dict,
                    parent_id_fields=parent_id_fields)
            elif hasattr(value, '__iter__'):
                if all(type(x) in BASIC_TYPES for x in value):
                    # Check for an array of BASIC types
                    # TODO Make this check the schema
                    # TODO Error if the any of the values contain the seperator
                    # TODO Support doubly nested arrays
                    sheet.append(parent_name+key)
                    flattened_dict[parent_name+key] = ';'.join(value)
                else:
                    sub_sheet_name = self.sub_sheet_mapping[key] if key in self.sub_sheet_mapping else key
                    if sub_sheet_name not in self.sub_sheets:
                        self.sub_sheets[sub_sheet_name] = []
                        self.sub_sheet_lines[sub_sheet_name] = []


                    for json_dict in value:
                        self.parse_json_dict(
                            json_dict,
                            sheet=self.sub_sheets[sub_sheet_name],
                            sheet_lines=self.sub_sheet_lines[sub_sheet_name],
                            parent_id_fields=parent_id_fields)
            else:
                raise ValueError('Unsupported type {}'.format(type(value)))
        
        if top:
            sheet_lines.append(flattened_dict)
