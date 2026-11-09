/* Private Linux QA only: emulate the observed UVC size negotiation on vivid.
 * Never installed by the application or exported to the physical Live card. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <linux/videodev2.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>

int ioctl(int fd, unsigned long request, ...) {
    static int (*next_ioctl)(int,unsigned long,...);
    va_list ap;va_start(ap,request);void *arg=va_arg(ap,void *);va_end(ap);
    if (!next_ioctl) next_ioctl=dlsym(RTLD_NEXT,"ioctl");
    if ((unsigned int)request==(unsigned int)VIDIOC_S_FMT && arg && getenv("ASTROALL_QA_RESIZE")) {
        struct v4l2_format *format=arg;
        if (format->type==V4L2_BUF_TYPE_VIDEO_CAPTURE && format->fmt.pix.pixelformat==V4L2_PIX_FMT_YUYV &&
            (format->fmt.pix.width==0 || (format->fmt.pix.width==1280 && format->fmt.pix.height==720))) {
            format->fmt.pix.width=640;format->fmt.pix.height=480;
            FILE *log=fopen("/tmp/uvc-size0311.log","a");
            if(log){fputs("UVC negotiated YUYV -> 640x480\n",log);fclose(log);}
        }
    }
    return next_ioctl(fd,request,arg);
}
