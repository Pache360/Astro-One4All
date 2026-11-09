import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('update_installer',Path(__file__).resolve().parents[1]/'system/install-update.py')
installer=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(installer)

class UpdateTests(unittest.TestCase):
    def archive(self,path,files):
        with tarfile.open(path,'w:gz') as archive:
            for name,data in files.items():
                info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;archive.addfile(info,io.BytesIO(data))

    @unittest.skipUnless(os.name=='posix','Linux symlinks')
    def test_032_repairs_absolute_logout_routes_and_keeps_other_preferences(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root';root.mkdir()
            pref=root/'home/astro/.config/lxpanel/LXDE/config';pref.parent.mkdir(parents=True)
            pref.write_text('[Command]\nLogout=lxde-logout\nTerminal=xterm\n')
            content=b'# 032\n';repair=(Path(__file__).resolve().parents[1]/'system/desktop_repair.py').read_bytes()
            files={'astroall/example.py':content,'system/desktop_repair.py':repair}
            manifest={'version':'0.3.2','architecture':'amd64','files':{k:hashlib.sha256(v).hexdigest() for k,v in files.items()}}
            archive=Path(tmp)/'032.tar.gz';self.archive(archive,dict(files,**{'manifest.json':json.dumps(manifest).encode()}))
            installer.install(archive,root)
            self.assertIn('Logout=/usr/bin/lxsession-logout',pref.read_text());self.assertIn('Terminal=xterm',pref.read_text())
            wrapper=root/'usr/local/bin/lxde-logout'
            self.assertIn('exec /usr/bin/lxsession-logout',wrapper.read_text());self.assertEqual(wrapper.stat().st_mode&0o777,0o755)
    def test_traversal_is_rejected_before_any_installation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root';root.mkdir();path=Path(tmp)/'unsafe.tar.gz';self.archive(path,{'../escape':b'bad'})
            with self.assertRaisesRegex(RuntimeError,'ruta'): installer.install(path,root)
            self.assertFalse((root/'opt/escape').exists());self.assertFalse((root/'opt/astroall-current').exists())
    def test_changed_file_fails_hash_before_switching(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root';root.mkdir();path=Path(tmp)/'bad-hash.tar.gz'
            manifest={'version':'0.3.0','architecture':'amd64','files':{'astroall/example.py':'0'*64}}
            self.archive(path,{'manifest.json':json.dumps(manifest).encode(),'astroall/example.py':b'altered'})
            with self.assertRaisesRegex(RuntimeError,'alterado'): installer.install(path,root)
            self.assertFalse((root/'opt/astroall-current').exists())
    @unittest.skipUnless(os.name=='posix','Linux symlinks')
    def test_versioned_install_preserves_old_tree_and_user_preferences(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root';root.mkdir();old=root/'opt/astroall';old.mkdir(parents=True);(old/'old.txt').write_text('0.2')
            prefs=root/'home/astro/.config/astroall';prefs.mkdir(parents=True);(prefs/'time.json').write_text('original')
            path=Path(tmp)/'good.tar.gz';content=b'# 0.3\n';manifest={'version':'0.3.0','architecture':'amd64','files':{'astroall/example.py':hashlib.sha256(content).hexdigest()}}
            self.archive(path,{'manifest.json':json.dumps(manifest).encode(),'astroall/example.py':content})
            installer.install(path,root)
            self.assertEqual((old/'old.txt').read_text(),'0.2');self.assertEqual((prefs/'time.json').read_text(),'original')
            self.assertEqual((root/'opt/astroall-current/astroall/example.py').read_bytes(),content)
            self.assertEqual((root/'opt/astroall-current').stat().st_mode&0o777,0o755)

    @unittest.skipUnless(os.name=='posix','Linux symlinks')
    def test_patch_upgrade_keeps_030_and_switches_to_031(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root';root.mkdir()
            for version in ('0.3.0','0.3.1'):
                path=Path(tmp)/(version+'.tar.gz');content=version.encode()
                manifest={'version':version,'architecture':'amd64','files':{'astroall/example.py':hashlib.sha256(content).hexdigest()}}
                self.archive(path,{'manifest.json':json.dumps(manifest).encode(),'astroall/example.py':content})
                installer.install(path,root)
            self.assertEqual((root/'opt/astroall-releases/0.3.0/astroall/example.py').read_text(),'0.3.0')
            self.assertEqual((root/'opt/astroall-current/astroall/example.py').read_text(),'0.3.1')
