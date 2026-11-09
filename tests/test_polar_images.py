import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,MagicMock
import numpy as np
from astroall.polar import horizon_vector
from astroall.polar_camera import (PolarSession,PolarSample,fit_axis,orientation,
    instructions,compatible,reticle,local_frame)
from astroall.solve import SolvedFrame


def rotation(axis,degrees):
    axis=np.asarray(axis,dtype=float);axis/=np.linalg.norm(axis)
    x,y,z=axis;skew=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
    theta=math.radians(degrees)
    return np.eye(3)*math.cos(theta)+(1-math.cos(theta))*np.outer(axis,axis)+math.sin(theta)*skew


def base(axis,cone=2):
    axis=np.array(axis);axis/=np.linalg.norm(axis)
    x=np.cross(axis,[0,0,1]);x/=np.linalg.norm(x)
    z=axis*math.cos(math.radians(cone))+np.cross(x,axis)*math.sin(math.radians(cone))
    return np.column_stack((x,np.cross(z,x),z))


def wcs_from_basis(basis,utc,latitude=17,longitude=-96,parity=1,scale=.008,width=1280,height=720):
    """Independent synthetic pinhole camera in a known physical orientation."""
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from astropy.wcs import WCS
    frame=local_frame(utc,latitude,longitude)
    def sky(vector):
        return SkyCoord(x=vector[0],y=vector[1],z=vector[2],representation_type='cartesian',frame=frame).icrs
    centre=sky(basis[:,2]);right=sky(basis[:,2]+basis[:,0]*1e-5)
    pa=float(centre.position_angle(right).rad)
    wcs=WCS(naxis=2);wcs.wcs.ctype=['RA---TAN','DEC--TAN'];wcs.wcs.radesys='ICRS'
    wcs.wcs.crpix=[(width+1)/2,(height+1)/2];wcs.wcs.crval=[centre.ra.deg,centre.dec.deg]
    wcs.wcs.cd=scale*np.array([[math.sin(pa),parity*math.cos(pa)],[math.cos(pa),-parity*math.sin(pa)]])
    return SolvedFrame(wcs.to_header().tostring(sep='\n',endcard=False,padding=False),width,height)


class PolarGeometryTests(unittest.TestCase):
    def test_axis_at_image_centre_and_small_cone_recovered_north_and_south(self):
        for lat,az,alt in ((17,2,15),(-35,178,36)):
            axis=horizon_vector(az,alt)
            for cone in (0,2,40):
                initial=base(axis,cone)
                bases=[rotation(axis,phase)@initial for phase in (0,20,40)]
                result=fit_axis(bases,lat)
                self.assertAlmostEqual(result['estimated_axis_alt_deg'],alt,places=7)
                self.assertAlmostEqual(result['estimated_axis_az_deg'],az,places=7)
                self.assertLess(result['fit_residual_arcmin'],1e-7)

    def test_inadequate_rotation_and_inconsistent_axes_are_rejected(self):
        axis=horizon_vector(2,16);initial=base(axis)
        with self.assertRaisesRegex(ValueError,'10°'):
            fit_axis([rotation(axis,p)@initial for p in (0,2,4)],17)
        with self.assertRaisesRegex(ValueError,'único eje'):
            fit_axis([initial,rotation(axis,25)@initial,rotation([1,0,0],15)@rotation(axis,50)@initial],17)

    def test_instruction_signs_in_both_hemispheres(self):
        for lat,az,alt,vertical,horizontal in ((17,2,15,'Sube','oeste'),(17,358,19,'Baja','este'),
                                              (-35,178,36,'Baja','oeste'),(-35,182,34,'Sube','este')):
            axis=horizon_vector(az,alt);initial=base(axis)
            result=fit_axis([rotation(axis,p)@initial for p in (0,20,40)],lat)
            text=instructions(result)
            self.assertIn(vertical,text[0]);self.assertIn(horizontal,text[1])


class PolarWcsTests(unittest.TestCase):
    def samples(self,latitude=17,parity=1):
        axis=horizon_vector(2 if latitude>0 else 178,abs(latitude)-1)
        initial=base(axis,2);samples=[]
        for i in range(3):
            utc=f'2026-11-09T04:0{i}:00+00:00';physical=rotation(axis,20*i)@initial
            solved=wcs_from_basis(physical,utc,latitude,parity=parity)
            basis=orientation(solved,utc,latitude,-96)
            samples.append(PolarSample(solved,utc,'/test/sky.jpg','main:camera',basis.tolist(),60.))
        return axis,samples

    def test_full_wcs_and_earth_rotation_recover_axis_near_pole(self):
        for lat in (17,-35):
            for parity in (1,-1):
                axis,samples=self.samples(lat,parity)
                result=fit_axis([s.basis for s in samples],lat)
                self.assertAlmostEqual(result['estimated_axis_alt_deg'],abs(lat)-1,places=3)
                self.assertAlmostEqual(result['estimated_axis_az_deg'],2 if lat>0 else 178,places=3)

    def test_adjusted_base_and_tracking_update_without_a_new_three_point_fit(self):
        axis,samples=self.samples();session=PolarSession()
        for sample in samples:session.accept(sample,(17,-96,0))
        target=np.array(horizon_vector(0,17));turn=np.cross(axis,target)
        correction=rotation(turn,math.degrees(math.acos(np.dot(axis,target))))
        physical=rotation(target,5)@correction@np.array(samples[-1].basis)
        utc='2026-11-09T04:10:00+00:00';solved=wcs_from_basis(physical,utc)
        current=PolarSample(solved,utc,'/test/new.jpg','main:camera',orientation(solved,utc,17,-96).tolist(),60.)
        session.accept(current,(17,-96,0))
        self.assertEqual(len(session.samples),3);self.assertLess(session.result['polar_error_arcmin'],.04)
        self.assertFalse(session.diagnostic()['mount_commands_sent'])
        json.dumps(session.diagnostic())

    def test_rejected_sample_keeps_previous_reference_and_solution(self):
        _,samples=self.samples();session=PolarSession();session.accept(samples[0],(17,-96,0))
        with self.assertRaisesRegex(ValueError,'Falta giro'):session.accept(samples[0],(17,-96,0))
        self.assertEqual(len(session.samples),1)
        session.accept(samples[1],(17,-96,0));session.accept(samples[2],(17,-96,0))
        original=session.result
        changed=PolarSample(samples[-1].solution,samples[-1].utc,'/other.jpg','main:camera',samples[-1].basis,61.)
        with self.assertRaisesRegex(ValueError,'DEC'):session.accept(changed,(17,-96,0))
        self.assertIs(session.result,original)
        with self.assertRaisesRegex(ValueError,'ubicación'):session.accept(samples[-1],(18,-96,0))

    def test_optics_or_camera_change_invalidates_reference(self):
        _,samples=self.samples();ref=samples[0].solution
        with self.assertRaises(ValueError):compatible(ref,wcs_from_basis(np.array(samples[0].basis),samples[0].utc,scale=.02))
        with self.assertRaises(ValueError):compatible(ref,wcs_from_basis(np.array(samples[0].basis),samples[0].utc,parity=-1))
        session=PolarSession();session.accept(samples[0],(17,-96,0))
        other=PolarSample(samples[1].solution,samples[1].utc,'/guide.jpg','guide:usb',samples[1].basis)
        with self.assertRaisesRegex(ValueError,'cámara'):session.accept(other,(17,-96,0))

    def test_polaris_reference_is_not_the_true_pole_and_roundtrip_uses_actual_wcs(self):
        axis,samples=self.samples();sample=samples[-1]
        overlay=reticle(sample.solution,sample.utc,17,-96,0,axis)
        self.assertTrue(overlay['pole']['inside']);self.assertTrue(overlay['polaris']['inside'])
        self.assertGreater(math.hypot(overlay['pole']['x']-overlay['polaris']['x'],overlay['pole']['y']-overlay['polaris']['y']),10)
        self.assertEqual(len(overlay['rings']),3)
        from astropy.wcs.utils import skycoord_to_pixel
        sky=sample.solution.sky(123.4,456.7);x,y=skycoord_to_pixel(sky,sample.solution.wcs())
        self.assertAlmostEqual(float(x),123.4,places=6);self.assertAlmostEqual(float(y),456.7,places=6)

    def test_naive_utc_and_invalid_site_rejected(self):
        with self.assertRaises(ValueError):local_frame('2026-11-09T04:00:00',17,-96)
        with self.assertRaises(ValueError):local_frame('2026-11-09T04:00:00+00:00',math.nan,-96)


class PolarCaptureTests(unittest.TestCase):
    def test_guide_camera_does_not_invent_pixel_size_or_sensor_format(self):
        from astroall.polar_capture import configuration
        settings={'clock_confirmed':True,'latitude':17,'longitude':-96,'elevation':0}
        profile={'indi_device':'Acteck','path':'/dev/by-id/usb-guide','bus':'usb2'}
        with patch('astroall.polar_capture.load_settings',return_value=settings),patch('astroall.guide_camera.profile',return_value=profile):
            config=configuration('guide','unknown','not used','',2,True)
            self.assertIsNone(config['width_deg']);self.assertEqual(config['site'],(17,-96,0))
    def test_missing_clock_or_preparation_does_not_capture(self):
        from astroall.polar_capture import configuration
        with patch('astroall.polar_capture.load_settings',return_value={'clock_confirmed':False}):
            with self.assertRaisesRegex(ValueError,'hora/ubicación'):configuration('main','APS-C Canon',50,'',2,True)
        with self.assertRaisesRegex(ValueError,'casilla'):configuration('main','APS-C Canon',50,'',2,False)

    def test_active_phd2_is_not_stopped_or_shared(self):
        from astroall.polar_capture import require_idle_guiding
        with patch('astroall.guiding.PHD2Client') as client:
            mock=client.return_value.__enter__.return_value;mock.request.return_value='Guiding'
            with self.assertRaisesRegex(RuntimeError,'Detén'):require_idle_guiding()
            mock.request.assert_called_once_with('get_app_state')

    def test_missing_solver_does_not_take_a_photo(self):
        from astroall.polar_capture import measure
        with patch('astroall.solve.solver_status',return_value={'ready':False}),patch('astroall.capture_service.capture_one') as capture:
            with self.assertRaisesRegex(RuntimeError,'índices'):measure({})
            capture.assert_not_called()


if __name__=='__main__':unittest.main()
