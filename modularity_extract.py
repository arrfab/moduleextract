#!/usr/bin/env python3

#pylint: disable=line-too-long

import argparse
import operator
import os.path

import yaml

def read_file(filename):
    ''' Read in YAML file with all its entries '''
    with open(filename, 'r') as _fd:
        raw_data = list(yaml.load_all(_fd))

    return raw_data

def find_modules_and_defaults(raw_data):
    ''' Find all modules '''
    modules = {}
    defaults = []

    for module in raw_data:
        if module['document'] == 'modulemd':
            if str(module['version']) == '1':
                raise NotImplementedError('No support for version 1 format right now')
            elif str(module['version']) == '2':
                if module['data']['name'] not in modules:
                    modules[module['data']['name']] = {}
                if module['data']['stream'] not in modules[module['data']['name']]:
                    modules[module['data']['name']][module['data']['stream']] = {}
                if module['data']['version'] not in modules[module['data']['name']][module['data']['stream']]:
                    modules[module['data']['name']][module['data']['stream']][module['data']['version']] = {}
                if module['data']['context'] not in modules[module['data']['name']][module['data']['stream']][module['data']['version']]:
                    modules[module['data']['name']][module['data']['stream']][module['data']['version']][module['data']['context']] = {}

                modules[module['data']['name']][module['data']['stream']][module['data']['version']][module['data']['context']] = get_module_v2(module['data'])
            else:
                raise NotImplementedError('Unknown metadata version %s' % module['version'])

        elif module['document'] == 'modulemd-defaults':
            if str(module['version']) == '1':
                defaults.append(get_module_defaults_v1(module['data']))
            else:
                raise NotImplementedError('Unknown metadata version %s' % module['version'])

    # sort defaults by module name and then stream
    defaults.sort(key=operator.itemgetter('module', 'stream'))

    return (modules, defaults)

def get_module_defaults_v1(module_defaults):
    ''' Extract the relevant v1 metadata for document: modulemd-defaults'''
    if 'stream' not in module_defaults:
        module_defaults['stream'] = None
    return module_defaults

def get_module_v2(module):
    ''' Extract the relevant v2 metadata for document: modulemd'''
    result = {}

    result[module['arch']] = {}
    result[module['arch']]['buildmacros'] = ''

    if 'buildopts' in module:
        if 'rpms' in module['buildopts']:
            if 'macros' in module['buildopts']['rpms']:
                result[module['arch']]['buildmacros'] = module['buildopts']['rpms']['macros']

    result[module['arch']]['dependencies'] = {}
    if 'dependencies' in module:
        if 'buildrequires' in module['dependencies']:
            result[module['arch']]['dependencies'] = module['dependencies']['buildrequires']

    result[module['arch']]['rpms'] = {}
    result[module['arch']]['rpms']['filter'] = []
    result[module['arch']]['rpms']['artifacts'] = []

    if 'filter' in module:
        if 'rpms' in module['filter']:
            result[module['arch']]['rpms']['filter'] = module['filter']['rpms']

    if 'artifacts' in module:
        if 'rpms' in module['artifacts']:
            result[module['arch']]['rpms']['artifacts'] = module['artifacts']['rpms']

    result[module['arch']]['sources'] = {}

    if 'components' in module:
        if 'rpms' in module['components']:
            for item in module['components']['rpms']:
                if 'buildorder' not in module['components']['rpms'][item]:
                    module['components']['rpms'][item]['buildorder'] = 99999999
                if 'sourcename' not in module['components']['rpms'][item]:
                    module['components']['rpms'][item]['sourcename'] = item
                result[module['arch']]['sources'][item] = module['components']['rpms'][item]

    if 'xmd' in module:
        if 'mbs' in module['xmd']:
            if 'buildrequires' in module['xmd']['mbs']:
                for req in module['xmd']['mbs']['buildrequires']:
                    if req in result[module['arch']]['dependencies']:
                        result[module['arch']]['dependencies'][req].append(module['xmd']['mbs']['buildrequires'][req]['stream'])
                        result[module['arch']]['dependencies'][req] = list(set(result[module['arch']]['dependencies'][req]))
                    else:
                        result[module['arch']]['dependencies'][req] = [module['xmd']['mbs']['buildrequires'][req]['stream']]

            if 'rpms' in module['xmd']['mbs']:
                for src in module['xmd']['mbs']['rpms']:
                    if src in result[module['arch']]['sources']:
                        result[module['arch']]['sources'][src].update(module['xmd']['mbs']['rpms'][src])
                    else:
                        result[module['arch']]['sources'][src] = module['xmd']['mbs']['rpms'][src]
                        result[module['arch']]['sources'][src]['buildorder'] = 99999999
                        result[module['arch']]['sources'][src]['sourcename'] = src

    # convert sources into sorted list
    temp_list = []
    for item in result[module['arch']]['sources']:
        temp_list.append(result[module['arch']]['sources'][item])
    result[module['arch']]['sources'] = sorted(temp_list, key=operator.itemgetter('buildorder', 'sourcename'))

    return result

if __name__ == '__main__':
    PARSER = argparse.ArgumentParser(description='Process modularity.yaml')
    PARSER.add_argument('filename', type=str, help='Name of file to parse')

    ARGS = PARSER.parse_args()

    if not os.path.exists(ARGS.filename):
        raise ValueError("%s does not exist" % ARGS.filename)

    RAW_DATA = read_file(ARGS.filename)

    MODULES = find_modules_and_defaults(RAW_DATA)

    import pprint
    pprint.pprint(MODULES)
