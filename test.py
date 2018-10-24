import requests
from lxml import etree

url = 'http://car.bitauto.com/benchicji-2364/m123304/'

response = requests.get(url)
html = etree.HTML(response.text)
title = html.xpath('//tbody/tr/td/span[@class="title"]/text()')
info = html.xpath('//tbody/tr/td/span[@class="info"]/text()')
print(title,info)



    
    
    
    
    
    
    
    
    
    
    
    
    