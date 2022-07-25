import requests
from lxml import etree
import os
import time

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


url = 'https://datachart.500.com/ssq/history/newinc/history.php?start=00001&end=999999'
ssqPath = './spider_data/ssq.txt'
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


response = requests.get(url)
response = response.text
selector = etree.HTML(response)
updateSum = 0

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

# 没有更新时退出
if updateSum > 0:
    try:
        mkdir('./spider_data/')
        open(ssqPath, 'w').close()
        of = open(ssqPath,"a")
        timeMark = '999999999'
        ssqs[timeMark] = ''
        ssqs[timeMark] = '{},{},{},{},{}\n'.format(timeMark, updateSum, len(ssqs.keys()) ,str(int(round(time.time() * 1000))), 'Current behavior update info')
        ssqkeys = sorted(ssqs.keys(), reverse = True)
        try:
            for key in ssqkeys:
                of.write(ssqs[key])
        finally:
            of.close()
            print('updateSum is {} \n'.format(updateSum))
    except IOError:
        print('Write failed')
        
print('Finished')
