'''
Created on Mar 7, 2020

@author: Patrick
'''

from d3guard import validation


key = validation.get_cloud_key()
if key == '':
    print("NO KEY!")
    
credits = validation.check_credits(key)

print('CREDITS CHECKED')
    