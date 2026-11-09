"""One bounded capture report, with no images or camera serial numbers."""
from datetime import datetime, timezone
import json
import traceback
from pathlib import Path


def diagnostic_path():
    return Path.home() / '.local/state/astroall/camera-diagnostic.json'


class CaptureReport:
    def __init__(self, path=None, **request):
        from . import __version__
        from .timekeeping import utc_now
        self.path = Path(path or diagnostic_path())
        self.data = {'application_version': __version__, 'request': request,
                     'started_utc': utc_now().isoformat(),'host_started_utc':datetime.now(timezone.utc).isoformat(), 'events': []}

    def update(self, stage, **values):
        from .timekeeping import utc_now
        self.data.update(values, stage=stage, updated_utc=utc_now().isoformat())
        self.data['events'] = (self.data['events'] + [{'stage': stage, 'utc': self.data['updated_utc']}])[-40:]
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            text=json.dumps(self.data, ensure_ascii=False, indent=2)
            if len(text)>100000:
                reduced={key:value for key,value in self.data.items() if key!='camera'}
                reduced['camera_omitted']='El detalle de ajustes excedió el límite del informe.'
                text=json.dumps(reduced,ensure_ascii=False,indent=2)
            temporary.write_text(text, encoding='utf-8')
            temporary.replace(self.path)
        except OSError:
            # A logging error must never prevent the emergency shutter release.
            pass

    def failed(self, exc):
        self.update('error', failed_stage=self.data.get('stage'),
                    error=str(exc), error_type=type(exc).__name__,
                    traceback=''.join(traceback.format_exception(type(exc),exc,exc.__traceback__))[-12000:])


def read_diagnostic():
    path = diagnostic_path()
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))
