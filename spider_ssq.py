import requests,warnings
from requests.packages import urllib3
from lxml import etree
import os
import time
import argparse

urllib3.disable_warnings()
warnings.filterwarnings("ignore")

def replaceStr(s=''):
    return s.replace(' ', '').replace(',', '')

def mkdir(path):
    path=path.strip()
    path=path.rstrip('\\')
    isExists=os.path.exists(path)
    if not isExists:
        os.makedirs(path) 
        return True
    else:
        return False

def start(url, url2):
    ssqPath = './spider_data/ssq.txt'
    ssqJSPath = './spider_data/ssq.js'
    ssqs = {}

    try:
        oldFile = open(ssqPath, 'r')
        try:
            line = oldFile.readline()
            while line: 
                ssqs[line.split(',')[0]] = line
                line = oldFile.readline() 
        finally:
            oldFile.close()
    except IOError:
        print('Failed to read history, {} isNotExists \n'.format(ssqPath))

    updateSum = 0

    try:
        response = requests.get(url)
        response = response.text
        selector = etree.HTML(response)
        for i in selector.xpath('//tr[@class="t_tr1"]'):
            datetime = replaceStr(i.xpath('td/text()')[0])
            # 期数长度不符合要求时
            if len(datetime) < 5:
                continue
            red = i.xpath('td/text()')[1:7]
            blue = i.xpath('td/text()')[7]
            prize1 = replaceStr(i.xpath('td/text()')[11])
            prize2 = replaceStr(i.xpath('td/text()')[13])
            drawdate = replaceStr(i.xpath('td/text()')[15])
            #red.insert(0,'20'+datetime)
            red.insert(0,datetime)
            red.append(blue)
            red.append(prize1)
            red.append(prize2)
            red.append(drawdate)
            val = '{}\n'.format(','.join(red))
            # 值异常
            if len(val) < 26:
                continue
            # 已经爬取过的数据不更新
            if datetime in ssqs and ssqs[datetime] == val:
                continue
            ssqs[datetime] = val
            updateSum = updateSum + 1
    except IOError:
        print('Failed requests error, url={} \n'.format(url))


    try:
        response = requests.get(url=url2,verify=False)
        response = response.json()
        for i in response['result']:
            datetime = i["code"][2:len(i["code"])]
            # 期数长度不符合要求时
            if len(datetime) < 5:
                continue
            red = i['red'].split(',')
            blue = i['blue']
            prize1 = i['prizegrades'][0]['typemoney']
            prize2 = i['prizegrades'][1]['typemoney']
            drawdate = i["date"][0:len(i["date"]) - 3]
            #red.insert(0,'20'+datetime)
            red.insert(0,datetime)
            red.append(blue)
            red.append(prize1)
            red.append(prize2)
            red.append(drawdate)
            val = '{}\n'.format(','.join(red))
            # 值异常
            if len(val) < 26:
                continue
            # 已经爬取过的数据不更新
            if datetime in ssqs and ssqs[datetime] == val:
                continue
            ssqs[datetime] = val
            updateSum = updateSum + 1
    except IOError:
        print('Failed requests error, url2={} \n'.format(url2))

    # 没有更新时退出
    if updateSum > 0:
        try:
            mkdir('./spider_data/')
            open(ssqPath, 'w').close()
            open(ssqJSPath, 'w').close()
            of = open(ssqPath,"a")
            ofJS = open(ssqJSPath,"a")
            timeMark = '999999999'
            ssqs[timeMark] = ''
            ssqs[timeMark] = '{},{},{},{},{}\n'.format(timeMark, updateSum, len(ssqs.keys()) ,str(int(round(time.time() * 1000))), 'Current behavior update info')
            ssqkeys = sorted(ssqs.keys(), reverse = True)
            try:
                ofJS.write("window.ssqData = `")
                for key in ssqkeys:
                    of.write(ssqs[key])
                    ofJS.write(ssqs[key])
                ofJS.write("`")
            finally:
                of.close()
                ofJS.close()
                print('updateSum is {} \n'.format(updateSum))
        except IOError:
            print('Write failed')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", type=str, required=False, default="", help="url")
    parser.add_argument("-u2", "--url2", type=str, required=False, default="", help="url2")
    args = parser.parse_args()
    # try:
    print(args)
    start(args.url, args.url2)
    print('Finished')
    # except:
    #     print('error')

