"""One-owner Linux serial transport, without user-space reset-line pulses."""
from pathlib import Path
import subprocess
import time

def open_mount_serial(port,baud):
    import serial
    import fcntl,termios
    existing=subprocess.run(['fuser',str(Path(port).resolve())],capture_output=True,timeout=3)
    if existing.returncode!=1: raise RuntimeError('Puerto ocupado o no comprobable. Cierra otros programas que abran directamente el Arduino.')
    # POSIX pySerial skips _update_dtr_state when dsrdtr=True. Do not drive
    # DTR low/high after the kernel opens the tty; those edges reset a Mega.
    # This is not a guarantee against an initial kernel/USB-bridge reset.
    handle=serial.Serial(port=None,baudrate=int(baud),bytesize=8,parity='N',stopbits=1,
                         timeout=.05,write_timeout=1,dsrdtr=True,rtscts=False,xonxoff=False)
    handle.port=port
    try:
        handle.open();fcntl.ioctl(handle.fileno(),termios.TIOCEXCL)
        attrs=termios.tcgetattr(handle.fileno())
        if attrs[2]&termios.HUPCL:
            attrs[2]&=~termios.HUPCL;termios.tcsetattr(handle.fileno(),termios.TCSANOW,attrs)
        time.sleep(2);handle.reset_input_buffer()
        return handle
    except Exception: handle.close();raise
