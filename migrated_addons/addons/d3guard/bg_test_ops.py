'''
Created on Feb 19, 2019

@author: Patrick
https://stackoverflow.com/questions/1977362/how-to-create-module-wide-variables-in-python

'''
# System imports
from os.path import join, dirname, abspath, basename
import platform
import math
import time

# Blender imports
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from bpy.types import Operator
from bpy.props import FloatProperty, BoolProperty, IntProperty, EnumProperty
from mathutils import Color, Vector, Matrix
# Addon imports
#from bg_processing.classes.JobManager import JobManager
from submodules.back_proc.classes import JobManager

from common_utilities import get_settings
#import tracking
import bg_status

#get the location osf the scripts
jobs_path = join(dirname(abspath(__file__)), "bg_scripts")
splint_shell_job = join(jobs_path, "bg_splint_shell.py")
min_thick_job = join(jobs_path, "bg_min_thickness.py")
refractory_model_job = join(jobs_path, "bg_refractory_model.py")
dynacmic_surface_job = join(jobs_path, "bg_dynamic_surface.py")


import splint_cache

#all the ops can share access to this dictionary
#The reason we do this is because the Blender Collection/Property Group gets fubarred by undo/redo operators
#this just helps our specialized system know whether or not to attempt processing a job

class JobsBox:
    def __init__(self):
        self.jobs_started = {}
        self.jobs_started['MINIMUM THICKNESS'] = False
        self.jobs_started['REFRACTORY MODEL'] = False
        self.jobs_started['SPLINT SHELL'] = False
        self.jobs_started['DYNAMIC SURFACE'] = False
        
        self.jobs_complete = {}
        self.jobs_complete['MINIMUM THICKNESS'] = False
        self.jobs_complete['REFRACTORY MODEL'] = False
        self.jobs_complete['SPLINT SHELL'] = False
        self.jobs_complete['DYNAMIC SURFACE'] = False
        
    
        self.force_stop_director = False
        self.director_running = False
        
    def clear_status(self):
        self.jobs_started['MINIMUM THICKNESS'] = False
        self.jobs_started['REFRACTORY MODEL'] = False
        self.jobs_started['SPLINT SHELL'] = False
        self.jobs_started['DYNAMIC SURFACE'] = False
        
        self.jobs_complete['MINIMUM THICKNESS'] = False
        self.jobs_complete['REFRACTORY MODEL'] = False
        self.jobs_complete['SPLINT SHELL'] = False
        self.jobs_complete['DYNAMIC SURFACE'] = False
        

#get a single instance of the Jobs Box
_job_status = JobsBox()

global jobs_started
jobs_started = {}
jobs_started['MINIMUM THICKNESS'] = False
jobs_started['REFRACTORY MODEL'] = False
jobs_started['SPLINT SHELL'] = False
jobs_started['DYNAMIC SURFACE'] = False

global jobs_complete
jobs_complete = {}
jobs_complete['MINIMUM THICKNESS'] = False
jobs_complete['REFRACTORY MODEL'] = False
jobs_complete['SPLINT SHELL'] = False
jobs_complete['DYNAMIC SURFACE'] = False

global force_stop_director 
force_stop_director = False  #this flag used to stop the job manager modal
global director_running
director_running = False


def clear_dicts():
    #nonlocal?
    print('CLEARING THE STATUS VARIABLES')

    bg_status.force_stop_director = True
    bg_status.director_running = False
    
    bg_status.min_thick_start = False
    bg_status.refractory_start = False
    bg_status.shell_start = False
    bg_status.dyn_surface_start = False
    
    bg_status.min_thick_complete = False
    bg_status.refractory_complete = False
    bg_status.shell_complete = False
    bg_status.dyn_surface_complete = False
    
    
    print('\n\n\n')
    
class D3SSPLINT_OT_bg_job_director(Operator):
    """ Keeps the bg jobs getting started if/when they can"""
    bl_idname = "d3splint.bg_job_director"
    bl_label = "Start Background Operations"
    bl_description = "Adds a job"
    bl_options = {'REGISTER'}

    ################################################
    # Blender Operator methods
    
    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """        
        return len(context.scene.odc_splints) != 0

    def execute(self, context):
        if bpy.data.filepath == "":
            self.report({"WARNING"}, "Please save the file first")
            return {"CANCELLED"}
        
        if bg_status.director_running:
            self.report({"WARNING"}, "Job director is allegedly running!")
            return {"CANCELLED"}    
        
        global force_stop_director  #is this needed?
        force_stop_director = False
        _job_status.force_stop_director = False
        bg_status.force_stop_director = False
        
        global director_running
        director_running = True
        _job_status.director_running = True
        bg_status.director_running = True
        
        n = context.scene.odc_splint_index
        self.splint = context.scene.odc_splints[n]
        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, context.window)
        self._handle = wm.modal_handler_add(self)  #TODO make sure to remove handlers and timers later
        self.last_time = time.time()
        return{"RUNNING_MODAL"}

    def eligible_jobs(self):
        
        el_jobs = set()
        jobs_todo = set()
        
        shell_scaff = 'Shell Patch' in bpy.data.objects
        ref_scaf = 'Refractory Scaffold' in bpy.data.objects
        dyn_surface = 'Dynamic Occlusal Surface' in bpy.data.objects
        
        #min thickness conditions
        #c0 = self.splint.min_thick_in_progress == False
        #c1 = self.splint.min_thick == False
        
        c0 = bg_status.min_thick_start == False
        c1 = bg_status.min_thick_complete == False
        
        if c0 and c1 and shell_scaff:
            el_jobs.add('MINIMUM THICKNESS')
        
        if c1:
            jobs_todo.add('MINIMUM THICKNESS')
        
        #Splint Shell Condiditions
        #c0 = self.splint.splint_shell_in_progress == False
        #c1 = self.splint.splint_shell == False
        
        c0 = bg_status.shell_start == False
        c1 = bg_status.shell_complete == False
        
        if c0 and c1 and shell_scaff:
            el_jobs.add('SPLINT SHELL')
        
        if c1:
            jobs_todo.add('SPLINT SHELL')
            
        #Refractory Shell Condiditions
        #c0 = self.splint.refractory_in_progress == False
        #c1 = self.splint.refractory_model == False
        c0 = bg_status.refractory_start == False
        c1 = bg_status.refractory_complete == False
        
        if c0 and c1 and ref_scaf:
            el_jobs.add('REFRACTORY MODEL')            
        if c1:
            jobs_todo.add('REFRACTORY MODEL')
            
        #Dynamic Surface Condiditions
        #c0 = self.splint.dynamic_surface_in_progress == False
        #c1 = self.splint.dynamic_surface == False
        c0 = bg_status.dyn_surface_start == False
        c1 = bg_status.dyn_surface_complete == False
        c2 = 'Articulator' in bpy.data.objects
        if c0 and c1 and c2 and dyn_surface:
            el_jobs.add('DYNAMIC SURFACE')
            
        if c1:
            jobs_todo.add('DYNAMIC SURFACE')
            
            
        return jobs_todo, el_jobs   
               
    def modal(self, context, event):
        if event.type == "TIMER":  #AHHHH, there may be multiple timers!
            dt = time.time() - self.last_time
            if dt < 2.0:  #prevent other timers from messing us up
                return {'PASS_THROUGH'}
            
            
            global force_stop_director  #is this needed?
            global director_running
            if bg_status.force_stop_director:
                print('\n\n')
                print('BG Job Director FOCED STOP!')
                print('\n\n')
                context.window_manager.event_timer_remove(self._timer)
                director_running = False
                force_stop_director = False
                
                bg_status.director_running = False
                bg_status.force_stop_director = False
                
                return {'FINISHED'}
        
            self.last_time = time.time()
            print('BG Job Director still running')
            #check for eligible jobs
            jobs_todo, el_jobs = self.eligible_jobs()

            #print('Jobs Started')
            #print(_job_status.jobs_started)
            #print('Jobs Complete')
            #print(_job_status.jobs_complete)
            #print('Jobs todo')
            #print(jobs_todo)
            #print('Eligible Jobs')
            #print(el_jobs)
            
            #if all eligigble jobs compelte.....quit
            if len(jobs_todo) == 0:
                print('\n\n')
                print('BG Job Director FINISHED!')
                print('\n\n')
                context.window_manager.event_timer_remove(self._timer)
                director_running = False
                return {'FINISHED'}
            
            
            if 'REFRACTORY MODEL' in el_jobs:
                try:
                    bpy.ops.d3splint.background_refractory_model(b_radius = self.splint.undercut_value,
                                                             c_radius = self.splint.passive_value,
                                                             d_radius = self.splint.drillcomp_value,
                                                             use_drillcomp = self.splint.use_drillcomp)
                except:
                    pass
                
                return {'PASS_THROUGH'}
            
            
            if 'SPLINT SHELL' in el_jobs:
                #specifiy values from actual splint instance
                try:
                    bpy.ops.d3splint.background_splint_shell(radius = self.splint.shell_thickness_value)
                except:
                    print('unable to add splint shell why!?')
                    pass
                
                return {'PASS_THROUGH'}
            
            if 'MINIMUM THICKNESS' in el_jobs:
                #specifiy values from actual splint instance
                try:
                    bpy.ops.d3splint.background_min_thickness(radius = self.splint.minimum_thickness_value)
                except:
                    pass
                
                return {'PASS_THROUGH'}
            
            if 'DYNAMIC SURFACE' in el_jobs:
                #specifiy values from actual splint instance
                if 'Mac' in platform.system():
                    print('curious if this works for mac for the drivers')
                
                try:
                    bpy.ops.d3splint.bg_functional_surface()
                except:
                    pass
                
                return {'PASS_THROUGH'}
            
        return {"PASS_THROUGH"}

    def cancel(self, context):
        pass
    
class D3SSPLINT_OT_bg_stop_job_director(Operator):
    """ Keeps the bg jobs getting started if/when they can"""
    bl_idname = "d3splint.stop_bg_job_director"
    bl_label = "Stop Background Operations"
    bl_description = "Stops The job director, remaining jobs will finish"
    bl_options = {'REGISTER'}

    ################################################
    # Blender Operator methods
    
    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        return len(context.scene.odc_splints)

    def execute(self, context):
        
        if bg_status.force_stop_director == True:
            self.report({'WARNING'}, 'The Job Director is already stopped')
            return {'CANCELLED'}
        
        print('Signal sent to stop the director')
        bg_status.force_stop_director = True
        
        #director running = False must be set by job director when it stops
        return{"RUNNING_MODAL"}
        
           
class D3SSPLINT_OT_min_thickness_background(Operator):
    """ Makes a minimum thickness shell """
    bl_idname = "d3splint.background_min_thickness"
    bl_label = "Add Job Min Thickness"
    bl_description = "Adds a job"
    bl_options = {'REGISTER'}

    ################################################
    # Blender Operator methods
    radius = FloatProperty(default = 1, min = .6, max = 4, description = 'Minimum thickness of splint', name = 'Thickness')
    resolution = FloatProperty(default = .75, description = '0.5 to 1.5 seems to be good')
    #old = BoolProperty(default = True)
    
    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        return True

    def execute(self, context):
        if bpy.data.filepath == "":
            self.report({"WARNING"}, "Please save the file first")
            return {"CANCELLED"}
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        self.splint = splint
        
        pdata = {}
        pdata['radius'] = self.radius
        pdata['resolution'] = self.resolution
        pdata['trimmed_model_name'] = 'Shell Patch'
        
        #splint.min_thick_in_progress = True
        #_job_status.jobs_started['MINIMUM THICKNESS'] = True
        bg_status.min_thick_start = True
                
        jobAdded, msg = self.JobManager.add_job(self.job["name"],
                                                    timeout = 30,
                                                    script = self.job["script"],
                                                    use_blend_file=True, 
                                                    passed_data=pdata)
        if not jobAdded:
            #_job_status.jobs_started['MINIMUM THICKNESS'] = False
            bg_status.min_thick_start = False
            self.report({"WARNING"}, "unable to add Minimum Thickness job right now")
            raise Exception(msg)
            #splint.min_thick_in_progress = False
            return {"CANCELLED"}
        
        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, context.window)
        wm.modal_handler_add(self)
        return{"RUNNING_MODAL"}

    def finish(self, context):
        
        mat = bpy.data.materials.get("Blockout Material")
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name="Blockout Material")
            mat.diffuse_color = Color((0.8, .1, .1))
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .4
            
        new_ob = bpy.data.objects.get('Minimum Thickness')
        if new_ob.name not in context.scene.objects:
            context.scene.objects.link(new_ob)
        
        if mat.name not in new_ob.data.materials:
            new_ob.data.materials.append(mat)
        new_ob.show_transparent = True
        new_ob.hide = True  #bring them in hidden
        
        bme= bmesh.new()
        bme.from_mesh(new_ob.data)
        bme.verts.ensure_lookup_table()
        bme.edges.ensure_lookup_table()
        bme.faces.ensure_lookup_table()
        
        splint_cache.write_min_cache(bme)
        #Mark the tasks complete!
        self.splint.min_thick = True
        bpy.ops.ed.undo_push()  #make it stick
        #self.splint.min_thick_in_progress = False
        #_job_status.jobs_started['MINIMUM THICKNESS'] = False
        #_job_status.jobs_complete['MINIMUM THICKNESS'] = True
        bg_status.min_thick_start = False
        bg_status.min_thick_complete = True
        context.window_manager.event_timer_remove(self._timer)
        
    def modal(self, context, event):
        if event.type == "TIMER":
            self.JobManager.process_job(self.job["name"], debug_level=3)
            
            if self.JobManager.job_complete(self.job["name"]):
                self.report({"INFO"}, "Background process '{job_name}' was finished".format(job_name=self.job["name"]))
                retrieved_data_blocks = self.JobManager.get_retrieved_data_blocks(self.job["name"])
                retrieved_python_data = self.JobManager.get_retrieved_python_data(self.job["name"])
                print(retrieved_data_blocks.objects)
                print(retrieved_python_data)             
                self.finish(context)
                return {"FINISHED"}
            
            elif self.JobManager.job_dropped(self.job["name"]):
                if self.JobManager.job_timed_out(self.job["name"]):
                    self.report({"WARNING"}, "Background process '{job_name}' timed out".format(job_name=self.job["name"]))
                elif self.JobManager.job_killed(self.job["name"]):
                    self.report({"WARNING"}, "Background process '{job_name}' was killed".format(job_name=self.job["name"]))
                else:
                    self.report({"WARNING"}, "Background process '{job_name}' failed".format(job_name=self.job["name"]))
                    errormsg = self.JobManager.get_issue_string(self.job["name"])
                    print(errormsg)
                bg_status.min_thick_start = False
                #_job_status.jobs_started['MINIMUM THICKNESS'] = False
                context.window_manager.event_timer_remove(self._timer)
                return {"CANCELLED"}
        return {"PASS_THROUGH"}

    def cancel(self, context):
        self.JobManager.kill_job(self.job["name"])
        bg_status.min_thick_start = False
        context.window_manager.event_timer_remove(self._timer)
    ################################################
    # initialization method

    def __init__(self):
        script = min_thick_job
        #self.job = min_thick_job
        self.job = {"name":basename(script), "script":script}
        self.JobManager = JobManager.get_instance(-1)
        self.JobManager.max_workers = 5

    ###################################################

class D3SPLINT_OT_splint_background_functional_surface(bpy.types.Operator):
    """Create functional surface using envelope of motion on articulator"""
    bl_idname = "d3splint.bg_functional_surface"
    bl_label = "BG Functional Surface"
    bl_options = {'REGISTER', 'UNDO'}
    
    modes = ['PROTRUSIVE', 'RIGHT_EXCURSION', 'LEFT_EXCURSION', 'RELAX_RAMP', '3WAY_ENVELOPE','FULL_ENVELOPE']
    mode_items = []
    for m in modes:
        mode_items += [(m, m, m)]
        
    mode = EnumProperty(name = 'Articulator Mode', items = mode_items, default = 'FULL_ENVELOPE')
    resolution = IntProperty(name = 'Resolution', description = "Number of steps along the condyle to create surface.  10-40 is reasonable.  Larger = Slower", default = 20)
    range_of_motion = FloatProperty(name = 'Range of Motion', min = 2, max = 8, description = 'Distance to allow translation down condyles', default = 6.0)
    use_relax = BoolProperty(name = 'Use Relax Ramp', default = False)
    relax_ramp_length = FloatProperty(name = 'Relax Ramp Length', min = 0.1, max = 2.0, description = 'Length of condylar path to animate, typically .2 to 1.0', default = 0.5)
    
    @classmethod
    def poll(cls, context):
        #conditions
        c1 = 'Articulator' in context.scene.objects
        c2 = 'Dynamic Occlusal Surface' in context.scene.objects
        c3 = 'Splint Shell' in context.scene.objects
        return c1 & c2 & c3
    
    def invoke(self, context, event):
        
        settings = get_settings()
        
        self.resolution = settings.def_condylar_resolution
        self.range_of_motion = settings.def_range_of_motion
        
        return context.window_manager.invoke_props_dialog(self)
    
    def finish(self, context):
        new_ob = bpy.data.objects.get('BG Dyn Plane')
        old_ob = bpy.data.objects.get('Dynamic Occlusal Surface')
        
        old_ob.data = new_ob.data
        bpy.data.objects.remove(new_ob)
        #old_ob.hide = False

        #tracking.trackUsage("D3Splint:CreateSurface",None)
        bpy.context.scene.frame_current = -1
        bpy.context.scene.frame_current = 0
        self.splint.ops_string += 'AnimateArticulator:'
        self.splint.dynamic_surface = True
        bpy.ops.ed.undo_push()
        #self.splint.dynamic_surface_in_progress = False
        #_job_status.jobs_complete['DYNAMIC SURFACE'] = True
        #_job_status.jobs_started['DYNAMIC SURFACE'] = False
        bg_status.dyn_surface_complete = True
        bg_status.dyn_surface_start = False
        
        
        
        #bpy.context.space_data.show_backface_culling = False  
        return 
    
    def execute(self, context):
        splint = context.scene.odc_splints[0]
        Model = bpy.data.objects.get(splint.opposing)
        Master = bpy.data.objects.get(splint.model)
        
        self.splint = splint
        Art = bpy.data.objects.get('Articulator')
        
        if Model == None:
            self.report({'ERROR'}, 'No Opposing Model')
            return {'CANCELLED'}
        
        if Art == None:
            self.report({'ERROR'}, 'You need to Generate Articulator or set initial articulator values first')
            return {'CANCELLED'}
        
        #filter the occlusal surface verts
        Plane = bpy.data.objects.get('Dynamic Occlusal Surface')
        if Plane == None:
            self.report({'ERROR'}, 'Need to mark occlusal curve on opposing object to get reference plane')
            return {'CANCELLED'}
        
        pdata = {}
        pdata['opposing_name'] = splint.opposing
        pdata['jaw_type'] = splint.jaw_type
        pdata['ops_string'] = splint.ops_string
        
        bpy.ops.d3splint.articulator_mode_set(mode = self.mode, 
                                              resolution = self.resolution, 
                                              range_of_motion = self.range_of_motion, 
                                              use_relax = self.use_relax,
                                              relax_ramp_length = self.relax_ramp_length)
        

        #self.splint.dynamic_surface_in_progress = True
        #_job_status.jobs_started['DYNAMIC SURFACE'] = True
        bg_status.dyn_surface_start = True
        jobAdded, msg = self.JobManager.add_job(self.job["name"], 
                                                timeout=60, 
                                                script=self.job["script"], 
                                                use_blend_file=True, 
                                                passed_data=pdata)
        if not jobAdded:
            #_job_status.jobs_started['DYNAMIC SURFACE'] = False
            bg_status.dyn_surface_start = False
            raise Exception(msg)
            return {"CANCELLED"}
        
        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, context.window)
        wm.modal_handler_add(self)  
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        if event.type == "TIMER":
            self.JobManager.process_job(self.job["name"], debug_level=3)
            
            if self.JobManager.job_complete(self.job["name"]):
                self.report({"INFO"}, "Background process '{job_name}' was finished".format(job_name=self.job["name"]))
                retrieved_data_blocks = self.JobManager.get_retrieved_data_blocks(self.job["name"])
                retrieved_python_data = self.JobManager.get_retrieved_python_data(self.job["name"])
                print(retrieved_data_blocks.objects)
                print(retrieved_python_data)             
                self.finish(context)
                return {"FINISHED"}
            
            elif self.JobManager.job_dropped(self.job["name"]):
                if self.JobManager.job_timed_out(self.job["name"]):
                    self.report({"WARNING"}, "Background process '{job_name}' timed out".format(job_name=self.job["name"]))
                elif self.JobManager.job_killed(self.job["name"]):
                    self.report({"WARNING"}, "Background process '{job_name}' was killed".format(job_name=self.job["name"]))
                else:
                    self.report({"WARNING"}, "Background process '{job_name}' failed".format(job_name=self.job["name"]))
                    errormsg = self.JobManager.get_issue_string(self.job["name"])
                    print(errormsg)
                #_job_status.jobs_started['DYNAMIC SURFACE'] = False
                bg_status.dyn_surface_start = False
                context.window_manager.event_timer_remove(self._timer)
                return {"CANCELLED"}
        return {"PASS_THROUGH"}

    def cancel(self, context):
        self.JobManager.kill_job(self.job)
        #self.splint.dynamic_surface_in_progress = False
        #jobs_started['DYNAMIC SURFACE'] = False
        bg_status.dyn_surface_start = False
        context.window_manager.event_timer_remove(self._timer)
    ################################################
    # initialization method

    def __init__(self):
        script = dynacmic_surface_job
        self.job = {"name":basename(script), "script":script}
        self.JobManager = JobManager.get_instance(-1)
        self.JobManager.max_workers = 5

class D3SSPLINT_OT_refractory_model_background(Operator):
    """ makes the refractory model in the backgorund """
    bl_idname = "d3splint.background_refractory_model"
    bl_label = "Add Job Refractory Model"
    bl_description = "Adds Refractory Model Background Job"
    bl_options = {'REGISTER'}

    
    b_radius = FloatProperty(default = .05 , min = .01, max = .12, description = 'Allowable Undercut, larger values results in more retention, more snap into place', name = 'Undercut')
    c_radius = FloatProperty(default = .12 , min = .05, max = .25, description = 'Compensation Gap, larger values results in less retention, less friction', name = 'Compensation Gap')
    d_radius = FloatProperty(default = 1.0, min = 0.5, max = 2.0, description = 'Drill compensation removes small concavities to account for the size of milling tools')
    resolution = FloatProperty(default = 1.5, description = 'Mesh resolution. 1.5 seems ok?')
    scale = FloatProperty(default = 10, description = 'Only chnage if willing to crash blender.  Small chnages can make drastic differences')
    
    max_blockout = FloatProperty(default = 10.0 , min = 2, max = 10.0, description = 'Limit the depth of blockout to save processing itme', name = 'Blockout Limit')
    override_large_angle = BoolProperty(name = 'Angle Override', default = False, description = 'Large deviations between insertion asxis and world Z')
    use_drillcomp = BoolProperty(name = 'Use Drill Compensation', default = False, description = 'Do additional calculation to overmill sharp internal angles')
    #use_drillcomp_Dev = BoolProperty(name = 'Use Drill Compensation Dev', default = False, description = 'Add an actual mesh sphere at surface')
    angle = FloatProperty(default = 0.0 , min = 0.0, max = 180.0, description = 'Angle between insertion axis and world Z', name = 'Insertion angle')
    
    ################################################
    # Blender Operator methods
    
    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        return True

    def draw(self,context):
        
        layout = self.layout
    
        row = layout.row()
        row.prop(self, "b_radius")
        
        row = layout.row()
        row.prop(self, "c_radius")
        
        row = layout.row()
        row.prop(self, "max_blockout")
        
        row = layout.row()
        row.prop(self, "use_drillcomp")
        
        row = layout.row()
        row.prop(self, "d_radius")
        
        if self.angle > 25:
            row = layout.row()
            msg  = 'The angle between insertion axis and world z is: ' + str(self.angle)[0:3]
            row.label(msg)
            
            row = layout.row()
            row.label('You will need to confirm this by overriding')
            
            row = layout.row()
            row.label('Consider cancelling (right click) and inspecting your insertion axis')
            
            row = layout.row()
            row.prop(self, "override_large_angle")
            
    def invoke(self, context, event):
        #gather some information
        Axis = bpy.data.objects.get('Insertion Axis')
        if Axis == None:
            self.report({'ERROR'},'Need to set survey from view first, then adjust axis arrow')
            return {'CANCELLED'}
        
        if len(context.scene.odc_splints) == 0:
            self.report({'ERROR'},'Need to plan a splint first')
            return {'CANCELLED'}
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        axis_z = Axis.matrix_world.to_quaternion() * Vector((0,0,1))
        
        if splint.jaw_type == 'MAXILLA':
            Z = Vector((0,0,-1))
        else:
            Z = Vector((0,0,1))
            
        angle = axis_z.angle(Z)
        angle_deg = 180/math.pi * angle
        
        if angle_deg > 35:
            self.angle = angle_deg
            
        settings = get_settings()
        self.c_radius = settings.def_passive_radius
        self.b_radius = settings.def_blockout_radius
        self.splint = splint
        return context.window_manager.invoke_props_dialog(self)
    
    
    def execute(self, context):
        if bpy.data.filepath == "":
            self.report({"WARNING"}, "Please save the file first")
            return {"CANCELLED"}
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        self.splint = splint
        
        pdata = {}
        pdata['b_radius'] = self.b_radius  #blockout
        pdata['c_radius'] = self.c_radius  #compensation
        pdata['d_radius'] = self.d_radius  #drill
        pdata['resolution'] = self.resolution
        pdata['max_blockout'] = self.max_blockout
        pdata['use_drillcomp'] = self.use_drillcomp
        pdata['model_name'] = splint.model
        pdata['jaw_type'] = splint.jaw_type
        pdata['scale'] = self.scale
        pdata['angle'] = self.angle
        
        #clear old data
        if 'Refractory Model' in bpy.data.objects:
            ob = bpy.data.objects.get('Refractory Model')
            me = ob.data
            context.scene.objects.unlink(ob)
            bpy.data.objects.remove(ob)
            bpy.data.meshes.remove(me)
        # NOTE: Set 'use_blend_file' to True to access data from the current blend file in script (False to execute script from default startup)
        #self.splint.refractory_in_progress = True
        #_job_status.jobs_started['REFRACTORY MODEL'] = True
        bg_status.refractory_start = True
        jobAdded, msg = self.JobManager.add_job(self.job["name"],
                                                    timeout = 200,
                                                    script = self.job["script"],
                                                    use_blend_file=True, 
                                                    passed_data=pdata)
        
        if not jobAdded:
            self.report({"WARNING"}, "unable to add job right now")
            #_job_status.jobs_started['REFRACTORY MODEL'] = False
            bg_status.refractory_start = False
            raise Exception(msg)
            return {"CANCELLED"}
        
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, context.window)
        wm.modal_handler_add(self)
        return{"RUNNING_MODAL"}

    def finish(self, context):                    
        new_ob = bpy.data.objects.get('Refractory Model')
        context.scene.objects.link(new_ob)

        mat = bpy.data.materials.get("Refractory Material")
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name="Refractory Material")
            mat.diffuse_color = Color((0.36, .8,.36))
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .4
            
        if len(new_ob.material_slots) == 0:
            new_ob.data.materials.append(mat)
        
        Model = bpy.data.objects.get(self.splint.model)
        if 'Child Of' not in new_ob.constraints: 
            cons = new_ob.constraints.new('CHILD_OF')
            cons.target = Model
            cons.inverse_matrix = Model.matrix_world.inverted()
        
        Model.hide = False
        new_ob.hide = True
        self.splint.refractory_model = True
        bpy.ops.ed.undo_push()
        #self.splint.refractory_in_progress = False
        #_job_status.jobs_complete['REFRACTORY MODEL'] = True
        #_job_status.jobs_started['REFRACTORY MODEL'] = False
        bg_status.refractory_complete = True
        bg_status.refractory_start = False
        #self.splint.passive_value = self.c_radius
        #self.splint.undercut_value = self.b_radius  #<  in BG mode we read from splint project
        self.splint.ops_string += 'Refractory Model:'
        context.window_manager.event_timer_remove(self._timer)
        #tracking.trackUsage("D3Splint:RemoveUndercuts", (str(self.b_radius)[0:4], str(self.b_radius)[0:4]), background = True)   
        
                
    def modal(self, context, event):
        if event.type == "TIMER":
            self.JobManager.process_job(self.job["name"], debug_level=3)
            
            if self.JobManager.job_complete(self.job["name"]):
                self.report({"INFO"}, "Background process '{job_name}' was finished".format(job_name=self.job["name"]))
                retrieved_data_blocks = self.JobManager.get_retrieved_data_blocks(self.job["name"])
                retrieved_python_data = self.JobManager.get_retrieved_python_data(self.job["name"])
                print(retrieved_data_blocks.objects)
                print(retrieved_python_data)             
                self.finish(context)
                return {"FINISHED"}
            
            elif self.JobManager.job_dropped(self.job["name"]):
                if self.JobManager.job_timed_out(self.job["name"]):
                    self.report({"WARNING"}, "Background process '{job_name}' timed out".format(job_name=self.job["name"]))
                elif self.JobManager.job_killed(self.job["name"]):
                    self.report({"WARNING"}, "Background process '{job_name}' was killed".format(job_name=self.job["name"]))
                else:
                    self.report({"WARNING"}, "Background process '{job_name}' failed".format(job_name=self.job["name"]))
                    errormsg = self.JobManager.get_issue_string(self.job["name"])
                    print(errormsg)
                #_job_status.jobs_started['REFRACTORY MODEL'] = False
                bg_status.refractory_start = False
                context.window_manager.event_timer_remove(self._timer)
                return {"CANCELLED"}
        return {"PASS_THROUGH"}

    def cancel(self, context):
        self.JobManager.kill_job(self.job["name"])
        bg_status.refractory_start = False
        context.window_manager.event_timer_remove(self._timer)
    ################################################
    # initialization method

    def __init__(self):
        script= refractory_model_job
        #self.job = min_thick_job
        self.job = {"name":basename(script), "script":script}
        self.JobManager = JobManager.get_instance(-1)
        self.JobManager.max_workers = 5


    ###################################################


class D3SSPLINT_OT_splint_shell_background(Operator):
    """ makes the splint shell in the backgorund """
    bl_idname = "d3splint.background_splint_shell"
    bl_label = "Add Job Splint Shell"
    bl_description = "Adds Splint Shell Background Job"
    bl_options = {'REGISTER'}

    
    radius = FloatProperty(default = 1.5, min = .6, max = 4, description = 'Thickness of splint', name = 'Thickness')
    resolution = FloatProperty(default = .4, min = .1, max = 2.0, description = 'Small values result in more dense meshes and longer processing times, but may be needed for experimental workflows')
    
    
    ################################################
    # Blender Operator methods
    
    @classmethod
    def poll(cls, context):
        #if "Trimmed_Model" in bpy.data.objects:
        #    return True
        #else:
        #    return False
        return True
    
    def draw(self,context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "radius")
        
  
    def invoke(self, context, event):
        settings = get_settings()
        self.radius = settings.def_shell_thickness
        return context.window_manager.invoke_props_dialog(self)
    
    
    def execute(self, context):
        if bpy.data.filepath == "":
            self.report({"WARNING"}, "Please save the file first")
            return {"CANCELLED"}
        n = context.scene.odc_splint_index
        self.splint = context.scene.odc_splints[n]
    
        pdata = {}
        pdata['radius'] = self.radius  #blockout
        pdata['resolution'] = self.resolution
        pdata['trimmed_model_name'] = 'Shell Patch'
        
        #clear old data
        if 'Splint Shell' in bpy.data.objects:
            ob = bpy.data.objects.get('Splint Shell')
            me = ob.data
            context.scene.objects.unlink(ob)
            bpy.data.objects.remove(ob)
            bpy.data.meshes.remove(me)
        # NOTE: Set 'use_blend_file' to True to access data from the current blend file in script (False to execute script from default startup)
        #self.splint.splint_shell_in_progress = True
        #_job_status.jobs_started['SPLINT SHELL'] = True
        bg_status.shell_start = True
        jobAdded, msg = self.JobManager.add_job(self.job["name"],
                                                    timeout = 120,
                                                    script = self.job["script"],
                                                    use_blend_file=True, 
                                                    passed_data=pdata)
        if not jobAdded:
            self.report({"WARNING"}, "unable to add job right now")
            #_job_status.jobs_started['SPLINT SHELL'] = False
            bg_status.shell_start = False
            raise Exception(msg)
            #splint.min_thick_in_progress = False
            
            return {"CANCELLED"}
        
        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, context.window)
        wm.modal_handler_add(self)
        return{"RUNNING_MODAL"}

    def finish(self, context):                    
        new_ob = bpy.data.objects.get('Splint Shell')
        context.scene.objects.link(new_ob)
        
        bme_shell = bmesh.new()
        bme_shell.from_mesh(new_ob.data)
        bme_shell.verts.ensure_lookup_table()
        bme_shell.edges.ensure_lookup_table()
        bme_shell.faces.ensure_lookup_table()
        splint_cache.write_shell_cache(bme_shell)
        if 'shell_backup' in bpy.data.meshes:
            shell_back = bpy.data.meshes.get('shell backup')
        else:
            shell_back = bpy.data.meshes.new('shell backup')
            shell_back.use_fake_user = True
        bme_shell.to_mesh(shell_back)
        
        new_ob.hide = True
        new_ob.matrix_world = bpy.data.objects.get('Shell Patch').matrix_world
        

        mat = bpy.data.materials.get("Splint Material")
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name="Splint Material")
            mat.diffuse_color = get_settings().def_splint_color
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .4
            
        if len(new_ob.material_slots) == 0:
            new_ob.data.materials.append(mat)
        
        Model = bpy.data.objects.get(self.splint.model)
        if 'Child Of' not in new_ob.constraints: 
            cons = new_ob.constraints.new('CHILD_OF')
            cons.target = Model
            cons.inverse_matrix = Model.matrix_world.inverted()

        self.splint.splint_shell = True
        bpy.ops.ed.undo_push()
        #_job_status.jobs_complete['SPLINT SHELL'] = True
        #_job_status.jobs_started['SPLINT SHELL'] = False
        bg_status.shell_complete = True
        bg_status.shell_start = False
        self.splint.splint_shell_in_progress = False
        self.splint.ops_string += 'Splint Shell:'
        context.window_manager.event_timer_remove(self._timer)
        #tracking.trackUsage("D3Splint:OffsetShell",self.radius)  
        
    def modal(self, context, event):
        if event.type == "TIMER":
            self.JobManager.process_job(self.job["name"], debug_level=3)
            
            if self.JobManager.job_complete(self.job["name"]):
                self.report({"INFO"}, "Background process '{job_name}' was finished".format(job_name=self.job["name"]))
                retrieved_data_blocks = self.JobManager.get_retrieved_data_blocks(self.job["name"])
                retrieved_python_data = self.JobManager.get_retrieved_python_data(self.job["name"])
                print(retrieved_data_blocks.objects)
                print(retrieved_python_data)             
                self.finish(context)
                return {"FINISHED"}
            
            elif self.JobManager.job_dropped(self.job["name"]):
                if self.JobManager.job_timed_out(self.job["name"]):
                    self.report({"WARNING"}, "Background process '{job_name}' timed out".format(job_name=self.job["name"]))
                elif self.JobManager.job_killed(self.job["name"]):
                    self.report({"WARNING"}, "Background process '{job_name}' was killed".format(job_name=self.job["name"]))
                else:
                    self.report({"WARNING"}, "Background process '{job_name}' failed".format(job_name=self.job["name"]))
                    errormsg = self.JobManager.get_issue_string(self.job["name"])
                    print(errormsg)
                #_job_status.jobs_started['SPLINT SHELL'] = False
                bg_status.shell_start = False
                context.window_manager.event_timer_remove(self._timer)
                return {"CANCELLED"}
        return {"PASS_THROUGH"}

    def cancel(self, context):
        self.JobManager.kill_job(self.job["name"])
        bg_status.shell_start = False
        context.window_manager.event_timer_remove(self._timer)
    ################################################
    # initialization method

    def __init__(self):
        script = splint_shell_job
        self.job = {"name":basename(script), "script":script}
        self.JobManager = JobManager.get_instance(-1)
        self.JobManager.max_workers = 5

    ###################################################

def register():
    bpy.utils.register_class(D3SSPLINT_OT_min_thickness_background)
    bpy.utils.register_class(D3SSPLINT_OT_refractory_model_background)
    bpy.utils.register_class(D3SSPLINT_OT_splint_shell_background)
    bpy.utils.register_class(D3SPLINT_OT_splint_background_functional_surface)
    bpy.utils.register_class(D3SSPLINT_OT_bg_job_director)
    bpy.utils.register_class(D3SSPLINT_OT_bg_stop_job_director)

def unregister():
    bpy.utils.unregister_class(D3SSPLINT_OT_min_thickness_background)
    bpy.utils.unregister_class(D3SSPLINT_OT_refractory_model_background)
    bpy.utils.unregister_class(D3SSPLINT_OT_splint_shell_background)
    bpy.utils.unregister_class(D3SPLINT_OT_splint_background_functional_surface)
    bpy.utils.unregister_class(D3SSPLINT_OT_bg_job_director)
    bpy.utils.register_class(D3SSPLINT_OT_bg_stop_job_director)