from contextlib import nullcontext
from datetime import datetime,timezone
from pathlib import Path
import unittest
from unittest.mock import patch
from astroall.session import recenter
from astroall.sky import Site,eod_position
from astroall.solve import Position,separation_arcsec
from astroall.geometry import offset

class Mount:
    def __init__(self,position): self.position=position;self.moves=[];self.aborts=0
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def get(self,*args): return {'values':{'RA':self.position.ra_deg/15,'DEC':self.position.dec_deg}}
    def collect(self,*args): pass
    def wait_slew(self,*args): return {}
    def goto_eod(self,device,ra,dec): self.position=Position(ra*15,dec);self.moves.append(self.position)
    def abort(self,*args): self.aborts+=1

class CenteringTests(unittest.TestCase):
    def test_capture_solve_correct_and_verify_without_sync(self):
        try: import astropy
        except ImportError: self.skipTest('Astropy included in the Live image')
        site=Site(17,-96);target=Position(10,20);observed=offset(target,-.1,.06)
        mount=Mount(eod_position(observed,site));solutions=iter([observed,target]);shots=[];events=[]
        def capture(*args): shots.append(args);return {'jpeg':'frame.jpg'}
        with patch('astroall.session.load_settings',return_value={'clock_confirmed':True,'latitude':17,'longitude':-96}),patch('astroall.session.profile',return_value={'device':'Simulated OAT'}),patch('astroall.session.visibility',return_value={'alt_deg':40}):
            result=recenter(target,5,capture=capture,solver=lambda *_:next(solutions),client_factory=lambda:mount,emit=events.append)
        self.assertTrue(result['centered']);self.assertEqual(len(mount.moves),1);self.assertEqual(len(shots),2)
        self.assertLess(separation_arcsec(mount.moves[0],eod_position(target,site)),.1)
        self.assertEqual(events[-1]['error_arcsec'],0)
    def test_out_of_bound_solve_never_moves_mount(self):
        try: import astropy
        except ImportError: self.skipTest('Astropy included in the Live image')
        mount=Mount(Position(20,20))
        with patch('astroall.session.load_settings',return_value={'clock_confirmed':True,'latitude':17,'longitude':-96}),patch('astroall.session.profile',return_value={'device':'Simulated OAT'}),patch('astroall.session.visibility',return_value={'alt_deg':40}):
            with self.assertRaisesRegex(ValueError,'excede'):
                recenter(Position(50,20),5,capture=lambda *_:{'jpeg':'frame.jpg'},solver=lambda *_:Position(20,20),client_factory=lambda:mount)
        self.assertFalse(mount.moves)
