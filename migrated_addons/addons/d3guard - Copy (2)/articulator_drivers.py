'''
Created on Mar 7, 2020

@author: Patrick
'''
import math

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement


def saw_tooth(frame):
    #amplitude  to 0 to 1
    #period of 30 frames
    
    r = math.fmod(frame, 30)
    return r/30
    
def thirty_steps(frame):
    r = math.floor(frame/30)/30
    return r



def full_envelope_with_relax(frame, condy_length, resolution, use_relax, relax_length, right_left):
    
    if frame > resolution * (resolution + 1):
        frame = resolution * (resolution + 1)
        
    factor = min(1, condy_length/8)
    
    
    r_factor = min(1, relax_length/2)
    
    if frame < resolution**2:
        if right_left == 'R':
            R = .2 + factor * .8 * math.fmod(frame,resolution)/resolution
        else:
            R = .2 + factor * .8 * math.floor(frame/resolution)/resolution
            
            
    else:#retrusion
    
        R = .2 - r_factor * .2 * (frame - resolution**2)/resolution
        
        
    return R

def three_way_envelope_l(frame, factor, resolution):
    #protrusion
    if frame < resolution:
        R = .2 + factor * .8 * abs(math.sin(math.pi * frame/(2*resolution)))
                   
    #right excursion
    elif frame >= resolution and frame < 2 * resolution:
        R = .2 + factor * .8 * abs(math.sin(math.pi * (frame-resolution)/(2*resolution)))
            
    #left excursion
    elif frame >=2*resolution and frame < 3*resolution:
        R = .2
        
    else:
        R = .2
        
    return R
               
def three_way_envelope_r(frame, factor, resolution):
    #protrusion
    if frame < resolution:
        R = .2 + factor * .8 * abs(math.sin(math.pi * frame/(2*resolution)))
             
    #right excursion
    elif frame >= resolution and frame < 2 * resolution:
        R = .2        
            
    #left excursion
    elif frame >=2*resolution and frame < 3*resolution:
        R = .2 + factor * .8 * abs(math.sin(math.pi * (frame-2*resolution)/(2*resolution)))
        
    else:
        R = .2
        
    return R

def load_driver_namespace():   
    
    if 'saw_tooth' not in bpy.app.driver_namespace:
        bpy.app.driver_namespace['saw_tooth'] = saw_tooth
    
    if 'thirty_steps' not in bpy.app.driver_namespace:
        bpy.app.driver_namespace['thirty_steps'] = thirty_steps
    
    if 'threeway_envelope_r' not in bpy.app.driver_namespace:
        bpy.app.driver_namespace['threeway_envelope_r'] = three_way_envelope_r
    
    if 'threeway_envelope_' not in bpy.app.driver_namespace:
        bpy.app.driver_namespace['threeway_envelope_l'] = three_way_envelope_l

    if 'full_envelope_with_relax' not in bpy.app.driver_namespace:
        bpy.app.driver_namespace['full_envelope_with_relax'] = full_envelope_with_relax