import pytest
from collections import OrderedDict
from flattening_ocds.schema import SchemaParser, get_property_type_set


type_string = { 'type': 'string' }


def test_get_property_type_set():
    assert get_property_type_set({'type': 'a'}) == set(['a'])
    assert get_property_type_set({'type': ['a']}) == set(['a'])
    assert get_property_type_set({'type': ['a', 'b']}) == set(['a', 'b'])


def test_filename_and_dict_error(tmpdir):
    """A value error should be raised if both schema_filename and
    root_schema_dict are supplied to SchemaParser"""
    tmpfile = tmpdir.join('test_schema.json')
    tmpfile.write('{}')
    with pytest.raises(ValueError):
        SchemaParser(schema_filename=tmpfile.strpath, root_schema_dict={})


def test_references_followed(tmpdir):
    """JSON references should be followed when a JSON file is read."""
    tmpfile = tmpdir.join('test_schema.json')
    tmpfile.write('{"a":{"$ref":"#/b"}, "b":"c"}')
    parser = SchemaParser(schema_filename=tmpfile.strpath)
    assert parser.root_schema_dict['a'] == 'c'


def test_order_preserved(tmpdir):
    """Order should be preserved when a JSON file is read."""
    tmpfile = tmpdir.join('test_schema.json')
    tmpfile.write('{"a":{}, "c":{}, "b":{}, "d":{}}')
    parser = SchemaParser(schema_filename=tmpfile.strpath)
    assert list(parser.root_schema_dict.keys()) == ['a', 'c', 'b', 'd']


def test_main_sheet_basic():
    parser = SchemaParser(root_schema_dict={
        'properties': {
            'testA': type_string,
            'testB': type_string
        }
    })
    parser.parse()
    assert set(parser.main_sheet) == set(['testA', 'testB'])


def test_main_sheet_nested():
    parser = SchemaParser(root_schema_dict={
        'properties': {
            'testA': {
                'type': 'object',
                'properties': {'testC': type_string}
            }
        }
    })
    parser.parse()
    assert set(parser.main_sheet) == set(['testA/testC'])


def test_sub_sheet():
    parser = SchemaParser(root_schema_dict={
        'properties': {
            'testA': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {'testB': type_string}
                }
            },
        }
    })
    parser.parse()
    assert set(parser.main_sheet) == set([])
    assert set(parser.sub_sheets) == set(['testA'])
    assert list(parser.sub_sheets['testA']) == ['ocid', 'testB']


def simple_array_properties(parent_name, child_name):
    return {
        'id': type_string,
        parent_name: {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {child_name: type_string}
            }
        }
    }


class TestSubSheetParentID(object):
    def test_parent_is_object(self):
        parser = SchemaParser(root_schema_dict={
            'properties': {
                'testA': {
                    'type': 'object',
                    'properties': simple_array_properties('testB', 'testC')
                }
            }
        })
        parser.parse()
        assert set(parser.main_sheet) == set(['testA/id'])
        assert set(parser.sub_sheets) == set(['testB'])
        assert list(parser.sub_sheets['testB']) == ['ocid', 'main/testA/id:testB', 'testC']

    def test_parent_is_array(self):
        parser = SchemaParser(root_schema_dict={
            'properties': {
                'testA': {
                    'type': 'array',
                    'items': {'type':'object', 'properties': simple_array_properties('testB', 'testC')}
                }
            }
        })
        parser.parse()
        assert set(parser.main_sheet) == set()
        assert set(parser.sub_sheets) == set(['testA', 'testB'])
        assert list(parser.sub_sheets['testA']) == ['ocid', 'id']
        assert list(parser.sub_sheets['testB']) == ['ocid', 'main/testA[]/id:testB', 'testC']

    def test_two_parents(self):
        parser = SchemaParser(root_schema_dict={
            'properties': OrderedDict([
                ('testA', {
                    'type': 'array',
                    'items': {'type':'object',
                        'properties': simple_array_properties('testB', 'testC')}
                }),
                ('testD', {
                    'type': 'array',
                    'items': {'type':'object',
                        'properties': simple_array_properties('testB', 'testE')}
                })
            ])
        })
        parser.parse()
        assert set(parser.main_sheet) == set()
        assert set(parser.sub_sheets) == set(['testA', 'testB', 'testD'])
        assert list(parser.sub_sheets['testA']) == ['ocid', 'id']
        assert list(parser.sub_sheets['testD']) == ['ocid', 'id']
        assert list(parser.sub_sheets['testB']) == ['ocid', 'main/testA[]/id:testB', 'main/testD[]/id:testB', 'testC', 'testE']

    def test_parent_is_object_nested(self):
        parser = SchemaParser(root_schema_dict={
            'properties': {
                'testA': {
                    'type': 'object',
                    'properties': {
                        'testB': {
                            'type': 'object',
                            'properties': simple_array_properties('testB', 'testC')
                        }
                    }
                }
            }
        })
        parser.parse()
        assert set(parser.main_sheet) == set(['testA/testB/id'])
        assert set(parser.sub_sheets) == set(['testB'])
        assert list(parser.sub_sheets['testB']) == ['ocid', 'main/testA/testB/id:testB', 'testC']


class TestSubSheetMainID(object):
    def test_parent_is_object(self):
        parser = SchemaParser(root_schema_dict={
            'properties': {
                'id': type_string,
                'testA': {
                    'type': 'object',
                    'properties': simple_array_properties('testB', 'testC')
                }
            }
        })
        parser.parse()
        assert set(parser.main_sheet) == set(['id', 'testA/id'])
        assert set(parser.sub_sheets) == set(['testB'])
        assert list(parser.sub_sheets['testB']) == ['ocid', 'main/id:testB', 'main/testA/id:testB', 'testC']

    def test_parent_is_array(self):
        parser = SchemaParser(root_schema_dict={
            'properties': {
                'id': type_string,
                'testA': {
                    'type': 'array',
                    'items': {'type': 'object',
                        'properties': simple_array_properties('testB', 'testC')}
                }
            }
        })
        parser.parse()
        assert set(parser.main_sheet) == set(['id'])
        assert set(parser.sub_sheets) == set(['testA', 'testB'])
        assert list(parser.sub_sheets['testA']) == ['ocid', 'main/id:testA', 'id']
        assert list(parser.sub_sheets['testB']) == ['ocid', 'main/id:testB', 'main/testA[]/id:testB', 'testC']

    def test_two_parents(self):
        parser = SchemaParser(root_schema_dict={
            'properties': OrderedDict([
                ('id', type_string),
                ('testA', {
                    'type': 'array',
                    'items': {'type': 'object',
                        'properties': simple_array_properties('testB', 'testC')}
                }),
                ('testD', {
                    'type': 'array',
                    'items': {'type':'object',
                        'properties': simple_array_properties('testB', 'testE')}
                })
            ])
        })
        parser.parse()
        assert set(parser.main_sheet) == set(['id'])
        assert set(parser.sub_sheets) == set(['testA', 'testB', 'testD'])
        assert list(parser.sub_sheets['testA']) == ['ocid', 'main/id:testA', 'id']
        assert list(parser.sub_sheets['testD']) == ['ocid', 'main/id:testD', 'id']
        assert list(parser.sub_sheets['testB']) == ['ocid', 'main/id:testB', 'main/testA[]/id:testB', 'main/testD[]/id:testB', 'testC', 'testE']

    def test_custom_main_sheet_name(self):
        parser = SchemaParser(
            root_schema_dict={
                'properties': {
                    'id': type_string,
                    'testA': {
                        'type': 'object',
                        'properties': simple_array_properties('testB', 'testC')
                    }
                }
            },
            main_sheet_name='custom_main_sheet_name'
        )
        parser.parse()
        assert set(parser.main_sheet) == set(['id', 'testA/id'])
        assert set(parser.sub_sheets) == set(['testB'])
        assert list(parser.sub_sheets['testB']) == ['ocid', 'custom_main_sheet_name/id:testB', 'custom_main_sheet_name/testA/id:testB', 'testC']


def test_simple_array():
    parser = SchemaParser(
        root_schema_dict={
            'properties': {
                'testA': {
                    'type': 'array',
                    'items': {
                        'type': 'string'
                    }
                }
            }
        },
        main_sheet_name='custom_main_sheet_name'
    )
    parser.parse()
    assert set(parser.main_sheet) == set(['testA:array'])


def test_references_sheet_names(tmpdir):
    """The referenced name should be used for the sheet name"""
    tmpfile = tmpdir.join('test_schema.json')
    tmpfile.write('''{
        "properties": { "testA": {
            "type": "array",
            "items": {"$ref": "#/testB"}
        } },
        "testB": { "type": "object", "properties": {"testC":{"type": "string"}} }
    }''')
    parser = SchemaParser(schema_filename=tmpfile.strpath)
    parser.parse()
    assert set(parser.sub_sheets) == set(['testB'])
    assert list(parser.sub_sheets['testB']) == ['ocid', 'testC']
