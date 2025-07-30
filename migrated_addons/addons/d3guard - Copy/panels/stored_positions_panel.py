'''
Created on Jul 25, 2020

@author: Patrick
'''

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import numpy as np
import math

def get_icon(trim_series, prop):
    #print('getting icon')
    if trim_series.get(prop):
        return 'CHECKBOX_HLT'
    else:
        return 'CHECKBOX_DEHLT'
    
    
def draw_store_positions(layout, box, d3dproject):
    #row = layout.row()
    #row.label('Jaw : {}'.format(trim.jaw_type))
    
    #row = box.row()
    #row.label('Work Flow : {}'.format(trim.workflow_type))
    
    if d3dproject.show_stored_positions:
        row = box.row()
        split = row.split(percentage = .2)
        colL = split.column()
        colL.prop(d3dproject,"show_stored_positions", text = "", icon = 'TRIA_DOWN')
        colR = split.column()
        colR.label('Stored Positions')
    
            
        models = d3dproject.stored_positions.split(',')
        models.pop()
        
        markers = [m for m in bpy.context.scene.timeline_markers]
        
        Mandible = bpy.data.objects.get(d3dproject.get_mandible())
        Bow = bpy.data.objects.get('Bottom Element')
        if not Mandible: return
        if not Bow: return
        
        row = box.row()
        row.operator("d3dual.store_articulated_position")# , icon = "RECORD")
        if models == []: 
            row = box.row()
            row.label('NO STORED POSITIONS')
            return
        
        active_pos = None
        active_ind = 0
        next_ind = 0
        prev_ind = 0
        
        for i, ob in enumerate(models):   
        #for i, m in enumerate(markers):
            
            #if ob == '': continue #bad hack for empty trailing comma
            obj = bpy.data.objects.get(ob)
            if not obj:
                row = box.row()
                row.label('MISSING STORED POSITION!')
                continue
           
            row = box.row()
            active = np.allclose(obj.matrix_world, Bow.matrix_world, atol = .00001)
            #print(active)
            #active = bpy.context.scene.frame_current == m.frame
            if active:
                active_pos = ob
                active_ind = i
                icon = 'MESH_CIRCLE'
            else:
                icon = 'NONE'
            row.label(ob, icon = icon) 


        if len(models):
            row = box.row()
            row.operator("d3dual.next_stored_position", icon = 'TRIA_LEFT', text = '').previous = True
            #row.operator("screen.marker_jump", icon = 'TRIA_LEFT', text = '').next = False
            row.operator("d3dual.jump_to_stored_position", icon = 'RECOVER_LAST', text = '')
            row.operator("d3dual.next_stored_position", icon = 'TRIA_RIGHT', text = '').previous = False
            #row.operator("screen.marker_jump", icon = 'TRIA_LEFT', text = '').next = True
    else:
        row = box.row()
        split = row.split(percentage = .2)
        
        colL = split.column(align=False)
        colL.prop(d3dproject,"show_stored_positions", text = "", icon = 'TRIA_RIGHT')
        colR = split.column()
        colR.label('Show Stored Positions')
        
        
        
def draw_scroll_arrows(layout):
    
    row = layout.row(align=True)
    pct = 0.7
    split = row.split(percentage=pct)
    OP1 = "d3dual.scroll_stored_position"
        
    l_split = split.split()
    left_side = l_split.column()
    #left_side.operator(OP, text='',  icon='RIGHTARROW_THIN')
    left_side.label('')
    left_side.operator(OP1, text='', icon='TRIA_LEFT').forward = False
    left_side.label('')

    right_side = l_split.column()
    right_side.label('')
    right_side.operator(OP1, text='', icon="TRIA_RIGHT").forward = True
    