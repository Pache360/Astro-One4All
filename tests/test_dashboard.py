"""Own UI smoke tests without connected equipment."""
import tkinter as tk
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from astroall.dashboard import Dashboard, NIGHT


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk()
        self.root.withdraw()
        self.app=Dashboard(self.root)
        self.addCleanup(self.root.destroy)

    def test_polar_reference_and_mount_survive_navigation_and_refresh_stops(self):
        self.app.show('mount');hand=self.app.hand;self.addCleanup(hand.close)
        self.app.show('polar');state=self.app.polar;session=state['session']
        session.samples.append(object());state['auto']=True
        state['timer']=self.root.after(60000,lambda:None)
        with patch.object(hand,'submit') as command:
            self.app.show('atlas');self.app.show('polar')
            self.assertIs(self.app.polar,state);self.assertIs(self.app.hand,hand)
            self.assertEqual(len(session.samples),1);self.assertFalse(state['auto']);self.assertIsNone(state['timer'])
            self.app.polar_view.reset();command.assert_not_called()
        self.assertEqual(session.samples,[])

    def test_polar_failed_measurement_stops_refresh_without_retry(self):
        self.app.show('polar');state=self.app.polar;state['auto']=True
        def task(label,operation,done):done(operation());return True
        with patch('astroall.polar_capture.configuration',return_value={'site':(17,-96,0)}),\
             patch('astroall.polar_capture.measure',side_effect=RuntimeError('Sin estrellas')) as capture,\
             patch('astroall.polar_ui.save_diagnostic'),patch.object(self.app,'task',side_effect=task):
            self.app.polar_view.measure()
            capture.assert_called_once();self.assertFalse(state['auto']);self.assertEqual(state['session'].error,'Sin estrellas')

    def test_polar_controls_switch_without_leaving_unused_camera_inputs(self):
        self.app.show('polar');view=self.app.polar_view
        self.app.polar['source'].set('Cámara guía USB');view.render()
        self.assertEqual(view.columns['focal'].winfo_manager(),'')
        self.assertEqual(view.columns['field'].winfo_manager(),'pack')
        self.app.polar['source'].set('Cámara principal');view.render()
        self.assertEqual(view.columns['field'].winfo_manager(),'')
        self.assertEqual(view.columns['focal'].winfo_manager(),'pack')

    def test_pages_and_compact_geometry(self):
        for page in ('session','atlas','mount','guide','focus','polar','system'):
            self.app.show(page)
            self.root.update_idletasks()
            self.assertLessEqual(self.root.winfo_reqwidth(),1366)
            self.assertLessEqual(self.root.winfo_reqheight(),740)

    def test_expired_view_callback_does_not_stop_equipment_updates(self):
        from astroall.mount_ui import update
        self.app.show('mount');hand=self.app.hand
        self.addCleanup(hand.close)
        destroyed=tk.Label(self.app.content,text='temporary');destroyed.destroy()
        connected={'Astro One4All OAT/CONNECTION':{'values':{'CONNECT':'On'},'state':'Ok'},
                   'Astro One4All OAT/FIRMWARE_INFO':{'values':{'VERSION':'v1.13.22'}}}
        self.app.show('atlas')
        self.app.post(lambda:destroyed.configure(text='expired callback'))
        self.app.post(lambda:update(self.app,connected))
        with tempfile.TemporaryDirectory() as tmp,patch('pathlib.Path.home',return_value=Path(tmp)):
            self.app.poll()
            self.assertTrue((Path(tmp)/'.local/state/astroall/ui-errors.jsonl').exists())
        self.assertEqual(self.app.mount_badge.get(),'Montura: conectada')
        self.assertIs(self.app.hand,hand)
        self.assertTrue(any('Error de interfaz' in line for line in self.app.log_lines))

    def test_global_mount_status_survives_page_changes_and_alert_is_not_connected(self):
        from astroall.mount_ui import update
        self.app.show('mount');hand=self.app.hand;self.addCleanup(hand.close)
        connected={'OAT/CONNECTION':{'values':{'CONNECT':'On'},'state':'Ok'}}
        update(self.app,connected)
        for page in ('atlas','session','guide','mount'):
            self.app.show(page)
            self.assertIs(self.app.hand,hand)
            self.assertEqual(self.app.mount_badge.get(),'Montura: conectada')
        update(self.app,{'OAT/CONNECTION':{'values':{'CONNECT':'On'},'state':'Alert'}})
        self.assertEqual(self.app.mount_badge.get(),'Montura: desconectada')

    def test_night_toggle_and_restore(self):
        with patch.object(self.app.screen,'enable'),patch.object(self.app.screen,'restore'):
            self.app.toggle_night()
            self.assertEqual(self.root.cget('bg'),NIGHT['bg'])
            self.assertTrue(self.app.night)
            self.app.toggle_night()
            self.assertFalse(self.app.night)

    def test_atlas_adds_an_editable_capture_proposal_without_starting_hardware(self):
        from astroall.atlas_ui import to_plan,search_targets
        self.app.show('atlas');self.app.atlas['query'].set('M31');search_targets(self.app)
        with patch.object(self.app,'task') as task:
            to_plan(self.app)
            task.assert_not_called()
        self.assertEqual(self.app.current_page,'session')
        self.assertTrue(self.app.plan_targets)
        self.assertTrue(self.app.sequence['goto'].get())
        self.assertGreater(int(self.app.sequence['count'].get()),10)
        self.assertEqual(self.app.sequence['iso'].get(),'800')
        self.assertFalse(self.app.sequence['guide'].get())
        self.assertFalse(self.app.busy)

    def test_manual_focal_survives_atlas_navigation_and_plan_has_its_own_field(self):
        from astroall.atlas_ui import search_targets,to_plan
        self.app.show('atlas');self.app.atlas['query'].set('M31');search_targets(self.app)
        self.app.atlas['focal'].set('50');self.app.show('system');self.app.show('atlas');self.root.update_idletasks()
        self.assertEqual(self.app.atlas['focal'].get(),'50')
        to_plan(self.app);prepared=self.app.sequence['field_deg'].get()
        self.assertTrue(self.app.sequence['jpg_correct'].get());self.assertFalse(self.app.sequence['guide'].get())
        self.app.show('atlas');self.app.atlas['focal'].set('250')
        self.assertEqual(self.app.sequence['field_deg'].get(),prepared)

    def test_clear_atlas_target_keeps_capture_settings_and_mount_owner(self):
        from astroall.atlas_ui import search_targets,to_plan
        from astroall.session_ui import clear_target
        self.app.show('atlas');self.app.atlas['query'].set('M31');search_targets(self.app);to_plan(self.app)
        s=self.app.sequence;blocks=list(s['blocks']);values={k:s[k].get() for k in ('count','exposure','iso','delay')}
        self.app.show('mount');hand=self.app.hand;self.addCleanup(hand.close);self.app.show('session')
        self.app.busy=True;targets=list(self.app.plan_targets)
        self.assertFalse(clear_target(self.app));self.assertEqual(self.app.plan_targets,targets)
        self.app.busy=False
        with patch.object(hand,'submit') as movement,patch.object(self.app,'task') as task:
            self.assertTrue(clear_target(self.app));movement.assert_not_called();task.assert_not_called()
        self.assertEqual(self.app.plan_targets,[]);self.assertIsNone(self.app.selected_target)
        self.assertFalse(s['goto'].get());self.assertFalse(s['jpg_correct'].get());self.assertEqual(s['framing'],{})
        self.assertEqual(s['blocks'],blocks);self.assertEqual({k:s[k].get() for k in values},values)
        self.assertIs(self.app.hand,hand)

    def test_short_camera_test_does_not_execute_the_loaded_atlas_plan(self):
        from astroall.atlas_ui import search_targets,to_plan
        self.app.show('atlas');self.app.atlas['query'].set('M31');search_targets(self.app);to_plan(self.app)
        targets=list(self.app.plan_targets)
        with patch('astroall.dashboard.messagebox.askyesno',return_value=True),patch('astroall.capture_service.capture_one') as capture,patch.object(self.app,'task') as task,patch('astroall.session_ui.execute') as plan:
            self.app.test_camera(False);task.call_args.args[1]()
            self.assertEqual(capture.call_args.args[1],1);plan.assert_not_called()
        self.assertEqual(self.app.plan_targets,targets)

    def test_rounded_capture_button_is_keyboard_accessible_and_honors_disabled(self):
        from astroall.ui_widgets import RoundedButton
        calls=[];button=self.app.button(self.app.content,'Capturar',lambda:calls.append('shot'),primary=True)
        self.assertIsInstance(button,RoundedButton);self.assertEqual(button.cget('takefocus'),'1')
        button.state(['disabled']);button.invoke();self.assertEqual(calls,[])
        button.state(['!disabled']);button.invoke();self.assertEqual(calls,['shot'])
        button.configure(text='Otra toma',command=lambda:calls.append('next'));button.invoke()
        self.assertEqual(calls,['shot','next'])

    def test_system_selection_never_starts_optional_equipment(self):
        from astroall.equipment_ui import save_selection
        self.app.show('atlas');self.app.atlas['guided'].set(True)
        self.app.sequence['guide'].set(True);self.app.sequence['dither'].set('2')
        self.app.show('system')
        with tempfile.TemporaryDirectory() as tmp,patch('pathlib.Path.home',return_value=Path(tmp)),patch('astroall.camera.open_camera') as camera,patch('astroall.guiding.PHD2Client') as phd:
            self.assertTrue(save_selection(self.app));camera.assert_not_called();phd.assert_not_called()
        self.assertFalse(self.app.sequence['guide'].get());self.assertEqual(self.app.sequence['dither'].get(),'0')
        self.assertFalse(self.app.atlas['guided'].get())

    def test_mount_profile_change_is_blocked_while_connection_stays_alive(self):
        from unittest.mock import MagicMock
        from astroall.mount_profiles import create,load
        from astroall.mount_profiles_ui import manager
        from astroall.ui_widgets import RoundedButton
        self.app.hand=MagicMock();self.app.hand.client=object();self.app.hand.connecting=False
        active=self.app.hand.client
        with tempfile.TemporaryDirectory() as tmp,patch('pathlib.Path.home',return_value=Path(tmp)):
            create('OAT MKS','MKS Gen L v2.1',{'driver':'indi_astroall_oat','device':'Astro One4All OAT','port':'/dev/ttyUSB1','baud':'38400'})
            manager(self.app)
            def children(widget):
                for child in widget.winfo_children():yield child;yield from children(child)
            buttons=[w for w in children(self.root) if isinstance(w,RoundedButton) and w.text=='Activar perfil seleccionado']
            buttons[0].invoke()
            self.assertEqual(load()['selected'],'default');self.assertIs(self.app.hand.client,active)
            self.app.hand.submit.assert_not_called()

    def test_empty_preview_does_not_attempt_camera_access(self):
        with patch('astroall.dashboard.open_camera') as camera:
            self.app.solve_current()
            camera.assert_not_called()
            self.assertIsNone(self.app.preview_path)

    def test_power_dialog_does_not_interrupt_running_capture(self):
        self.app.busy=True
        with patch('astroall.dashboard.messagebox.showinfo') as message,patch('subprocess.Popen') as process:
            self.app.power_dialog()
        message.assert_called_once();process.assert_not_called()

    def test_capture_error_is_visible_and_not_replaced_by_task_finished(self):
        self.app.busy=True
        self.app.messages.put(('error','El controlador no anuncia Release Full'))
        self.app.messages.put(('done',None))
        with patch('astroall.dashboard.messagebox.showerror') as dialog:
            self.app.poll()
        self.assertIn('Release Full',dialog.call_args.args[1])
        self.assertIn('No se completó',self.app.status.get())
        self.assertFalse(self.app.busy)

    def test_error_diagnostic_can_be_saved_without_running_equipment_scan(self):
        import json
        self.app.last_task_error='USB busy'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'diagnostic.json'
            with patch('astroall.dashboard.filedialog.asksaveasfilename',return_value=str(path)),patch('astroall.camera_diagnostic.read_diagnostic',return_value={'stage':'error'}):
                self.app.export_diagnostic()
            data=json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(data['last_error'],'USB busy');self.assertEqual(data['last_capture']['stage'],'error')

    def test_jpeg_preview_is_red_only_in_night_mode(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'preview.jpg'
            Image.new('RGB',(50,50),(30,180,250)).save(path)
            self.app.preview_path=str(path)
            with patch.object(self.app.screen,'enable'):
                self.app.toggle_night()
                self.root.update_idletasks()
                self.app.render_preview()
            photo=self.app.preview_photo
            rgb=self.root.tk.call(str(photo),'get',20,20)
            self.assertGreater(rgb[0],rgb[1])
            self.assertGreater(rgb[0],rgb[2])


if __name__=='__main__': unittest.main()
