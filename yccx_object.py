import re
import demjson
import pymysql
import requests
import threading
from lxml import etree
from bs4 import BeautifulSoup

    
class Spider:
    name="易车爬虫"
    url = "http://api.car.bitauto.com/CarInfo/getlefttreejson.ashx?tagtype=chexing&pagetype=masterbrand&objid=0"
    head = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'}
    
    def get_brand(self,):
        response = requests.get(self.url,headers=self.head)
        brandjs = demjson.decode(response.text[132:-2])
        return brandjs
        
    def parse_ppjs(self,brandjs):
        for letter in brandjs:
            brands = brandjs.get(letter)
            for brand in brands:
                brand_name = brand.get('name')            
                brand_id = brand.get('id')            
                url = 'http://api.car.bitauto.com/CarInfo/getlefttreejson.ashx?tagtype=chexing&pagetype=masterbrand&objid={id}'.format(id=brand_id)
                response = requests.get(url,headers=self.head)
                ppjs = demjson.decode(response.text[132:-2])            
                pps = ppjs.get(letter)           
                for pp in pps:                
                    if pp.get('name') == brand_name:                   
                        pp_child = pp.get('child')                    
                        if pp_child[0].get('type') == 'cb':                        
                            cj_list = []                        
                            for cj in pp_child:                            
                                cj_name = cj.get('name')                            
                                cxs = cj.get('child')                           
                                cx_list = []                           
                                for cx in cxs:                                
                                    cx_name = cx.get('name')                                
                                    cx_url = cx.get('url')                               
                                    cx_list.append({cx_name:cx_url})                          
                                cj_list.append({cj_name:cx_list})                    
                        elif pp_child[0].get('type') == 'cs':                       
                            cxs = pp.get('child')                       
                            cj_list = []
                            cx_list = []                      
                            for cx in cxs:                           
                                cx_name = cx.get('name')                           
                                cx_url = cx.get('url')                            
                                cx_list.append({cx_name:cx_url})                       
                            cj_list.append({brand_name:cx_list})                   
                        yield {brand_name:cj_list}
                        
    def parse_cxjs(self,pp_list):
        pp_name = list(pp_list.keys())[0]
        for cj in list(pp_list.values())[0]:
            cj_name = list(cj.keys())[0]
            for cx in list(cj.values())[0]:
                cx_name = list(cx.keys())[0]
                cx_url = 'http://car.bitauto.com' + list(cx.values())[0]
                response = requests.get(cx_url,headers=self.head)
                html = etree.HTML(response.text)
                url = html.xpath('//div[@class="section-header header1"]/div[@class="box"]/h2/a/@href')
                cx_url = 'http://car.bitauto.com' + ''.join(url)
                response = requests.get(cx_url,headers=self.head)
                soup = BeautifulSoup(response.text,'lxml')
                lis = soup.select('.brand-info ul li')[:-1]
                nk_list = []
                for li in lis:        
                    if "停售年款" in li.get_text():
                        tsnks = li.select('div a')
                        for tsnk in tsnks:
                            nk = tsnk.get_text()
                            url = tsnk['href']
                            nk_list.append({nk:url})
                    elif "款" in li.get_text() and "停售年款" not in li.get_text() and "新款上市" not in li.get_text() and "新款即将上市" not in li.get_text():
                        nks = li.select('a')
                        nk = nks[0].get_text()
                        url = nks[0]['href']
                        nk_list.append({nk:url})
                    elif "未上市" in li.get_text():
                        pass
                    elif "全部在售" in li.get_text():
                        pass
                for i in range(len(nk_list)):
                    nk = nk_list[i]
                    yield [pp_name,cj_name,cx_name,nk]
                    '''
                    t = threading.Thread(target=parse_nk,args=(pp_name,cj_name,cx_name,nk))
                    t.start()
                    t.join()
                    '''
        
    def parse_nk(self,pp_name,cj_name,cx_name,nk):
        year = list(nk.keys())[0].replace('款','')
        url = 'http://car.bitauto.com' + list(nk.values())[0]
        response = requests.get(url,headers=self.head)
        soup = BeautifulSoup(response.text,'lxml')
        trs = soup.select('tbody tr')
        cx_name_list = []
        for tr in trs:
            if len(tr['id'])==16 or len(tr['id'])==17:
                pass
            else:
                cx_x_name = re.sub('.*?款 ','',tr.select('td')[0].select('a')[0].get_text(),re.S)
                return pp_name,cj_name,cx_name,year,cx_x_name
                
    def save(self,pp_name,cj_name,cx_name,year,cx_x_name):
        sql = "INSERT INTO cx(pp_name,cj_name,cx_name,year,cx_x_name) VALUES('%s','%s','%s','%s','%s');"%(pp_name,cj_name,cx_name,year,cx_x_name)
        cursor.execute(sql)
        db.commit()
    
    
    
    
    
    
    
    
    
    
    
    
