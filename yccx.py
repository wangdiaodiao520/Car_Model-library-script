import requests
from bs4 import BeautifulSoup
from lxml import etree
import demjson
import re
import pymysql
import threading


#声明数据库
db = pymysql.connect(host='192.168.1.107',port=3306, user='debian-sys-maint',password='LLmPbgeHXb3YlGbx',db='cx',charset='utf8mb4')
cursor = db.cursor()
#请求头
head = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'}
#得到品牌列表连接js

#拿到品牌js数据
def get_brand():
    url = 'http://api.car.bitauto.com/CarInfo/getlefttreejson.ashx?tagtype=chexing&pagetype=masterbrand&objid=0'
    response = requests.get(url,headers=head)
    brandjs = demjson.decode(response.text[132:-2])
    return brandjs
  
#解析品牌列表js,构造一个list，包含品牌-厂家-车型-连接
def parse_ppjs(brandjs):
    #拿到每个字母下的品牌集
    for letter in brandjs:
        brands = brandjs.get(letter)
        #从品牌集中拿到每个品牌
        for brand in brands:
            #拿到此品牌名
            brand_name = brand.get('name')
            #此品牌id
            brand_id = brand.get('id')
            #构造此品牌js链接，请求url，拿到带有品牌数据的js
            url = 'http://api.car.bitauto.com/CarInfo/getlefttreejson.ashx?tagtype=chexing&pagetype=masterbrand&objid={id}'.format(id=brand_id)
            response = requests.get(url,headers=head)
            ppjs = demjson.decode(response.text[132:-2])
            #拿到此字母下的品牌集
            pps = ppjs.get(letter)
            #迭代品牌集
            for pp in pps:
                #判断是否是此品牌
                if pp.get('name') == brand_name:
                    #拿到品牌js下的child集
                    pp_child = pp.get('child')
                    #判断品牌下child集的type
                    if pp_child[0].get('type') == 'cb':
                        #厂家列表
                        cj_list = []
                        #如type为cb，拿到下级厂家js
                        for cj in pp_child:
                            #厂家名
                            cj_name = cj.get('name')
                            #厂家下child（车型js）
                            cxs = cj.get('child')
                            #车型列表
                            cx_list = []
                            #拿到每个车型
                            for cx in cxs:
                                #车型名
                                cx_name = cx.get('name')
                                #车型页url
                                cx_url = cx.get('url')
                                #构造成[{车型,url},{车型,url}]
                                cx_list.append({cx_name:cx_url})
                            #构造成[{厂家：[{车型,url},{车型,url}]},{厂家：[{车型,url},{车型,url}]}]
                            cj_list.append({cj_name:cx_list})
                    #如type为cs，拿到下级车型集
                    elif pp_child[0].get('type') == 'cs':
                        #品牌下child（车型js）
                        cxs = pp.get('child')
                        #厂家列表，车型列表
                        cj_list = []
                        cx_list = []
                        #拿到每个车型
                        for cx in cxs:
                            #车型名
                            cx_name = cx.get('name')
                            #车型页url
                            cx_url = cx.get('url')
                            #构造成[{车型,url},{车型,url}]
                            cx_list.append({cx_name:cx_url})
                        #构造成[{厂家：[{车型,url},{车型,url}]},{厂家：[{车型,url},{车型,url}]}]
                        cj_list.append({brand_name:cx_list})
                   #这里使用生成器防止过长时间网络io阻塞
                    yield {brand_name:cj_list}

#解析车型list
def parse_cxjs(pp_list):
    #拿到品牌名
    pp_name = list(pp_list.keys())[0]
    #迭代厂家集，拿到每个厂家
    for cj in list(pp_list.values())[0]:
        #拿到厂家名
        cj_name = list(cj.keys())[0]
        #迭代车型集，拿到每个车型
        for cx in list(cj.values())[0]:
            #车型名
            cx_name = list(cx.keys())[0]
            #车型url
            cx_url = 'http://car.bitauto.com' + list(cx.values())[0]
            #转换url
            cx_url = trans_url(cx_url)
            #拿到车型下所有年款和年款相对应的url，格式为[{年款：url}，{年款：url}]
            nk_list = parse_cx_url(cx_url)
            for i in range(len(nk_list)):#在这一步使用多线程提高速度---------
                nk = nk_list[i]
                #parse_nk(pp_name,cj_name,cx_name,nk)
                t = threading.Thread(target=parse_nk,args=(pp_name,cj_name,cx_name,nk))
                t.start()
                t.join()
                
                
#请求车型url函数，（功能为从tree页转换到专属页）
def trans_url(cx_url):
    response = requests.get(cx_url,headers=head)
    html = etree.HTML(response.text)
    url = html.xpath('//div[@class="section-header header1"]/div[@class="box"]/h2/a/@href')
    cx_url = 'http://car.bitauto.com' + ''.join(url)
    return cx_url

#解析车型连接    
def parse_cx_url(cx_url):
    response = requests.get(cx_url,headers=head)
    soup = BeautifulSoup(response.text,'lxml')
    #拿到年款集，包含未上市、全部在售、停售年款、****款
    lis = soup.select('.brand-info ul li')[:-1]
    nk_list = []
    #判断每个li，并操作
    for li in lis:
        #如是停售年款，拿其中年款和url
        if "停售年款" in li.get_text():
            tsnks = li.select('div a')
            for tsnk in tsnks:
                nk = tsnk.get_text()
                url = tsnk['href']
                nk_list.append({nk:url})
        #如是****款，拿其中年款和url
        elif "款" in li.get_text() and "停售年款" not in li.get_text() and "新款上市" not in li.get_text() and "新款即将上市" not in li.get_text():
            nks = li.select('a')
            nk = nks[0].get_text()
            url = nks[0]['href']
            nk_list.append({nk:url})
        #其余不提取数据
        elif "未上市" in li.get_text():
            pass
        elif "全部在售" in li.get_text():
            pass
    return nk_list
        
#解析年款url
def parse_nk(pp_name,cj_name,cx_name,nk):
    #年款
    year = list(nk.keys())[0]
    #年款url
    url = 'http://car.bitauto.com' + list(nk.values())[0]
    #请求url，并定位至车型box
    response = requests.get(url,headers=head)
    soup = BeautifulSoup(response.text,'lxml')
    trs = soup.select('tbody tr')
    cx_name_list = []
    #对车型box中的每个tr进行判断，判断其中数据是否是车型数据
    for tr in trs:
        if len(tr['id'])==16:
            pass
        else:
            cx_x_name = re.sub('.*?款 ','',tr.select('td')[0].select('a')[0].get_text(),re.S)
            save(pp_name,cj_name,cx_name,year,cx_x_name)
            
#保存函数
def save(pp_name,cj_name,cx_name,year,cx_x_name):
    sql = "INSERT INTO cx(pp_name,cj_name,cx_name,year,cx_x_name) VALUES('%s','%s','%s','%s','%s');"%(pp_name,cj_name,cx_name,year,cx_x_name)
    cursor.execute(sql)
    db.commit()
        
if __name__ == "__main__":
    brandjs = get_brand()
    for pp_list in parse_ppjs(brandjs):
        parse_cxjs(pp_list)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
   