import requests, warnings
from requests.packages import urllib3
from lxml import etree
import os
import re
import sys
import time
import random
import argparse
import traceback
from urllib.parse import urlparse

urllib3.disable_warnings()
warnings.filterwarnings("ignore")

# 开奖站点对默认的 python-requests UA 会返回拦截页，必须伪装 UA
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36',
]
TIMEOUT = (10, 25)          # (连接超时, 读取超时)
RETRIES = 3
PER_ATTEMPT_SECONDS = 60    # 单次请求的读取时长上限，防慢速滴流把任务拖死
TOTAL_BUDGET_SECONDS = 360  # 整个抓取过程的硬预算

_DEADLINE = [None]

def budgetLeft():
    if not _DEADLINE[0]:
        return None
    return _DEADLINE[0] - time.time()

def refererOf(url):
    # 用来源自身的站点根作为 Referer，避免在代码里写死具体域名
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        return None
    return '{}://{}/'.format(p.scheme, p.netloc)

class _FatalHttpError(Exception):
    """不可重试的 HTTP 错误（如 404），直接放弃当前源。"""
    pass

def replaceStr(s=''):
    # 全角空格 / 千分位逗号都会污染 CSV 列，统一清洗
    return str(s).replace(' ', '').replace(',', '').replace('\u3000', '').strip()

def numberStr(s=''):
    """金额字段只保留数字。官网接口会给 '6250000（含加奖1250000）' 这种带说明的字符串，
    直接落盘会让下游按数字解析失败。"""
    s = replaceStr(s)
    m = re.match(r'^(\d+)', s)
    if m:
        return m.group(1)
    digits = re.sub(r'\D', '', s)
    return digits

def mkdir(path):
    path = path.strip()
    path = path.rstrip('\\')
    isExists = os.path.exists(path)
    if not isExists:
        os.makedirs(path)
        return True
    else:
        return False

def fetch(url, referer=None, retries=RETRIES):
    """带重试和硬性时间预算的 GET。
    用流式读取，边读边计时，避免对方慢速滴流时读超时永远不触发、任务被无限拖住。
    """
    if not url or not url.startswith(('http://', 'https://')):
        raise ValueError('invalid url: {!r}'.format(url))

    lastError = None
    for attempt in range(1, retries + 1):
        left = budgetLeft()
        if left is not None and left <= 5:
            raise RuntimeError('global time budget exhausted before attempt')
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        if referer:
            headers['Referer'] = referer
        try:
            with requests.get(url=url, headers=headers, timeout=TIMEOUT, verify=False, stream=True) as response:
                # 4xx 里只有 403/429 值得重试（多是反爬/限流），其余直接失败省时间
                if 400 <= response.status_code < 500 and response.status_code not in (403, 429):
                    raise _FatalHttpError('HTTP {} for {}'.format(response.status_code, url))
                # 状态码非 2xx 时抛异常，否则错误页会被静默解析成 0 条
                response.raise_for_status()

                body = bytearray()
                startedAt = time.time()
                for chunk in response.iter_content(chunk_size=65536):
                    body += chunk
                    if time.time() - startedAt > PER_ATTEMPT_SECONDS:
                        raise TimeoutError('response too slow, aborted after {}s and {} bytes'
                                           .format(PER_ATTEMPT_SECONDS, len(body)))
                if not body:
                    raise ValueError('empty body')
                # 回填已读内容，后续仍按普通 Response 使用
                response._content = bytes(body)
                response._content_consumed = True
                return response
        except _FatalHttpError:
            raise
        except Exception as e:
            lastError = '{}: {}'.format(type(e).__name__, e)
            print('fetch attempt {}/{} failed -> {}: {}'.format(attempt, retries, type(e).__name__, e))
            if attempt < retries:
                # 指数退避 + 抖动，避开同 IP / 同时间窗口的限流
                time.sleep(min(2 ** attempt, 10) + random.uniform(0.5, 1.5))
    raise RuntimeError('all {} attempts failed, last error: {}'.format(retries, lastError))

def parseCwlRecord(i):
    """福彩官网接口的字段映射。"""
    datetime = str(i["code"])[2:]
    red = str(i['red']).split(',')
    blue = str(i['blue']).strip()
    prize1 = i['prizegrades'][0]['typemoney']
    prize2 = i['prizegrades'][1]['typemoney']
    drawdate = str(i["date"])[0:len(str(i["date"])) - 3]
    return datetime, red, blue, prize1, prize2, drawdate

def parseZhcwRecord(i):
    """中彩网接口的字段映射（期号是 7 位，红球用空格分隔）。"""
    datetime = str(i['issue'])[2:]
    red = str(i['frontWinningNum']).split()
    blue = str(i['backWinningNum']).strip()
    grades = {}
    for g in (i.get('winnerDetails') or []):
        base = g.get('baseBetWinner') or {}
        grades[str(g.get('awardEtc'))] = base.get('awardMoney', '')
    prize1 = grades.get('1', '')
    prize2 = grades.get('2', '')
    drawdate = str(i['openTime']).strip()
    return datetime, red, blue, prize1, prize2, drawdate

def collectFromJson(url, ssqs, label, referer=None, onlyNew=False):
    """解析 JSON 接口，自动识别两种常见返回结构，返回 (解析行数, 更新条数)。
    支持：福彩官网 result[] 结构、中彩网 data[] 结构。
    onlyNew=True 时只补写缺失期号，不覆盖已有行，避免不同源金额格式差异来回改动文件。
    """
    updates = 0
    rows = 0
    try:
        payload = fetch(url, referer=referer).json()
    except Exception as e:
        print('Failed requests error, {}={} \n{}: {} \n'.format(label, url, type(e).__name__, e))
        return 0, 0

    records = None
    parser = None
    if isinstance(payload, dict) and isinstance(payload.get('result'), list):
        records, parser = payload['result'], parseCwlRecord
    elif isinstance(payload, dict) and isinstance(payload.get('data'), list):
        records, parser = payload['data'], parseZhcwRecord
    if not records:
        print('WARNING {} returned no records (keys: {}), source may be broken \n'
              .format(label, list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__))
        return 0, 0

    for i in records:
        try:
            datetime, red, blue, prize1, prize2, drawdate = parser(i)
            # 期数长度不符合要求时
            if len(datetime) < 5:
                continue
            red.insert(0, datetime)
            red.append(blue)
            # 金额一旦带千分位逗号会撑破 CSV 列数，统一清洗
            red.append(numberStr(prize1))
            red.append(numberStr(prize2))
            red.append(drawdate)
            val = '{}\n'.format(','.join(red))
        except (KeyError, IndexError, TypeError, AttributeError, ValueError):
            # 单行异常不影响整个源
            print('Skipped a malformed record from {} \n'.format(label))
            continue
        rows = rows + 1
        # 值异常
        if len(val) < 26:
            continue
        # 已经爬取过的数据不更新
        if datetime in ssqs and (onlyNew or ssqs[datetime] == val):
            continue
        ssqs[datetime] = val
        updates = updates + 1

    print('{} rows = {}, updateSum = {} \n'.format(label, rows, updates))
    return rows, updates

def collectFromHtml(url, ssqs, label):
    """解析历史开奖表格（HTML），返回 (解析行数, 更新条数)。"""
    updates = 0
    rows = 0
    try:
        response = fetch(url)
        # 页面是 GBK 编码，requests 常猜成 ISO-8859-1，会让中文变成乱码
        if not response.encoding or response.encoding.lower() in ('iso-8859-1', 'ascii'):
            response.encoding = response.apparent_encoding or 'gbk'
        selector = etree.HTML(response.text)
        if selector is None:
            raise ValueError('page is not valid HTML')
        trs = selector.xpath('//tr[@class="t_tr1"]')
        if not trs:
            print('WARNING {} page has no t_tr1 rows, maybe blocked or layout changed \n'.format(label))
    except Exception as e:
        print('Failed requests error, {}={} \n{}: {} \n'.format(label, url, type(e).__name__, e))
        return 0, 0

    for i in trs:
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
            red.insert(0, datetime)
            red.append(blue)
            red.append(prize1)
            red.append(prize2)
            red.append(drawdate)
            val = '{}\n'.format(','.join(red))
        except (KeyError, IndexError, TypeError, AttributeError):
            # 列数变化时跳过该行，不要让整个源挂掉
            print('Skipped a malformed row from {} \n'.format(label))
            continue
        rows = rows + 1
        # 值异常
        if len(val) < 26:
            continue
        # 已经爬取过的数据不更新
        if datetime in ssqs and ssqs[datetime] == val:
            continue
        ssqs[datetime] = val
        updates = updates + 1

    print('{} rows = {}, updateSum = {} \n'.format(label, rows, updates))
    return rows, updates

def start(url, url2, url3=''):
    _DEADLINE[0] = time.time() + TOTAL_BUDGET_SECONDS
    ssqPath = './spider_data/ssq.txt'
    ssqJSPath = './spider_data/ssq.js'
    ssqs = {}
    historyExists = True

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
        historyExists = False
        print('Failed to read history, {} isNotExists \n'.format(ssqPath))

    rowsFromUrl2 = 0
    rowsFromUrl = 0
    rowsFromFallback = 0
    updatesTotal = 0

    # 源1：配置的 JSON 接口（可选，通常是最轻量的一个源）
    if url2 and (budgetLeft() is None or budgetLeft() > 10):
        try:
            rowsFromUrl2, updates = collectFromJson(url2, ssqs, 'url2', referer=refererOf(url2))
            updatesTotal = updatesTotal + updates
        except Exception as e:
            print('Source url2 crashed, keep going: {}: {} \n'.format(type(e).__name__, e))

    # 源2：历史开奖页（HTML）
    if url and (budgetLeft() is None or budgetLeft() > 10):
        try:
            rowsFromUrl, updates = collectFromHtml(url, ssqs, 'url')
            updatesTotal = updatesTotal + updates
        except Exception as e:
            print('Source url crashed, keep going: {}: {} \n'.format(type(e).__name__, e))

    # 源3：备用接口（由 secret 提供，支持 url3 参数）。只在主源不可用时启用，
    # 既能兜住主源的限流/改版，又不会每次运行都多发一个大请求
    url2Host = urlparse(url2).netloc if url2 else ''
    url3Host = urlparse(url3).netloc if url3 else ''
    if ((not url) or (url and rowsFromUrl == 0)) and (budgetLeft() is None or budgetLeft() > 10):
        if not url3:
            print('No fallback url configured (-u3), skip \n')
        elif url2Host and url3Host and url2Host == url3Host:
            print('Fallback source is the same as url2, skip \n')
        else:
            print('Activating fallback source \n')
            try:
                rowsFromFallback, updates = collectFromJson(url3, ssqs, 'fallback', referer=refererOf(url3), onlyNew=True)
                updatesTotal = updatesTotal + updates
            except Exception as e:
                print('Source fallback crashed, keep going: {}: {} \n'.format(type(e).__name__, e))

    totalRows = rowsFromUrl2 + rowsFromUrl + rowsFromFallback
    print('rows parsed: url2={}, url={}, fallback={} \n'.format(rowsFromUrl2, rowsFromUrl, rowsFromFallback))

    # 所有源都没拿到数据，说明是抓取故障而不是「暂无新开奖」
    if totalRows == 0:
        print('All sources returned no rows, aborting without touching data files \n')
        return False

    # 历史文件缺失且只抓到很少数据时，宁可不写，避免把完整历史覆盖成残缺文件
    validRows = len([k for k in ssqs.keys() if len(k) == 5 and k.isdigit()])
    if not historyExists and validRows < 500:
        print('Refuse to overwrite: only {} rows collected while history is missing \n'.format(validRows))
        return False

    # 期号断层预警：pageSize/limit 太小会在历史中留下空洞
    gaps = findGaps(ssqs)
    if gaps:
        print('WARNING missing issues detected (increase pageSize/limit): {} \n'.format(gaps))

    # 内容没变就不写盘，避免定时任务产生空提交和无意义的文件改动
    if not ssqChanged(ssqPath, ssqs):
        print('No data change, skip writing \n')
        return True

    timeMark = '999999999'
    ssqs[timeMark] = '{},{},{},{},{}\n'.format(timeMark, updatesTotal, validRows + 1, str(int(round(time.time() * 1000))), 'Current behavior update info')
    ssqkeys = sorted(ssqs.keys(), reverse=True)
    # 先在内存里拼好，避免写入中途失败把已有数据截断成空文件
    txtBody = ''.join(ssqs[key] for key in ssqkeys)
    jsBody = 'window.ssqData = `{}`'.format(txtBody)
    try:
        mkdir('./spider_data/')
        writeAtomic(ssqPath, txtBody)
        writeAtomic(ssqJSPath, jsBody)
        print('updateSum is {} \n'.format(updatesTotal))
    except IOError as e:
        print('Write failed, {}: {} \n'.format(type(e).__name__, e))
        return False

    return True

def ssqChanged(ssqPath, ssqs):
    """比较抓到的数据与磁盘文件是否一致（忽略 999999999 统计行）。"""
    try:
        with open(ssqPath, 'r') as f:
            oldLines = {}
            for line in f:
                key = line.split(',')[0]
                if key and key != '999999999':
                    oldLines[key] = line
    except IOError:
        return True

    newLines = dict((k, v) for k, v in ssqs.items() if k != '999999999')
    return oldLines != newLines

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
    parser.add_argument("-u3", "--url3", type=str, required=False, default="", help="url3 fallback")
    args = parser.parse_args()
    try:
        print(args)
        # URL 两端的空白会让 requests 直接报错，先清掉
        ok = start(args.url.strip(), args.url2.strip(), args.url3.strip())
        print('Finished')
        if not ok:
            sys.exit(1)
    except Exception:
        # 打完整堆栈并以非 0 退出，否则 CI 会把静默失败当成功
        traceback.print_exc()
        print('error')
        sys.exit(1)
