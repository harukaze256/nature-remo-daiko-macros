import datetime
import json
import pathlib
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
    def test_private_output_outside_source_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=pathlib.Path(folder)
            config=folder/'settings.json';config.write_text(json.dumps(self.settings),encoding='utf-8')
            outputs=generate.export(config,folder/'generated')
            self.assertEqual(len(outputs),2)
            with self.assertRaises(FileExistsError):generate.export(config,folder/'generated')
        with self.assertRaises(ValueError):generate.require_external(generate.SOURCE_DIRECTORY/'private')

if __name__=='__main__':unittest.main()
