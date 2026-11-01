import datetime
import json
import pathlib
import re
import tempfile
import unittest
import unittest.mock
import xml.etree.ElementTree as ET
import generate

class Tests(unittest.TestCase):
    def setUp(self):self.settings={'sid':'7'*5,'last_color':100,'last_brightness':150}
    def test_private_payload_and_clock(self):
        root=ET.fromstring(generate.build_xml(True,self.settings,datetime.datetime(2026,1,1,12,34)))
        data=bytes.fromhex(root.find('write').get('value'))
        self.assertEqual(len(data),20)
        self.assertEqual(data[:5],self.settings['sid'].encode())
        self.assertEqual(data[5:9],bytes([192,100,150,0]))
        self.assertEqual(data[15:17],bytes([12,34]))
    def test_off_and_invalid_config(self):
        data=bytes.fromhex(ET.fromstring(generate.build_xml(False,self.settings)).find('write').get('value'))
        self.assertEqual(data[6:8],bytes([13,255]))
        for settings in [{},{'sid':'X'*5},{'sid':'7'*5,'last_brightness':True},{'sid':'7'*5,'last_brightness':238}]:
            with self.assertRaises(ValueError):generate.build_xml(True,settings)
    def test_default_on_is_full_brightness_and_coolest(self):
        write=ET.fromstring(generate.build_xml(True,{'sid':'7'*5})).find('write')
        self.assertEqual(bytes.fromhex(write.get('value'))[6:8],bytes([13,13]))
        self.assertEqual(write.get('description'),'Main light ON')
    def test_failed_export_leaves_no_partial_files(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=pathlib.Path(folder)
            config=folder/'settings.json';config.write_text(json.dumps(self.settings),encoding='utf-8')
            real_open=pathlib.Path.open
            def failing_open(path,*args,**kwargs):
                if path.name=='off.xml':raise OSError('disk full')
                return real_open(path,*args,**kwargs)
            with unittest.mock.patch.object(pathlib.Path,'open',failing_open):
                with self.assertRaises(OSError):generate.export(config,folder/'generated')
            self.assertEqual(list((folder/'generated').iterdir()),[])
    def test_level_byte_direction_and_off_value(self):
        self.assertEqual([generate.level_byte(p) for p in (0,1,5,20,40,80,100)],[240,237,229,195,149,58,13])
        values=[generate.level_byte(p) for p in range(101)]
        self.assertNotIn(238,values)
        self.assertTrue(all(a>b for a,b in zip(values,values[1:])))
        for bad in (-1,101,50.0,True,'50'):
            with self.assertRaises(ValueError):generate.level_byte(bad)
    def test_level_xml_and_filename(self):
        root=ET.fromstring(generate.build_level_xml(40,20,{'sid':'7'*5}))
        self.assertEqual(root.get('name'),'DAIKO 40% C20')
        self.assertEqual(bytes.fromhex(root.find('write').get('value'))[5:8],bytes([0xc0,195,149]))
        self.assertEqual(generate.level_filename(1,5,'sleep'),'level-b001-c005-sleep.xml')
        self.assertEqual(generate.level_filename(80,100),'level-b080-c100.xml')
        for bad in ('Rest','re st','../x',''):
            with self.assertRaises(ValueError):generate.level_filename(40,20,bad)
    def test_matches_published_scene_files(self):
        files=sorted(generate.SOURCE_DIRECTORY.glob('level-*.xml'))
        self.assertTrue(files)
        for path in files:
            b,c=map(int,re.match(r'level-b(\d{3})-c(\d{3})',path.name).groups())
            published=path.read_text(encoding='utf-8')
            data=bytes.fromhex(ET.fromstring(published).find('write').get('value'))
            clock=datetime.datetime(2026,1,1,data[15],data[16])
            rebuilt=generate.build_level_xml(b,c,{'sid':data[:5].decode('ascii')},clock)
            self.assertEqual(rebuilt,published,path.name)
    def test_export_level_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=pathlib.Path(folder)
            config=folder/'settings.json';config.write_text(json.dumps({'sid':'7'*5}),encoding='utf-8')
            path=generate.export_level(config,folder/'generated',40,20,'rest')
            self.assertEqual(path.name,'level-b040-c020-rest.xml')
            with self.assertRaises(FileExistsError):generate.export_level(config,folder/'generated',40,20,'rest')
    def test_private_output_outside_source_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=pathlib.Path(folder)
            config=folder/'settings.json';config.write_text(json.dumps(self.settings),encoding='utf-8')
            outputs=generate.export(config,folder/'generated')
            self.assertEqual(len(outputs),2)
            with self.assertRaises(FileExistsError):generate.export(config,folder/'generated')
        with self.assertRaises(ValueError):generate.require_external(generate.SOURCE_DIRECTORY/'private')

if __name__=='__main__':unittest.main()
