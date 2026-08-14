import requests,warnings
from requests.packages import urllib3
from lxml import etree
import os
import sys
import time
import argparse
import traceback

urllib3.disable_warnings()
warnings.filterwarnings("ignore")

# 500.com 对默认的 python-requests UA 返回 567 拦截页，必须伪装 UA
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
}
TIMEOUT = 30

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

def fetch(url):
    # 状态码非 2xx 时抛异常，否则错误页会被静默解析成 0 条
    response = requests.get(url=url, headers=HEADERS, timeout=TIMEOUT, verify=False)
    response.raise_for_status()
    return response

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
    # 每个源实际解析出的行数，用来区分「没有新数据」和「源已失效」
    rowsFromUrl2 = 0
    rowsFromUrl = 0
    sourceFailed = 0

    try:
        response = fetch(url2)
        response = response.json()
        for i in response['result']:
            try:
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
                # 金额一旦带千分位逗号会撑破 CSV 列数，统一清洗
                red.append(replaceStr(prize1))
                red.append(replaceStr(prize2))
                red.append(drawdate)
                val = '{}\n'.format(','.join(red))
            except (KeyError, IndexError, TypeError, AttributeError):
                # 单行异常不影响整个源
                print('Skipped a malformed record from url2 \n')
                continue
            rowsFromUrl2 = rowsFromUrl2 + 1
            # 值异常
            if len(val) < 26:
                continue
            # 已经爬取过的数据不更新
            if datetime in ssqs and ssqs[datetime] == val:
                continue
            ssqs[datetime] = val
            updateSum = updateSum + 1

        if rowsFromUrl2 == 0:
            sourceFailed = sourceFailed + 1
            print('WARNING url2 parsed 0 rows, source may be broken \n')
        print('url2 updateSum = {} \n'.format(str(updateSum)))
    except Exception as e:
        sourceFailed = sourceFailed + 1
        print('Failed requests error, url2={} \n{}: {} \n'.format(url2, type(e).__name__, e))

    try:
        response = fetch(url)
        response = response.text
        selector = etree.HTML(response)
        for i in selector.xpath('//tr[@class="t_tr1"]'):
            try:
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
            except (KeyError, IndexError, TypeError, AttributeError):
                # 列数变化时跳过该行，不要让整个源挂掉
                print('Skipped a malformed row from url \n')
                continue
            rowsFromUrl = rowsFromUrl + 1
            # 值异常
            if len(val) < 26:
                continue
            # 已经爬取过的数据不更新
            if datetime in ssqs and ssqs[datetime] == val:
                continue
            ssqs[datetime] = val
            updateSum = updateSum + 1

        if rowsFromUrl == 0:
            sourceFailed = sourceFailed + 1
            print('WARNING url parsed 0 rows, source may be broken \n')
        print('url updateSum all = {} \n'.format(str(updateSum)))
    except Exception as e:
        sourceFailed = sourceFailed + 1
        print('Failed requests error, url={} \n{}: {} \n'.format(url, type(e).__name__, e))

    print('rows parsed: url2={}, url={} \n'.format(rowsFromUrl2, rowsFromUrl))

    # 两个源都没拿到数据，说明是抓取故障而不是「暂无新开奖」
    if rowsFromUrl2 == 0 and rowsFromUrl == 0:
        print('Both sources returned no rows, aborting without touching data files \n')
        return False

    # 期号断层预警：pageSize/limit 太小会在历史中留下空洞
    gaps = findGaps(ssqs)
    if gaps:
        print('WARNING missing issues detected (increase pageSize/limit): {} \n'.format(gaps))

    # 没有更新时退出
    if updateSum > 0:
        timeMark = '999999999'
        ssqs[timeMark] = ''
        ssqs[timeMark] = '{},{},{},{},{}\n'.format(timeMark, updateSum, len(ssqs.keys()) ,str(int(round(time.time() * 1000))), 'Current behavior update info')
        ssqkeys = sorted(ssqs.keys(), reverse = True)
        # 先在内存里拼好，避免写入中途失败把已有数据截断成空文件
        txtBody = ''.join(ssqs[key] for key in ssqkeys)
        jsBody = 'window.ssqData = `{}`'.format(txtBody)
        try:
            mkdir('./spider_data/')
            writeAtomic(ssqPath, txtBody)
            writeAtomic(ssqJSPath, jsBody)
            print('updateSum is {} \n'.format(updateSum))
        except IOError as e:
            print('Write failed, {}: {} \n'.format(type(e).__name__, e))
            return False

    return True

def writeAtomic(path, content):
    # 同目录临时文件 + os.replace，保证要么是旧内容要么是新内容
    tmpPath = '{}.tmp'.format(path)
    f = open(tmpPath, 'w')
    try:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    finally:
        f.close()
    os.replace(tmpPath, path)

def findGaps(ssqs):
    # 按 5 位期号的年份分组，报出组内缺失的期号
    issues = {}
    for key in ssqs.keys():
        if len(key) != 5 or not key.isdigit():
            continue
        issues.setdefault(key[0:2], []).append(int(key[2:]))
    gaps = []
    for year in sorted(issues.keys()):
        nums = set(issues[year])
        for n in range(min(nums), max(nums) + 1):
            if n not in nums:
                gaps.append('{}{:03d}'.format(year, n))
    return gaps


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", type=str, required=False, default="", help="url")
    parser.add_argument("-u2", "--url2", type=str, required=False, default="", help="url2")
    args = parser.parse_args()
    try:
        print(args)
        # URL 两端的空白会让 requests 直接报错，先清掉
        ok = start(args.url.strip(), args.url2.strip())
        print('Finished')
        if not ok:
            sys.exit(1)
    except Exception:
        # 打完整堆栈并以非 0 退出，否则 CI 会把静默失败当成功
        traceback.print_exc()
        print('error')
        sys.exit(1)
