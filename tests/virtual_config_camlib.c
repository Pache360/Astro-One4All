/* Test-only camlib. Never installed into the Live or used for real devices.
 * Real libgphoto2 + Python configuration widgets, without USB hardware.
 */
#include <gphoto2/gphoto2-camera.h>
#include <gphoto2/gphoto2-library.h>
#include <gphoto2/gphoto2-result.h>
#include <gphoto2/gphoto2-port-result.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char shutter[32]="1/60", iso[32]="1600", target[32]="Memory card";
static int open_shutter=0;
static void trace(const char *op, const char *value) {
 const char *path=getenv("ASTROALL_TEST_CAMLIB_TRACE");
 if(path) { FILE *f=fopen(path,"a"); if(f) { fprintf(f,"%s:%s\n",op,value); fclose(f); } }
}
static int menu(CameraWidget *root, const char *name, const char *value, const char **choices) {
 CameraWidget *child; int n;
 gp_widget_new(GP_WIDGET_RADIO,name,&child);gp_widget_set_name(child,name);
 for(n=0;choices[n];n++) gp_widget_add_choice(child,choices[n]);
 gp_widget_set_value(child,value);gp_widget_set_changed(child,0);gp_widget_append(root,child);return GP_OK;
}
static int get_config(Camera *camera, CameraWidget **out, GPContext *context) {
 const char *ss[]={"bulb","30","3.2","2","1","1/60",NULL};
 const char *is[]={"100","800","1600",NULL};
 const char *ct[]={"Internal RAM","Memory card",NULL};
 const char *fmt[]={"RAW + M","cRAW + M",NULL};
 const char *mode[]={"Manual",NULL};
 const char *drive[]={"Single",NULL};
 const char *remote[]={"None","Press Half","Press Full","Release Half","Release Full","Immediate",NULL};
 if(open_shutter) { trace("read_during_bulb","rejected");return GP_ERROR_CAMERA_BUSY; }
 gp_widget_new(GP_WIDGET_WINDOW,"Virtual camera configuration",out);gp_widget_set_name(*out,"main");
 menu(*out,"shutterspeed",shutter,ss);menu(*out,"iso",iso,is);menu(*out,"capturetarget",target,ct);
 menu(*out,"imageformat","cRAW + M",fmt);menu(*out,"autoexposuremode","Manual",mode);
 menu(*out,"drivemode","Single",drive);menu(*out,"eosremoterelease","None",remote);
 trace("get_config","ok");return GP_OK;
}
static int get_single(Camera *camera,const char *name,CameraWidget **out,GPContext *context) {
 CameraWidget *root,*child;CameraWidgetType type;const char *value,*choice;int n;
 int result=get_config(camera,&root,context);if(result<0)return result;
 result=gp_widget_get_child_by_name(root,name,&child);
 if(result>=0) {
  gp_widget_get_type(child,&type);gp_widget_new(type,name,out);gp_widget_set_name(*out,name);
  for(n=0;n<gp_widget_count_choices(child);n++) {gp_widget_get_choice(child,n,&choice);gp_widget_add_choice(*out,choice);}
  gp_widget_get_value(child,&value);gp_widget_set_value(*out,value);gp_widget_set_changed(*out,0);
 }
 gp_widget_free(root);return result;
}
static int put_value(const char *name,CameraWidget *item) {
 const char *value;gp_widget_get_value(item,&value);trace(name,value);
 if(!strcmp(name,"shutterspeed"))snprintf(shutter,sizeof(shutter),"%s",value);
 if(!strcmp(name,"iso"))snprintf(iso,sizeof(iso),"%s",value);
 if(!strcmp(name,"capturetarget"))snprintf(target,sizeof(target),"%s",value);
 if(!strcmp(name,"eosremoterelease")) {
  if(!strcmp(value,"Press Full"))open_shutter=1;
  if(!strcmp(value,"Release Full"))open_shutter=0;
 }
 return GP_OK;
}
static int set_config(Camera *camera,CameraWidget *root,GPContext *context) {
 const char *names[]={"shutterspeed","iso","capturetarget","eosremoterelease",NULL};int n;
 for(n=0;names[n];n++) { CameraWidget *child;
  if(gp_widget_get_child_by_name(root,names[n],&child)>=0 && gp_widget_changed(child))put_value(names[n],child);
 }
 return GP_OK;
}
static int set_single(Camera *camera,const char *name,CameraWidget *item,GPContext *context) {
 if(getenv("ASTROALL_TEST_REJECT_SINGLE") && !strcmp(name,"shutterspeed")) { trace("set_single_shutterspeed","BAD_PARAMETERS");return GP_ERROR_BAD_PARAMETERS; }
 return put_value(name,item);
}
int camera_id(CameraText *id) { strcpy(id->text,"astroall-virtual-config-test");return GP_OK; }
static int capture_busy(Camera *camera, CameraCaptureType type, CameraFilePath *path, GPContext *context) {
 trace("capture","synthetic-busy-no-photo");
 gp_context_error(context,"PTP native test: exposure still processing");
 return GP_ERROR_CAMERA_BUSY;
}
int camera_abilities(CameraAbilitiesList *list) {
 CameraAbilities abilities;memset(&abilities,0,sizeof(abilities));strcpy(abilities.model,"Canon EOS R50");
 abilities.status=GP_DRIVER_STATUS_EXPERIMENTAL;abilities.port=GP_PORT_DISK;
 abilities.operations=GP_OPERATION_CONFIG|GP_OPERATION_CAPTURE_IMAGE;return gp_abilities_list_append(list,abilities);
}
int camera_init(Camera *camera,GPContext *context) {
 trace("init","explicit-native-test");
 if(getenv("ASTROALL_TEST_FAIL_INIT")) { gp_context_error(context,"PTP native test: camera refused initialization");return GP_ERROR; }
 camera->functions->get_config=get_config;camera->functions->set_config=set_config;
 camera->functions->get_single_config=get_single;camera->functions->set_single_config=set_single;
 camera->functions->capture=capture_busy;
 return GP_OK;
}
