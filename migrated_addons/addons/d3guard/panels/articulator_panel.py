'''
Created on Mar 24, 2019

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement


from articulator_handlers import articulator_draw_data

def draw_articulator_tools(layout, show_data = False):
    
    row = layout.row()
    row.label('Articulation')
    row = layout.row()
    col = row.column()
    col.operator("d3dual.live_articulator_parameters", text = "Set Articulator Values")
    #col.operator("d3splint.splint_mount_articulator", text = "Mount on Articulator")

    row = layout.row()
    col = row.column()

    col.operator("d3dual.open_pin_on_articulator", text = "Change Pin Setting" )
    col.operator("d3dual.capture_articulated_position", text = "Capture Position" )
    col.operator("d3dual.recover_mounting_relationship", text = "Recover Mounting" )
    
           
    if show_data:
        
        if 'hinge_opening' not in articulator_draw_data: return
        row = layout.row()
        row.label('Hinge Opening: {:.1f}deg'.format(articulator_draw_data['hinge_opening']))
        row = layout.row()
        row.label('Translation: {:.2f}mm'.format(articulator_draw_data['total_translation']))  
        
        row = layout.row()
        R = articulator_draw_data['lateral_deviation']
        if R < 0:
            direction = 'Right'
        else:
            direction = 'Left'
            
        row.label('Deviation {:.1f}deg to {}'.format(abs(R), direction))
        
          
    
    
            