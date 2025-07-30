'''
module for global status of the job director
so that state can be preserved across opening of new files
'''
force_stop_director = False
director_running = False

min_thick_start = False
refractory_start = False
shell_start = False
dyn_surface_start = False


min_thick_complete = False
refractory_complete = False
shell_complete = False
dyn_surface_complete = False
