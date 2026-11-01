"""Generate private Nature Remo XML from a configuration stored outside this repo.

No network access, account identifier, device address or connection code is built in.
"""
import argparse
import datetime
import json
import pathlib
import re
import xml.etree.ElementTree as ET

SERVICE = '0000ffb0-0000-1000-8000-00805f9b34fb'
CHARACTERISTIC = '0000ffb2-0000-1000-8000-00805f9b34fb'
SOURCE_DIRECTORY = pathlib.Path(__file__).resolve().parent
# Smaller values are brighter / cooler: 13 is 100% brightness and the coolest color.
DEFAULTS = {'last_color':13,'last_brightness':13}
# The lamp treats brightness raw 238 (0xEE) as OFF.
BRIGHTNESS_OFF_VALUE = 238

def validate_settings(settings):
    if not isinstance(settings,dict):raise ValueError('Settings must be a JSON object.')
    sid=settings.get('sid')
    if not isinstance(sid,str) or len(sid)!=5 or not sid.isascii() or not sid.isdigit():
        raise ValueError('A five-digit ASCII connection code is required in the private settings file.')
    for key,default in DEFAULTS.items():
        value=settings.get(key,default)
        if type(value) is not int or not 13<=value<=240:
            raise ValueError(key+' must be an integer from 13 to 240.')
    if settings.get('last_brightness',DEFAULTS['last_brightness'])==BRIGHTNESS_OFF_VALUE:
        raise ValueError('last_brightness 238 turns the lamp off; use 237 or 239.')

def build_xml(power,settings,clock=None):
    if type(power) is not bool:raise ValueError('Power must be a boolean.')
    validate_settings(settings)
    clock=clock or datetime.datetime.now()
    data=bytearray(20)
    data[:5]=settings['sid'].encode('ascii')
    data[5]=0xc0
    data[6]=settings.get('last_color',DEFAULTS['last_color']) if power else 13
    data[7]=settings.get('last_brightness',DEFAULTS['last_brightness']) if power else 255
    data[15:17]=bytes((clock.hour,clock.minute))
    root=ET.Element('macro',name='DAIKO ON' if power else 'DAIKO OFF',icon='PLAY')
    service=ET.SubElement(root,'assert-service',uuid=SERVICE)
    characteristic=ET.SubElement(service,'assert-characteristic',uuid=CHARACTERISTIC)
    ET.SubElement(characteristic,'property',name='WRITE',requirement='MANDATORY')
    ET.SubElement(root,'write',{'description':'Main light ON' if power else 'Main light OFF',
        'characteristic-uuid':CHARACTERISTIC,'service-uuid':SERVICE,
        'value':bytes(data).hex().upper(),'type':'WRITE_REQUEST'})
    ET.SubElement(root,'sleep',timeout='300')
    ET.indent(root,space='  ')
    return ET.tostring(root,encoding='unicode')+'\n'

def level_byte(percent):
    """0..100% (100 = brightest / coolest) -> raw 13..240, never the OFF value 238."""
    if type(percent) is not int or not 0<=percent<=100:
        raise ValueError('Percent must be an integer from 0 to 100.')
    raw=(227*(100-percent)+50)//100+13
    return BRIGHTNESS_OFF_VALUE-1 if raw==BRIGHTNESS_OFF_VALUE else raw

def level_filename(brightness,color,name=None):
    if name is not None and not re.fullmatch(r'[a-z0-9]+',name):
        raise ValueError('Name must use lowercase letters and digits only.')
    return f'level-b{brightness:03d}-c{color:03d}'+(f'-{name}' if name else '')+'.xml'

def build_level_xml(brightness,color,settings,clock=None):
    """ON macro fixed to brightness% and color% (coolness)."""
    values=dict(settings,last_color=level_byte(color),last_brightness=level_byte(brightness))
    root=ET.fromstring(build_xml(True,values,clock))
    root.set('name',f'DAIKO {brightness}% C{color}')
    return ET.tostring(root,encoding='unicode')+'\n'

def require_external(path):
    path=pathlib.Path(path).resolve()
    if path.is_relative_to(SOURCE_DIRECTORY):
        raise ValueError('Private settings and generated files must be outside the source directory.')
    return path

def export(settings_path,output_path):
    settings_path=require_external(settings_path)
    output_path=require_external(output_path)
    settings=json.loads(settings_path.read_text(encoding='utf-8-sig'))
    clock=datetime.datetime.now()
    documents={name:build_xml(power,settings,clock) for name,power in [('on.xml',True),('off.xml',False)]}
    output_path.mkdir(parents=True,exist_ok=True)
    for name in documents:
        if (output_path/name).exists():raise FileExistsError('Output already exists; select another private output directory.')
    written=[]
    try:
        for name,text in documents.items():
            with (output_path/name).open('x',encoding='utf-8') as file:
                written.append(output_path/name)
                file.write(text)
    except OSError:
        # Don't leave a half-finished ON/OFF pair that blocks the next run.
        for path in written:path.unlink(missing_ok=True)
        raise
    return tuple(output_path/name for name in documents)

def export_level(settings_path,output_path,brightness,color,name=None):
    settings_path=require_external(settings_path)
    output_path=require_external(output_path)
    settings=json.loads(settings_path.read_text(encoding='utf-8-sig'))
    path=output_path/level_filename(brightness,color,name)
    document=build_level_xml(brightness,color,settings)
    output_path.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as file:file.write(document)
    return path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--settings',required=True,type=pathlib.Path,help='Private JSON file outside the source directory')
    parser.add_argument('--output',required=True,type=pathlib.Path,help='Private output directory outside the source directory')
    parser.add_argument('--brightness',type=int,help='Scene brightness 0-100%% (100 = brightest). Use with --color.')
    parser.add_argument('--color',type=int,help='Scene color 0-100%% (0 = warmest, 100 = coolest). Use with --brightness.')
    parser.add_argument('--name',help='Optional lowercase name added to the scene file name, e.g. rest')
    args=parser.parse_args()
    scene=args.brightness is not None or args.color is not None
    if scene and (args.brightness is None or args.color is None):
        parser.error('--brightness and --color must be given together.')
    if args.name is not None and not scene:
        parser.error('--name is only used with --brightness and --color.')
    try:
        if scene:path=export_level(args.settings,args.output,args.brightness,args.color,args.name)
        else:export(args.settings,args.output)
    except (ValueError,OSError) as error:parser.exit(1,'Generation failed: '+str(error)+'\n')
    if scene:print(f'Generated private scene XML {path.name}. The file contains the connection code; do not publish it.')
    else:print('Generated private ON/OFF XML. The files contain the connection code; do not publish them.')

if __name__=='__main__':main()
